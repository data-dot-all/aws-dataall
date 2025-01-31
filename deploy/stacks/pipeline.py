import re
import uuid
from typing import List

from aws_cdk import Stack, Tags, RemovalPolicy, Duration
from aws_cdk import aws_codebuild as codebuild
from aws_cdk import aws_codecommit as codecommit
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from aws_cdk import aws_kms as kms
from aws_cdk import aws_s3 as s3
from aws_cdk import pipelines
from aws_cdk.pipelines import CodePipelineSource

from .albfront_stage import AlbFrontStage
from .aurora import AuroraServerlessStack
from .backend_stage import BackendStage
from .cloudfront_stage import CloudfrontStage
from .codeartifact import CodeArtifactStack
from .ecr_stage import ECRStage
from .vpc import VpcStack
from .iam_utils import get_tooling_account_external_id


class PipelineStack(Stack):
    def __init__(
        self,
        id,
        scope,
        repo_connection_arn,
        target_envs: List = None,
        git_branch='main',
        resource_prefix='dataall',
        source='codecommit',
        repo_string='awslabs/aws-dataall',
        **kwargs,
    ):
        super().__init__(id, scope, **kwargs)
        self.validate_deployment_params(source, repo_connection_arn, git_branch, resource_prefix, target_envs)
        self.git_branch = git_branch
        self.source = source
        self.resource_prefix = resource_prefix
        self.target_envs = target_envs
        self.repo_string = repo_string
        self.repo_connection_arn = repo_connection_arn
        self.log_retention_duration = (
            self.node.try_get_context('log_retention_duration') or logs.RetentionDays.TWO_YEARS.value
        )

        self.vpc_stack = VpcStack(
            self,
            id='Vpc',
            envname=git_branch,
            cidr='10.0.0.0/16',
            resource_prefix=resource_prefix,
            vpc_id=self.node.try_get_context('tooling_vpc_id'),
            restricted_nacl=self.node.try_get_context('tooling_vpc_restricted_nacl'),
            log_retention_duration=self.log_retention_duration,
            **kwargs,
        )
        self.vpc = self.vpc_stack.vpc

        self.aurora_devdb = AuroraServerlessStack(
            self,
            'Aurora',
            envname=self.git_branch,
            resource_prefix=self.resource_prefix,
            vpc=self.vpc,
            prod_sizing=False,
            **kwargs,
        )

        self.codebuild_sg = ec2.SecurityGroup(
            self,
            f'{self.resource_prefix}-codebuild-sg',
            security_group_name=f'{self.resource_prefix}-{self.git_branch}-cbprojects-sg',
            vpc=self.vpc,
            allow_all_outbound=True,
        )
        self.aurora_devdb.aurora_sg.add_ingress_rule(
            peer=self.codebuild_sg,
            connection=ec2.Port.tcp(5432),
            description='Allow Codebuild to run integration tests',
        )

        self.codeartifact = CodeArtifactStack(
            self,
            'CodeArtifact',
            target_envs=self.target_envs,
            git_branch=self.git_branch,
            resource_prefix=self.resource_prefix,
        )

        self.set_codebuild_iam_roles()

        self.pipeline_bucket_name = f'{self.resource_prefix}-{self.git_branch}-code-{self.account}-{self.region}'
        self.pipeline_bucket = s3.Bucket(
            self,
            id='source-code-bucket',
            bucket_name=self.pipeline_bucket_name,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            encryption=s3.BucketEncryption.S3_MANAGED,
            cors=[
                s3.CorsRule(
                    allowed_methods=[
                        s3.HttpMethods.HEAD,
                        s3.HttpMethods.POST,
                        s3.HttpMethods.PUT,
                        s3.HttpMethods.DELETE,
                        s3.HttpMethods.GET,
                    ],
                    allowed_origins=['*'],
                    allowed_headers=['*'],
                    exposed_headers=[],
                )
            ],
            versioned=True,
            enforce_ssl=True,
            auto_delete_objects=True,
        )
        self.pipeline_bucket.grant_read_write(iam.AccountPrincipal(self.account))

        self.artifact_bucket_name = f'{self.resource_prefix}-{self.git_branch}-artifacts-{self.account}-{self.region}'
        self.artifact_bucket_key = kms.Key(
            self,
            f'{self.artifact_bucket_name}-key',
            removal_policy=RemovalPolicy.DESTROY,
            alias=f'{self.artifact_bucket_name}-key',
            enable_key_rotation=True,
        )
        self.artifact_bucket = s3.Bucket(
            self,
            'pipeline-artifacts-bucket',
            bucket_name=f'{self.resource_prefix}-{self.git_branch}-artifacts-{self.account}-{self.region}',
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            versioned=True,
            encryption_key=self.artifact_bucket_key,
            enforce_ssl=True,
            auto_delete_objects=True,
        )

        if self.source == 'codestar_connection':
            source = CodePipelineSource.connection(
                repo_string=repo_string, branch=self.git_branch, connection_arn=repo_connection_arn
            )

        else:
            source = CodePipelineSource.code_commit(
                repository=codecommit.Repository.from_repository_name(self, 'sourcerepo', repository_name='dataall'),
                branch=self.git_branch,
            )

        self.pipeline = pipelines.CodePipeline(
            self,
            f'{self.resource_prefix}-{self.git_branch}-cdkpipeline',
            pipeline_name=f'{self.resource_prefix}-pipeline-{self.git_branch}',
            publish_assets_in_parallel=False,
            artifact_bucket=self.artifact_bucket,
            cross_account_keys=True,
            enable_key_rotation=True,
            synth=pipelines.CodeBuildStep(
                'Synth',
                input=source,
                build_environment=codebuild.BuildEnvironment(
                    build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_5,
                ),
                commands=[
                    f'aws codeartifact login --tool npm --repository {self.codeartifact.codeartifact_npm_repo_name} --domain {self.codeartifact.codeartifact_domain_name} --domain-owner {self.codeartifact.domain.attr_owner}',
                    'npm install -g aws-cdk',
                    f'aws codeartifact login --tool pip --repository {self.codeartifact.codeartifact_pip_repo_name} --domain {self.codeartifact.codeartifact_domain_name} --domain-owner {self.codeartifact.domain.attr_owner}',
                    'pip install -r deploy/requirements.txt',
                    'cdk synth',
                    'echo ${CODEBUILD_SOURCE_VERSION}',
                ],
                role=self.baseline_codebuild_role.without_policy_updates(),
                vpc=self.vpc,
            ),
            code_build_defaults=pipelines.CodeBuildOptions(
                build_environment=codebuild.BuildEnvironment(
                    environment_variables={
                        'DATAALL_REPO_BRANCH': codebuild.BuildEnvironmentVariable(value=git_branch),
                    }
                )
            ),
        )

        self.pipeline.node.add_dependency(self.aurora_devdb)

        self.set_quality_gate_stage()

        self.image_tag = f'{git_branch}-{str(uuid.uuid4())[:8]}'

        repository_name = self.set_ecr_stage({'envname': git_branch, 'account': self.account, 'region': self.region})

        target_envs = target_envs or [{'envname': 'dev', 'account': self.account, 'region': self.region}]

        for target_env in target_envs:
            self.pipeline_bucket.grant_read(iam.AccountPrincipal(target_env['account']))

            backend_stage = self.set_backend_stage(target_env, repository_name)

            if target_env.get('with_approval'):
                backend_stage.add_pre(
                    pipelines.ManualApprovalStep(
                        id=f'Approve{target_env["envname"]}Deployment',
                        comment=f'Approve deployment for environment {target_env["envname"]}',
                    )
                )

            if target_env.get('with_approval_tests', False):
                self.set_approval_tests_stage(backend_stage, target_env)

            if target_env.get('enable_update_dataall_stacks_in_cicd_pipeline', False):
                self.set_stacks_updater_stage(target_env)

            if target_env.get('internet_facing', True):
                self.set_cloudfront_stage(
                    target_env,
                )
            else:
                self.set_albfront_stage(target_env, repository_name)

        Tags.of(self).add('Application', f'{resource_prefix}-{git_branch}')

    def set_codebuild_iam_roles(self):
        # IAM Role Creation
        self.baseline_codebuild_role = iam.Role(
            self,
            id=f'CodeBuildBaselineRole{self.git_branch}',
            role_name=f'{self.resource_prefix}-{self.git_branch}-baseline-codebuild-role',
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal('codebuild.amazonaws.com'),
                iam.ServicePrincipal('codepipeline.amazonaws.com'),
                iam.AccountPrincipal(self.account),
            ),
        )
        self.expanded_codebuild_role = iam.Role(
            self,
            id=f'CodeBuildExpandedRole{self.git_branch}',
            role_name=f'{self.resource_prefix}-{self.git_branch}-expanded-codebuild-role',
            assumed_by=iam.ServicePrincipal('codebuild.amazonaws.com'),
        )

        self.baseline_codebuild_policy = iam.ManagedPolicy(
            self,
            'BaselineCodeBuildManagedPolicy',
            managed_policy_name=f'{self.resource_prefix}-{self.git_branch}-baseline-cb-policy',
            roles=[self.baseline_codebuild_role, self.expanded_codebuild_role],
            statements=[
                iam.PolicyStatement(
                    actions=[
                        'sts:AssumeRole',
                    ],
                    resources=['arn:aws:iam::*:role/cdk-hnb659fds-lookup-role*'],
                ),
                iam.PolicyStatement(
                    actions=[
                        'sts:GetServiceBearerToken',
                    ],
                    resources=['*'],
                    conditions={'StringEquals': {'sts:AWSServiceName': 'codeartifact.amazonaws.com'}},
                ),
                iam.PolicyStatement(
                    actions=[
                        'ecr:GetAuthorizationToken',
                        'ec2:DescribePrefixLists',
                        'ec2:DescribeManagedPrefixLists',
                        'ec2:DescribeNetworkInterfaces',
                        'ec2:DescribeSubnets',
                        'ec2:DescribeSecurityGroups',
                        'ec2:DescribeDhcpOptions',
                        'ec2:DescribeVpcs',
                    ],
                    resources=['*'],
                ),
                iam.PolicyStatement(
                    actions=[
                        'ec2:CreateNetworkInterface',
                        'ec2:DeleteNetworkInterface',
                    ],
                    resources=[
                        f'arn:aws:ec2:{self.region}:{self.account}:*/*',
                    ],
                ),
                iam.PolicyStatement(
                    actions=[
                        'ec2:AssignPrivateIpAddresses',
                        'ec2:UnassignPrivateIpAddresses',
                    ],
                    resources=[
                        f'arn:aws:ec2:{self.region}:{self.account}:*/*',
                    ],
                    conditions={'StringEquals': {'ec2:Vpc': f'{self.vpc.vpc_id}'}},
                ),
                iam.PolicyStatement(
                    actions=[
                        'codeartifact:GetAuthorizationToken',
                        'codeartifact:GetRepositoryEndpoint',
                        'codeartifact:ReadFromRepository',
                        'ecr:GetDownloadUrlForLayer',
                        'ecr:BatchGetImage',
                        'ecr:BatchCheckLayerAvailability',
                        'ecr:PutImage',
                        'ecr:InitiateLayerUpload',
                        'ecr:UploadLayerPart',
                        'ecr:CompleteLayerUpload',
                        'ecr:GetDownloadUrlForLayer',
                        'kms:Decrypt',
                        'kms:Encrypt',
                        'kms:GenerateDataKey',
                        'kms:ReEncrypt*',
                        'kms:DescribeKey',
                        'secretsmanager:GetSecretValue',
                        'secretsmanager:DescribeSecret',
                        'ssm:GetParametersByPath',
                        'ssm:GetParameters',
                        'ssm:GetParameter',
                        's3:Get*',
                        's3:Put*',
                        's3:List*',
                        'codebuild:CreateReportGroup',
                        'codebuild:CreateReport',
                        'codebuild:UpdateReport',
                        'codebuild:BatchPutTestCases',
                        'codebuild:BatchPutCodeCoverages',
                        'ec2:GetManagedPrefixListEntries',
                        'ec2:CreateNetworkInterfacePermission',
                        'logs:CreateLogGroup',
                        'logs:CreateLogStream',
                        'logs:PutLogEvents',
                    ],
                    resources=[
                        f'arn:aws:s3:::{self.resource_prefix}*',
                        f'arn:aws:s3:::{self.resource_prefix}*/*',
                        f'arn:aws:codebuild:{self.region}:{self.account}:project/*{self.resource_prefix}*',
                        f'arn:aws:codebuild:{self.region}:{self.account}:report-group/{self.resource_prefix}*',
                        f'arn:aws:secretsmanager:{self.region}:{self.account}:secret:*{self.resource_prefix}*',
                        f'arn:aws:secretsmanager:{self.region}:{self.account}:secret:*dataall*',
                        f'arn:aws:kms:{self.region}:{self.account}:key/*',
                        f'arn:aws:ssm:*:{self.account}:parameter/*dataall*',
                        f'arn:aws:ssm:*:{self.account}:parameter/*{self.resource_prefix}*',
                        f'arn:aws:ecr:{self.region}:{self.account}:repository/{self.resource_prefix}*',
                        f'arn:aws:codeartifact:{self.region}:{self.account}:repository/{self.resource_prefix}*',
                        f'arn:aws:codeartifact:{self.region}:{self.account}:domain/{self.resource_prefix}*',
                        f'arn:aws:ec2:{self.region}:{self.account}:prefix-list/*',
                        f'arn:aws:ec2:{self.region}:{self.account}:network-interface/*',
                        f'arn:aws:logs:{self.region}:{self.account}:log-group:/aws/codebuild/{self.resource_prefix}*',
                    ],
                ),
            ],
        )
        self.expanded_codebuild_policy = iam.ManagedPolicy(
            self,
            'ExpandedCodeBuildManagedPolicy',
            managed_policy_name=f'{self.resource_prefix}-{self.git_branch}-expanded-cb-policy',
            roles=[self.expanded_codebuild_role],
            statements=[
                iam.PolicyStatement(
                    actions=[
                        'cloudfront:CreateInvalidation',
                        'sts:AssumeRole',
                    ],
                    resources=[
                        f'arn:aws:iam::*:role/{self.resource_prefix}*',
                        'arn:aws:iam::*:role/dataall-integration-tests*',
                        'arn:aws:cloudfront::*:distribution/*',
                    ],
                )
            ],
        )

    def validate_deployment_params(self, source, repo_connection_arn, git_branch, resource_prefix, target_envs):
        if (source == 'codestar_connection' and repo_connection_arn is None) or (
            repo_connection_arn is not None
            and not re.match(r'arn:aws(-[\w]+)*:.+:.+:[0-9]{12}:.+', repo_connection_arn)
        ):
            raise ValueError(
                f'Error: When the source is a CodeStar Connection, {repo_connection_arn} cannot be None.'
                f'Please define the ARN of the CodeStar Connection'
            )
        if not bool(re.match(r'^[a-zA-Z0-9-_]+$', git_branch)):
            raise ValueError(
                f'Git branch {git_branch} name is created to use AWS resources.'
                f'It must match the pattern ^[a-zA-Z0-9-_]+$'
            )
        for env in target_envs:
            if not bool(re.match(r'^[a-zA-Z0-9-_]+$', env['envname'])):
                raise ValueError(
                    f'envname {env["envname"]} is created to use AWS resources. '
                    f'It must match the pattern ^[a-zA-Z0-9-_]+$'
                )
            if env['account'] == self.account and env['region'] == self.region and env['envname'] == git_branch:
                raise ValueError(
                    'Seems like tooling account and deployment '
                    'account are the same in the same region with the same envname and git_branch.'
                    'Try a different envname than git_branch for it to work'
                )
            if (
                env.get('internet_facing', True) not in [True, False]
                or env.get('with_approval', False) not in [True, False]
                or env.get('prod_sizing', False) not in [True, False]
                or env.get('enable_cw_canaries', False) not in [True, False]
                or env.get('enable_cw_rum', False) not in [True, False]
            ):
                raise ValueError(
                    'Data type not supported in one of cdk.json variables (internet_facing,with_approvalprod_sizing,enable_cw_canaries,enable_cw_rum) \n'
                    'Supported data type : Boolean'
                )
        if len(resource_prefix) >= 20:
            raise ValueError(
                f'Resource prefix {resource_prefix} '
                f'must be less than 50 characters to avoid AWS resources naming limits'
            )

        # Validate if all configs are present when deploying custom_auth
        for env in target_envs:
            if 'custom_auth' in env:
                custom_auth_configs = env.get('custom_auth')
                if (
                    'url' not in custom_auth_configs
                    or 'provider' not in custom_auth_configs
                    or 'redirect_url' not in custom_auth_configs
                    or 'client_id' not in custom_auth_configs
                    or 'response_types' not in custom_auth_configs
                    or 'scopes' not in custom_auth_configs
                    or 'jwks_url' not in custom_auth_configs
                    or 'claims_mapping' not in custom_auth_configs
                    or 'user_id' not in custom_auth_configs['claims_mapping']
                    or 'email' not in custom_auth_configs['claims_mapping']
                ):
                    raise ValueError(
                        'Custom Auth Configuration Error : Missing some configurations in custom_auth section in Deployments. Please take a look at template_cdk.json for reference or visit the data.all webpage and checkout the Deploy to AWS section'
                    )

                if (
                    not isinstance(custom_auth_configs['url'], str)
                    or not isinstance(custom_auth_configs['provider'], str)
                    or not isinstance(custom_auth_configs['redirect_url'], str)
                    or not isinstance(custom_auth_configs['client_id'], str)
                    or not isinstance(custom_auth_configs['response_types'], str)
                    or not isinstance(custom_auth_configs['scopes'], str)
                    or not isinstance(custom_auth_configs['jwks_url'], str)
                    or not isinstance(custom_auth_configs['claims_mapping']['user_id'], str)
                    or not isinstance(custom_auth_configs['claims_mapping']['email'], str)
                ):
                    raise TypeError(
                        'Custom Auth Configuration Error : Type error: Configs type is not as required. Please take a look at template_cdk.json for reference or visit the data.all webpage and checkout the Deploy to AWS section'
                    )

    def set_quality_gate_stage(self):
        quality_gate_param = self.node.try_get_context('quality_gate')
        if quality_gate_param is not False:
            gate_quality_wave = self.pipeline.add_wave('QualityGate')
            gate_quality_wave.add_pre(
                pipelines.CodeBuildStep(
                    id='ValidateDBMigrations',
                    build_environment=codebuild.BuildEnvironment(
                        build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_5,
                    ),
                    commands=[
                        f'aws codeartifact login --tool pip --repository {self.codeartifact.codeartifact_pip_repo_name} --domain {self.codeartifact.codeartifact_domain_name} --domain-owner {self.codeartifact.domain.attr_owner}',
                        f'export envname={self.git_branch}',
                        'python -m venv env',
                        '. env/bin/activate',
                        'make drop-tables',
                        'make upgrade-db',
                    ],
                    role=self.baseline_codebuild_role.without_policy_updates(),
                    vpc=self.vpc,
                    security_groups=[self.codebuild_sg],
                ),
                pipelines.CodeBuildStep(
                    id='SecurityChecks',
                    build_environment=codebuild.BuildEnvironment(
                        build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_5,
                    ),
                    commands=[
                        f'aws codeartifact login --tool pip --repository {self.codeartifact.codeartifact_pip_repo_name} --domain {self.codeartifact.codeartifact_domain_name} --domain-owner {self.codeartifact.domain.attr_owner}',
                        'pip install --upgrade pip',
                        'python -m venv env',
                        '. env/bin/activate',
                        'make check-security',
                    ],
                    role=self.baseline_codebuild_role.without_policy_updates(),
                    vpc=self.vpc,
                ),
                pipelines.CodeBuildStep(
                    id='Lint',
                    build_environment=codebuild.BuildEnvironment(
                        build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_5,
                    ),
                    commands=[
                        f'aws codeartifact login --tool pip --repository {self.codeartifact.codeartifact_pip_repo_name} --domain {self.codeartifact.codeartifact_domain_name} --domain-owner {self.codeartifact.domain.attr_owner}',
                        'pip install --upgrade pip',
                        'python -m venv env',
                        '. env/bin/activate',
                        'make lint',
                        'cd frontend',
                        f'aws codeartifact login --tool npm --repository {self.codeartifact.codeartifact_npm_repo_name} --domain {self.codeartifact.codeartifact_domain_name} --domain-owner {self.codeartifact.domain.attr_owner}',
                        'npm install',
                        'npm run copy-config',
                        'npm run copy-version',
                        'npm run lint -- --quiet',
                    ],
                    role=self.baseline_codebuild_role.without_policy_updates(),
                    vpc=self.vpc,
                ),
            )
            gate_quality_wave.add_post(
                pipelines.CodeBuildStep(
                    id='IntegrationTests',
                    build_environment=codebuild.BuildEnvironment(
                        build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_5,
                    ),
                    partial_build_spec=codebuild.BuildSpec.from_object(
                        dict(
                            version='0.2',
                            phases={
                                'build': {
                                    'commands': [
                                        'set -eu',
                                        f'aws codeartifact login --tool pip --repository {self.codeartifact.codeartifact_pip_repo_name} --domain {self.codeartifact.codeartifact_domain_name} --domain-owner {self.codeartifact.domain.attr_owner}',
                                        f'export envname={self.git_branch}',
                                        'python -m venv env',
                                        '. env/bin/activate',
                                        'make coverage',
                                    ]
                                },
                            },
                            reports={
                                'CoverageReport': {
                                    'files': ['cobertura.xml'],
                                    'base-directory': '$CODEBUILD_SRC_DIR',
                                    'file-format': 'COBERTURAXML',
                                }
                            },
                        )
                    ),
                    commands=[],
                    role=self.baseline_codebuild_role.without_policy_updates(),
                    vpc=self.vpc,
                    security_groups=[self.codebuild_sg],
                    timeout=Duration.hours(36),
                ),
                pipelines.CodeBuildStep(
                    id='UploadCodeToS3',
                    build_environment=codebuild.BuildEnvironment(
                        build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_5,
                    ),
                    commands=[
                        'mkdir -p source_build',
                        'mv backend ./source_build/',
                        'mv config.json ./source_build/',
                        'cd source_build/ && zip -r ../source_build/source_build.zip *',
                        f'aws s3api put-object --bucket {self.pipeline_bucket.bucket_name}  --key source_build.zip --body source_build.zip',
                    ],
                    role=self.baseline_codebuild_role.without_policy_updates(),
                    vpc=self.vpc,
                    security_groups=[self.codebuild_sg],
                ),
            )
        else:
            gate_quality_wave = self.pipeline.add_wave('UploadCodeToS3')
            gate_quality_wave.add_pre(
                pipelines.CodeBuildStep(
                    id='UploadCodeToS3',
                    build_environment=codebuild.BuildEnvironment(
                        build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_5,
                    ),
                    commands=[
                        'mkdir -p source_build',
                        'mv backend ./source_build/',
                        'mv config.json ./source_build/',
                        'cd source_build/ && zip -r ../source_build/source_build.zip *',
                        f'aws s3api put-object --bucket {self.pipeline_bucket.bucket_name}  --key source_build.zip --body source_build.zip',
                    ],
                    role=self.baseline_codebuild_role.without_policy_updates(),
                    vpc=self.vpc,
                    security_groups=[self.codebuild_sg],
                ),
            )

    def set_ecr_stage(
        self,
        target_env,
    ):
        repository_name = f'{self.resource_prefix}-{target_env["envname"]}-ecr-repository'
        ecr_stage = self.pipeline.add_stage(
            ECRStage(
                self,
                f'{self.resource_prefix}-ecr-stage',
                env={
                    'account': target_env['account'],
                    'region': target_env['region'],
                },
                envname=target_env['envname'],
                tooling_account_id=self.account,
                target_envs=self.target_envs,
                repository_name=repository_name,
            )
        )
        ecr_stage.add_post(
            pipelines.CodeBuildStep(
                id='LambdaImage',
                build_environment=codebuild.BuildEnvironment(
                    build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_5,
                    privileged=True,
                    environment_variables={
                        'REPOSITORY_URI': codebuild.BuildEnvironmentVariable(
                            value=f'{target_env["account"]}.dkr.ecr.{target_env["region"]}.amazonaws.com/{repository_name}'
                        ),
                        'IMAGE_TAG': codebuild.BuildEnvironmentVariable(value=f'lambdas-{self.image_tag}'),
                    },
                ),
                commands=[
                    f'make deploy-image type=lambda image-tag=$IMAGE_TAG account={target_env["account"]} region={target_env["region"]} repo={repository_name}',
                ],
                role=self.baseline_codebuild_role.without_policy_updates(),
                vpc=self.vpc,
            ),
            pipelines.CodeBuildStep(
                id='ECSImage',
                build_environment=codebuild.BuildEnvironment(
                    build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_5,
                    privileged=True,
                    environment_variables={
                        'REPOSITORY_URI': codebuild.BuildEnvironmentVariable(
                            value=f'{target_env["account"]}.dkr.ecr.{target_env["region"]}.amazonaws.com/{repository_name}'
                        ),
                        'IMAGE_TAG': codebuild.BuildEnvironmentVariable(value=f'cdkproxy-{self.image_tag}'),
                    },
                ),
                commands=[
                    f'make deploy-image type=ecs image-tag=$IMAGE_TAG account={target_env["account"]} region={target_env["region"]} repo={repository_name}',
                ],
                role=self.baseline_codebuild_role.without_policy_updates(),
                vpc=self.vpc,
            ),
        )
        return repository_name

    def set_backend_stage(self, target_env, repository_name):
        backend_stage = self.pipeline.add_stage(
            BackendStage(
                self,
                f'{self.resource_prefix}-{target_env["envname"]}-backend-stage',
                env={
                    'account': target_env['account'],
                    'region': target_env['region'],
                },
                envname=target_env['envname'],
                resource_prefix=self.resource_prefix,
                tooling_account_id=self.account,
                pipeline_bucket=self.pipeline_bucket_name,
                ecr_repository=f'arn:aws:ecr:{target_env.get("region", self.region)}:{self.account}:repository/{repository_name}',
                commit_id=self.image_tag,
                vpc_id=target_env.get('vpc_id'),
                vpc_endpoints_sg=target_env.get('vpc_endpoints_sg'),
                vpc_restricted_nacls=target_env.get('vpc_restricted_nacl', False),
                internet_facing=target_env.get('internet_facing', True),
                custom_domain=target_env.get('custom_domain'),
                apigw_custom_domain=target_env.get('apigw_custom_domain'),
                ip_ranges=target_env.get('ip_ranges'),
                apig_vpce=target_env.get('apig_vpce'),
                prod_sizing=target_env.get('prod_sizing', True),
                enable_cw_rum=target_env.get('enable_cw_rum', False) and target_env.get('custom_auth', None) is None,
                enable_cw_canaries=target_env.get('enable_cw_canaries', False)
                and target_env.get('custom_auth', None) is None,
                shared_dashboard_sessions=target_env.get('shared_dashboard_sessions', 'anonymous'),
                enable_opensearch_serverless=target_env.get('enable_opensearch_serverless', False),
                enable_pivot_role_auto_create=target_env.get('enable_pivot_role_auto_create', False),
                codeartifact_domain_name=self.codeartifact.codeartifact_domain_name,
                codeartifact_pip_repo_name=self.codeartifact.codeartifact_pip_repo_name,
                reauth_config=target_env.get('reauth_config', None),
                cognito_user_session_timeout_inmins=target_env.get('cognito_user_session_timeout_inmins', 43200),
                custom_auth=target_env.get('custom_auth', None),
                custom_waf_rules=target_env.get('custom_waf_rules', None),
                with_approval_tests=target_env.get('with_approval_tests', False),
                allowed_origins=target_env.get('allowed_origins', '*'),
                log_retention_duration=self.log_retention_duration,
                deploy_dms_stack=target_env.get('aurora_migration_enabled', False),
                old_aurora_connection_secret_arn=target_env.get('old_aurora_connection_secret_arn', ''),
            )
        )
        return backend_stage

    def set_approval_tests_stage(
        self,
        backend_stage,
        target_env,
    ):
        if target_env.get('custom_auth', None) is None:
            frontend_deployment_role_arn = f'arn:aws:iam::{target_env["account"]}:role/{self.resource_prefix}-{target_env["envname"]}-cognito-config-role'
        else:
            frontend_deployment_role_arn = f'arn:aws:iam::{target_env["account"]}:role/{self.resource_prefix}-{target_env["envname"]}-frontend-config-role'

        backend_stage.add_post(
            pipelines.CodeBuildStep(
                id='ApprovalTests',
                build_environment=codebuild.BuildEnvironment(
                    build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_5,
                ),
                partial_build_spec=codebuild.BuildSpec.from_object(
                    dict(
                        version='0.2',
                        phases={
                            'build': {
                                'commands': [
                                    'set -eu',
                                    'mkdir ~/.aws/ && touch ~/.aws/config',
                                    'echo "[profile buildprofile]" > ~/.aws/config',
                                    f'echo "role_arn = {frontend_deployment_role_arn}" >> ~/.aws/config',
                                    'echo "credential_source = EcsContainer" >> ~/.aws/config',
                                    f'echo "external_id = {get_tooling_account_external_id(target_env["account"])}" >> ~/.aws/config',
                                    'aws sts get-caller-identity --profile buildprofile',
                                    f'export COGNITO_CLIENT=$(aws ssm get-parameter --name /dataall/{target_env["envname"]}/cognito/appclient --profile buildprofile --output text --query "Parameter.Value")',
                                    f'export API_ENDPOINT=$(aws ssm get-parameter --name /dataall/{target_env["envname"]}/apiGateway/backendUrl --profile buildprofile --output text --query "Parameter.Value")',
                                    f'export IDP_DOMAIN_URL=https://$(aws ssm get-parameter --name /dataall/{target_env["envname"]}/cognito/domain --profile buildprofile --output text --query "Parameter.Value").auth.{target_env["region"]}.amazoncognito.com',
                                    f'export DATAALL_DOMAIN_URL=https://$(aws ssm get-parameter --region us-east-1 --name /dataall/{target_env["envname"]}/CloudfrontDistributionDomainName --profile buildprofile --output text --query "Parameter.Value")',
                                    f'export TESTDATA=$(aws ssm get-parameter --name /dataall/{target_env["envname"]}/testdata --profile buildprofile --output text --query "Parameter.Value")',
                                    f'export ENVNAME={target_env["envname"]}',
                                    f'export AWS_REGION={target_env["region"]}',
                                    f'aws codeartifact login --tool pip --repository {self.codeartifact.codeartifact_pip_repo_name} --domain {self.codeartifact.codeartifact_domain_name} --domain-owner {self.codeartifact.domain.attr_owner}',
                                    'python -m venv env',
                                    '. env/bin/activate',
                                    'make integration-tests',
                                ]
                            },
                        },
                        reports={
                            'PytestReports': {
                                'files': ['reports/integration_tests.xml'],
                                'base-directory': '$CODEBUILD_SRC_DIR',
                                'file-format': 'JUNITXML',
                            }
                        },
                    )
                ),
                commands=[],
                role=self.expanded_codebuild_role.without_policy_updates(),
                vpc=self.vpc,
                security_groups=[self.codebuild_sg],
                timeout=Duration.hours(4),
            )
        )

    def set_stacks_updater_stage(
        self,
        target_env,
    ):
        wave = self.pipeline.add_wave(f'{self.resource_prefix}-{target_env["envname"]}-stacks-updater-stage')
        wave.add_post(
            pipelines.CodeBuildStep(
                id='StacksUpdater',
                build_environment=codebuild.BuildEnvironment(
                    build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_5,
                ),
                commands=[
                    'mkdir ~/.aws/ && touch ~/.aws/config',
                    'echo "[profile buildprofile]" > ~/.aws/config',
                    f'echo "role_arn = arn:aws:iam::{target_env["account"]}:role/{self.resource_prefix}-{target_env["envname"]}-cb-stackupdater-role" >> ~/.aws/config',
                    'echo "credential_source = EcsContainer" >> ~/.aws/config',
                    f'echo "external_id = {get_tooling_account_external_id(target_env["account"])}" >> ~/.aws/config',
                    'aws sts get-caller-identity --profile buildprofile',
                    f"export cluster_name=$(aws ssm get-parameter --name /dataall/{target_env['envname']}/ecs/cluster/name --profile buildprofile --output text --query 'Parameter.Value')",
                    f"export private_subnets=$(aws ssm get-parameter --name /dataall/{target_env['envname']}/ecs/private_subnets --profile buildprofile --output text --query 'Parameter.Value')",
                    f"export security_groups=$(aws ssm get-parameter --name /dataall/{target_env['envname']}/ecs/security_groups --profile buildprofile --output text --query 'Parameter.Value')",
                    f"export task_definition=$(aws ssm get-parameter --name /dataall/{target_env['envname']}/ecs/task_def_arn/stacks_updater --profile buildprofile --output text --query 'Parameter.Value')",
                    'network_config="awsvpcConfiguration={subnets=[$private_subnets],securityGroups=[$security_groups],assignPublicIp=DISABLED}"',
                    f'cluster_arn="arn:aws:ecs:{target_env["region"]}:{target_env["account"]}:cluster/$cluster_name"',
                    'aws --profile buildprofile ecs run-task --task-definition $task_definition --cluster "$cluster_arn" --launch-type "FARGATE" --network-configuration "$network_config" --launch-type FARGATE --propagate-tags TASK_DEFINITION',
                ],
                role=self.expanded_codebuild_role.without_policy_updates(),
                vpc=self.vpc,
            ),
        )

    def set_cloudfront_stage(self, target_env):
        cloudfront_stage = self.pipeline.add_stage(
            CloudfrontStage(
                self,
                f'{self.resource_prefix}-{target_env["envname"]}-cloudfront-stage',
                env={
                    'account': target_env['account'],
                    'region': 'us-east-1',
                },
                envname=target_env['envname'],
                resource_prefix=self.resource_prefix,
                tooling_account_id=self.account,
                custom_domain=target_env.get('custom_domain'),
                custom_auth=target_env.get('custom_auth', None),
                custom_waf_rules=target_env.get('custom_waf_rules', None),
                backend_region=target_env.get('region', self.region),
            )
        )
        front_stage_actions = (
            pipelines.CodeBuildStep(
                id='DeployFrontEnd',
                build_environment=codebuild.BuildEnvironment(
                    build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_5,
                    compute_type=codebuild.ComputeType.LARGE,
                ),
                commands=[
                    f'export REACT_APP_STAGE={target_env["envname"]}',
                    f'export envname={target_env["envname"]}',
                    f'export internet_facing={target_env.get("internet_facing", True)}',
                    f'export custom_domain={str(True) if target_env.get("custom_domain") else str(False)}',
                    f'export deployment_region={target_env.get("region", self.region)}',
                    f'export enable_cw_rum={target_env.get("enable_cw_rum", False) and target_env.get("custom_auth", None) is None}',
                    f'export resource_prefix={self.resource_prefix}',
                    f'export reauth_ttl={str(target_env.get("reauth_config", {}).get("ttl", 5))}',
                    f'export custom_auth_provider={str(target_env.get("custom_auth", {}).get("provider", "None"))}',
                    f'export custom_auth_url={str(target_env.get("custom_auth", {}).get("url", "None"))}',
                    f'export custom_auth_redirect_url={str(target_env.get("custom_auth", {}).get("redirect_url", "None"))}',
                    f'export custom_auth_client_id={str(target_env.get("custom_auth", {}).get("client_id", "None"))}',
                    f'export custom_auth_response_types={str(target_env.get("custom_auth", {}).get("response_types", "None"))}',
                    f'export custom_auth_scopes={str(target_env.get("custom_auth", {}).get("scopes", "None"))}',
                    f'export custom_auth_claims_mapping_email={str(target_env.get("custom_auth", {}).get("claims_mapping", {}).get("email", "None"))}',
                    f'export custom_auth_claims_mapping_user_id={str(target_env.get("custom_auth", {}).get("claims_mapping", {}).get("user_id", "None"))}',
                    'mkdir ~/.aws/ && touch ~/.aws/config',
                    'echo "[profile buildprofile]" > ~/.aws/config',
                    f'echo "role_arn = arn:aws:iam::{target_env["account"]}:role/{self.resource_prefix}-{target_env["envname"]}-S3DeploymentRole" >> ~/.aws/config',
                    'echo "credential_source = EcsContainer" >> ~/.aws/config',
                    f'echo "external_id = {get_tooling_account_external_id(target_env["account"])}" >> ~/.aws/config',
                    'aws sts get-caller-identity --profile buildprofile',
                    'export AWS_PROFILE=buildprofile',
                    'pip install boto3==1.35.26',
                    'pip install beautifulsoup4',
                    'python deploy/configs/frontend_config.py',
                    'export AWS_DEFAULT_REGION=us-east-1',
                    'export AWS_REGION=us-east-1',
                    f"export distributionId=$(aws ssm get-parameter --name /dataall/{target_env['envname']}/CloudfrontDistributionId --profile buildprofile --output text --query 'Parameter.Value')",
                    f"export bucket=$(aws ssm get-parameter --name /dataall/{target_env['envname']}/CloudfrontDistributionBucket --profile buildprofile --output text --query 'Parameter.Value')",
                    'export NODE_OPTIONS="--max-old-space-size=6144"',
                    'npm install -g yarn',
                    'cd frontend',
                    'yarn install',
                    'yarn build',
                    'aws s3 sync build/ s3://$bucket --profile buildprofile',
                    "aws cloudfront create-invalidation --distribution-id $distributionId --paths '/*' --profile buildprofile",
                ],
                role=self.expanded_codebuild_role.without_policy_updates(),
                vpc=self.vpc,
            ),
        )
        if target_env.get('enable_cw_rum', False) and target_env.get('custom_auth', None) is None:
            front_stage_actions = (
                *front_stage_actions,
                self.cw_rum_config_action(target_env),
            )
        self.pipeline.add_wave(f'{self.resource_prefix}-{target_env["envname"]}-frontend-stage').add_post(
            *front_stage_actions
        )
        if target_env.get('custom_auth', None) is None:
            self.pipeline.add_wave(f'{self.resource_prefix}-{target_env["envname"]}-docs-stage').add_post(
                pipelines.CodeBuildStep(
                    id='UpdateDocumentation',
                    build_environment=codebuild.BuildEnvironment(
                        build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_4,
                    ),
                    commands=[
                        f'aws codeartifact login --tool pip --repository {self.codeartifact.codeartifact_pip_repo_name} --domain {self.codeartifact.codeartifact_domain_name} --domain-owner {self.codeartifact.domain.attr_owner}',
                        f'make assume-role REMOTE_ACCOUNT_ID={target_env["account"]} REMOTE_ROLE={self.resource_prefix}-{target_env["envname"]}-S3DeploymentRole EXTERNAL_ID={get_tooling_account_external_id(target_env["account"])}',
                        '. ./.env.assumed_role',
                        'aws sts get-caller-identity',
                        'export AWS_DEFAULT_REGION=us-east-1',
                        f"export distributionId=$(aws ssm get-parameter --name /dataall/{target_env['envname']}/cloudfront/docs/user/CloudfrontDistributionId --output text --query 'Parameter.Value')",
                        f"export bucket=$(aws ssm get-parameter --name /dataall/{target_env['envname']}/cloudfront/docs/user/CloudfrontDistributionBucket --output text --query 'Parameter.Value')",
                        'cd documentation/userguide',
                        'pip install -r requirements.txt',
                        'mkdocs build',
                        'aws s3 sync site/ s3://$bucket',
                        "aws cloudfront create-invalidation --distribution-id $distributionId --paths '/*'",
                    ],
                    role=self.expanded_codebuild_role.without_policy_updates(),
                    vpc=self.vpc,
                ),
            )

    def cw_rum_config_action(self, target_env):
        return pipelines.CodeBuildStep(
            id='ConfigureRUM',
            build_environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_5,
            ),
            commands=[
                f'export envname={target_env["envname"]}',
                f'export internet_facing={target_env.get("internet_facing", True)}',
                f'export custom_domain={str(True) if target_env.get("custom_domain") else str(False)}',
                f'export deployment_region={target_env.get("region", self.region)}',
                f'export resource_prefix={self.resource_prefix}',
                'mkdir ~/.aws/ && touch ~/.aws/config',
                'echo "[profile buildprofile]" > ~/.aws/config',
                f'echo "role_arn = arn:aws:iam::{target_env["account"]}:role/{self.resource_prefix}-{target_env["envname"]}-rum-config-role" >> ~/.aws/config',
                'echo "credential_source = EcsContainer" >> ~/.aws/config',
                'aws sts get-caller-identity --profile buildprofile',
                'export AWS_PROFILE=buildprofile',
                'pip install --upgrade pip',
                'pip install boto3==1.35.26',
                'python deploy/configs/rum_config.py',
            ],
            role=self.expanded_codebuild_role.without_policy_updates(),
            vpc=self.vpc,
        )

    def set_albfront_stage(self, target_env, repository_name):
        if target_env.get('custom_auth', None) is None:
            frontend_deployment_role_arn = f'arn:aws:iam::{target_env["account"]}:role/{self.resource_prefix}-{target_env["envname"]}-cognito-config-role'
        else:
            frontend_deployment_role_arn = f'arn:aws:iam::{target_env["account"]}:role/{self.resource_prefix}-{target_env["envname"]}-frontend-config-role'
        albfront_stage = self.pipeline.add_stage(
            AlbFrontStage(
                self,
                f'{self.resource_prefix}-{target_env["envname"]}-albfront-stage',
                env={
                    'account': target_env['account'],
                    'region': target_env['region'],
                },
                envname=target_env['envname'],
                ecr_repository=f'arn:aws:ecr:{self.region}:{self.account}:repository/{repository_name}',
                image_tag=self.image_tag,
                custom_domain=target_env['custom_domain'],
                ip_ranges=target_env.get('ip_ranges'),
                resource_prefix=self.resource_prefix,
                custom_auth=target_env.get('custom_auth', None),
                backend_region=target_env.get('region', self.region),
                log_retention_duration=self.log_retention_duration,
            ),
            pre=[
                pipelines.CodeBuildStep(
                    id='FrontendImage',
                    build_environment=codebuild.BuildEnvironment(
                        build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_5,
                        compute_type=codebuild.ComputeType.LARGE,
                        privileged=True,
                        environment_variables={
                            'REPOSITORY_URI': codebuild.BuildEnvironmentVariable(
                                value=f'{self.account}.dkr.ecr.{self.region}.amazonaws.com/{repository_name}'
                            ),
                            'IMAGE_TAG': codebuild.BuildEnvironmentVariable(value=f'frontend-{self.image_tag}'),
                        },
                    ),
                    commands=[
                        f'aws codeartifact login --tool pip --repository {self.codeartifact.codeartifact_pip_repo_name} --domain {self.codeartifact.codeartifact_domain_name} --domain-owner {self.codeartifact.domain.attr_owner}',
                        f'export REACT_APP_STAGE={target_env["envname"]}',
                        f'export envname={target_env["envname"]}',
                        f'export internet_facing={target_env.get("internet_facing", False)}',
                        'export custom_domain=True',
                        f'export deployment_region={target_env.get("region", self.region)}',
                        f'export enable_cw_rum={target_env.get("enable_cw_rum", False) and target_env.get("custom_auth", None) is None}',
                        f'export resource_prefix={self.resource_prefix}',
                        f'export reauth_ttl={str(target_env.get("reauth_config", {}).get("ttl", 5))}',
                        f'export custom_auth_provider={str(target_env.get("custom_auth", {}).get("provider", "None"))}',
                        f'export custom_auth_url={str(target_env.get("custom_auth", {}).get("url", "None"))}',
                        f'export custom_auth_redirect_url={str(target_env.get("custom_auth", {}).get("redirect_url", "None"))}',
                        f'export custom_auth_client_id={str(target_env.get("custom_auth", {}).get("client_id", "None"))}',
                        f'export custom_auth_response_types={str(target_env.get("custom_auth", {}).get("response_types", "None"))}',
                        f'export custom_auth_scopes={str(target_env.get("custom_auth", {}).get("scopes", "None"))}',
                        f'export custom_auth_claims_mapping_email={str(target_env.get("custom_auth", {}).get("claims_mapping", {}).get("email", "None"))}',
                        f'export custom_auth_claims_mapping_user_id={str(target_env.get("custom_auth", {}).get("claims_mapping", {}).get("user_id", "None"))}',
                        'mkdir ~/.aws/ && touch ~/.aws/config',
                        'echo "[profile buildprofile]" > ~/.aws/config',
                        f'echo "role_arn = {frontend_deployment_role_arn}" >> ~/.aws/config',
                        'echo "credential_source = EcsContainer" >> ~/.aws/config',
                        f'echo "external_id = {get_tooling_account_external_id(target_env["account"])}" >> ~/.aws/config',
                        'aws sts get-caller-identity --profile buildprofile',
                        'export AWS_PROFILE=buildprofile',
                        'pip install boto3==1.35.26',
                        'pip install beautifulsoup4',
                        'python deploy/configs/frontend_config.py',
                        'unset AWS_PROFILE',
                        f'docker build -f frontend/docker/prod/Dockerfile --build-arg REACT_APP_STAGE={target_env["envname"]} --build-arg DOMAIN={target_env.get("custom_domain", {}).get("name")} -t $IMAGE_TAG:$IMAGE_TAG .',
                        f'aws ecr get-login-password --region {self.region} | docker login --username AWS --password-stdin {self.account}.dkr.ecr.{self.region}.amazonaws.com',
                        'docker tag $IMAGE_TAG:$IMAGE_TAG $REPOSITORY_URI:$IMAGE_TAG',
                        'docker push $REPOSITORY_URI:$IMAGE_TAG',
                    ],
                    role=self.expanded_codebuild_role.without_policy_updates(),
                    vpc=self.vpc,
                )
            ],
        )
        if target_env.get('custom_auth') is None:
            albfront_stage.add_pre(self.user_guide_pre_build_alb(repository_name))

        if target_env.get('enable_cw_rum', False) and target_env.get('custom_auth', None) is None:
            albfront_stage.add_post(self.cw_rum_config_action(target_env))

    def user_guide_pre_build_alb(self, repository_name):
        return pipelines.CodeBuildStep(
            id='UserGuideImage',
            build_environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_4,
                compute_type=codebuild.ComputeType.LARGE,
                privileged=True,
                environment_variables={
                    'REPOSITORY_URI': codebuild.BuildEnvironmentVariable(
                        value=f'{self.account}.dkr.ecr.{self.region}.amazonaws.com/{repository_name}'
                    ),
                    'IMAGE_TAG': codebuild.BuildEnvironmentVariable(value=f'userguide-{self.image_tag}'),
                },
            ),
            commands=[
                f'aws codeartifact login --tool pip --repository {self.codeartifact.codeartifact_pip_repo_name} --domain {self.codeartifact.codeartifact_domain_name} --domain-owner {self.codeartifact.domain.attr_owner}',
                'cd documentation/userguide',
                'docker build -f docker/prod/Dockerfile -t $IMAGE_TAG:$IMAGE_TAG .',
                f'aws ecr get-login-password --region {self.region} | docker login --username AWS --password-stdin {self.account}.dkr.ecr.{self.region}.amazonaws.com',
                'docker tag $IMAGE_TAG:$IMAGE_TAG $REPOSITORY_URI:$IMAGE_TAG',
                'docker push $REPOSITORY_URI:$IMAGE_TAG',
            ],
            role=self.expanded_codebuild_role.without_policy_updates(),
            vpc=self.vpc,
        )

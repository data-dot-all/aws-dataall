from builtins import super

import boto3
from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk import RemovalPolicy

from .aurora import AuroraServerlessStack
from .cognito import IdpStack
from .container import ContainerStack
from .cw_canaries import CloudWatchCanariesStack
from .cw_rum import CloudWatchRumStack
from .lambda_api import LambdaApiStack
from .monitoring import MonitoringStack
from .opensearch import OpenSearchStack
from .opensearch_serverless import OpenSearchServerlessStack
from .param_store_stack import ParamStoreStack
from .run_if import run_if
from .s3_resources import S3ResourcesStack
from .secrets_stack import SecretsManagerStack
from .ses_stack import SesStack
from .sqs import SqsStack
from .trigger_function_stack import TriggerFunctionStack
from .vpc import VpcStack
from .iam_utils import get_tooling_account_external_id
from .dms_task import DMSTaskStack


class BackendStack(Stack):
    def __init__(
        self,
        scope,
        id,
        envname: str = 'dev',
        resource_prefix='dataall',
        tooling_account_id=None,
        ecr_repository=None,
        image_tag=None,
        pipeline_bucket=None,
        vpc_id=None,
        vpc_restricted_nacls=False,
        vpc_endpoints_sg=None,
        internet_facing=True,
        custom_domain=None,
        apigw_custom_domain=None,
        ip_ranges=None,
        apig_vpce=None,
        prod_sizing=False,
        enable_cw_canaries=False,
        enable_cw_rum=False,
        shared_dashboard_sessions='anonymous',
        enable_pivot_role_auto_create=False,
        enable_opensearch_serverless=False,
        codeartifact_domain_name=None,
        codeartifact_pip_repo_name=None,
        reauth_config=None,
        cognito_user_session_timeout_inmins=43200,
        custom_auth=None,
        custom_waf_rules=None,
        with_approval_tests=False,
        allowed_origins='*',
        log_retention_duration=None,
        deploy_dms_stack=False,
        old_aurora_connection_secret_arn=None,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        self.resource_prefix = resource_prefix
        self.envname = envname
        self.prod_sizing = prod_sizing

        self.vpc_stack = VpcStack(
            self,
            id='Vpc',
            envname=envname,
            resource_prefix=resource_prefix,
            vpc_endpoints_sg=vpc_endpoints_sg,
            vpc_id=vpc_id,
            restricted_nacl=vpc_restricted_nacls,
            log_retention_duration=log_retention_duration,
            **kwargs,
        )
        vpc = self.vpc_stack.vpc
        vpc_endpoints_sg = self.vpc_stack.vpce_security_group
        vpce_connection = ec2.Connections(security_groups=[vpc_endpoints_sg])
        self.s3_prefix_list = self.get_s3_prefix_list()

        self.pivot_role_name = f'dataallPivotRole{"-cdk" if enable_pivot_role_auto_create else ""}'

        ParamStoreStack(
            self,
            'ParamStore',
            envname=envname,
            resource_prefix=resource_prefix,
            custom_domain=custom_domain,
            enable_cw_canaries=enable_cw_canaries,
            shared_dashboard_sessions=shared_dashboard_sessions,
            enable_pivot_role_auto_create=enable_pivot_role_auto_create,
            pivot_role_name=self.pivot_role_name,
            reauth_apis=reauth_config.get('reauth_apis', None) if reauth_config else None,
            prod_sizing=prod_sizing,
            tooling_account_id=tooling_account_id,
            **kwargs,
        )
        if enable_cw_canaries:
            SecretsManagerStack(
                self,
                'Secrets',
                envname=envname,
                resource_prefix=resource_prefix,
                **kwargs,
            )

        s3_resources_stack = S3ResourcesStack(
            self,
            'S3Resources',
            envname=envname,
            resource_prefix=resource_prefix,
            **kwargs,
        )

        cognito_stack = None
        if custom_auth is None:
            cognito_stack = IdpStack(
                self,
                'Cognito',
                envname=envname,
                resource_prefix=resource_prefix,
                internet_facing=internet_facing,
                tooling_account_id=tooling_account_id,
                enable_cw_rum=enable_cw_rum,
                vpc=vpc,
                cognito_user_session_timeout_inmins=cognito_user_session_timeout_inmins,
                custom_waf_rules=custom_waf_rules,
                with_approval_tests=with_approval_tests,
                **kwargs,
            )
        else:
            cross_account_frontend_config_role = iam.Role(
                self,
                f'{resource_prefix}-{envname}-frontend-config-role',
                role_name=f'{resource_prefix}-{envname}-frontend-config-role',
                assumed_by=iam.AccountPrincipal(tooling_account_id),
                external_ids=[get_tooling_account_external_id(self.account)],
            )
            cross_account_frontend_config_role.add_to_policy(
                iam.PolicyStatement(
                    actions=[
                        'ssm:GetParameterHistory',
                        'ssm:GetParameters',
                        'ssm:GetParameter',
                        'ssm:GetParametersByPath',
                    ],
                    resources=[
                        f'arn:aws:ssm:*:{self.account}:parameter/*{resource_prefix}*',
                        f'arn:aws:ssm:*:{self.account}:parameter/*dataall*',
                    ],
                ),
            )

        sqs_stack = SqsStack(
            self,
            'SqsStack',
            envname=envname,
            resource_prefix=resource_prefix,
            prod_sizing=prod_sizing,
            **kwargs,
        )

        # Create the SES Stack
        ses_stack = self.create_ses_stack(custom_domain, envname, kwargs, resource_prefix)

        repo = ecr.Repository.from_repository_arn(self, 'ECRREPO', repository_arn=ecr_repository)
        if None not in [custom_domain, ses_stack]:
            email_sender = (
                custom_domain.get('email_notification_sender_email_id', 'noreply')
                + '@'
                + custom_domain.get('hosted_zone_name')
            )
        else:
            email_sender = 'none'

        self.lambda_api_stack = LambdaApiStack(
            self,
            'Lambdas',
            envname=envname,
            resource_prefix=resource_prefix,
            vpc=vpc,
            vpce_connection=vpce_connection,
            sqs_queue=sqs_stack.queue,
            image_tag=image_tag,
            ecr_repository=repo,
            internet_facing=internet_facing,
            ip_ranges=ip_ranges,
            apig_vpce=apig_vpce,
            prod_sizing=prod_sizing,
            user_pool=cognito_stack.user_pool if custom_auth is None else None,
            user_pool_client=cognito_stack.client if custom_auth is None else None,
            pivot_role_name=self.pivot_role_name,
            reauth_ttl=reauth_config.get('ttl', 5) if reauth_config else 5,
            email_notification_sender_email_id=email_sender,
            email_custom_domain=ses_stack.ses_identity.email_identity_name if ses_stack is not None else None,
            ses_configuration_set=ses_stack.configuration_set.configuration_set_name if ses_stack is not None else None,
            custom_domain=custom_domain,
            apigw_custom_domain=apigw_custom_domain,
            custom_auth=custom_auth,
            custom_waf_rules=custom_waf_rules,
            allowed_origins=allowed_origins,
            log_retention_duration=log_retention_duration,
            **kwargs,
        )

        self.ecs_stack = ContainerStack(
            self,
            'ECS',
            envname=envname,
            resource_prefix=resource_prefix,
            vpc=vpc,
            vpce_connection=vpce_connection,
            ecr_repository=repo,
            image_tag=image_tag,
            prod_sizing=prod_sizing,
            pivot_role_name=self.pivot_role_name,
            tooling_account_id=tooling_account_id,
            s3_prefix_list=self.s3_prefix_list,
            lambdas=[
                self.lambda_api_stack.aws_handler,
                self.lambda_api_stack.api_handler,
                self.lambda_api_stack.elasticsearch_proxy_handler,
            ],
            email_custom_domain=ses_stack.ses_identity.email_identity_name if ses_stack is not None else None,
            ses_configuration_set=ses_stack.configuration_set.configuration_set_name if ses_stack is not None else None,
            custom_domain=custom_domain,
            log_retention_duration=log_retention_duration,
            **kwargs,
        )

        quicksight_monitoring_sg = self.create_quicksight_role_sg_group(
            envname=envname, resource_prefix=resource_prefix, vpc=vpc
        )

        aurora_stack = AuroraServerlessStack(
            self,
            'Aurora',
            envname=envname,
            resource_prefix=resource_prefix,
            vpc=vpc,
            lambdas=[
                self.lambda_api_stack.aws_handler,
                self.lambda_api_stack.api_handler,
                self.lambda_api_stack.elasticsearch_proxy_handler,
            ],
            ecs_security_groups=self.ecs_stack.ecs_security_groups,
            prod_sizing=prod_sizing,
            quicksight_monitoring_sg=quicksight_monitoring_sg,
            **kwargs,
        )

        lambda_env_key = kms.Key(
            self,
            f'{resource_prefix}-trig-lambda-env-var-key',
            removal_policy=RemovalPolicy.DESTROY,
            alias=f'{resource_prefix}-trig-lambda-env-var-key',
            enable_key_rotation=True,
            policy=iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        resources=['*'],
                        effect=iam.Effect.ALLOW,
                        principals=[
                            iam.AccountPrincipal(account_id=self.account),
                        ],
                        actions=['kms:*'],
                    ),
                    iam.PolicyStatement(
                        resources=['*'],
                        effect=iam.Effect.ALLOW,
                        principals=[
                            iam.ServicePrincipal(service='lambda.amazonaws.com'),
                        ],
                        actions=['kms:GenerateDataKey*', 'kms:Decrypt'],
                    ),
                ],
            ),
        )

        db_snapshots = TriggerFunctionStack(
            self,
            'DbSnapshots',
            handler='deployment_triggers.dbsnapshots_handler.handler',
            envname=envname,
            resource_prefix=resource_prefix,
            vpc=vpc,
            vpce_connection=vpce_connection,
            image_tag=image_tag,
            ecr_repository=repo,
            execute_after=[aurora_stack.cluster],
            connectables=[aurora_stack.cluster],
            additional_policy_statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=['rds:AddTagsToResource', 'rds:CreateDBClusterSnapshot'],
                    resources=[
                        f'arn:aws:rds:*:{self.account}:cluster-snapshot:{resource_prefix}*',
                        f'arn:aws:rds:*:{self.account}:cluster:{resource_prefix}*',
                    ],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=['rds:DescribeDBClusters'],
                    resources=['*'],
                ),
            ],
            env_var_encryption_key=lambda_env_key,
            **kwargs,
        )

        db_migrations = TriggerFunctionStack(
            self,
            'DbMigrations',
            handler='deployment_triggers.dbmigrations_handler.handler',
            envname=envname,
            resource_prefix=resource_prefix,
            vpc=vpc,
            vpce_connection=vpce_connection,
            image_tag=image_tag,
            ecr_repository=repo,
            execute_after=[db_snapshots.trigger_function],
            connectables=[aurora_stack.cluster],
            env_var_encryption_key=lambda_env_key,
            **kwargs,
        )

        TriggerFunctionStack(
            self,
            'SavePerms',
            handler='deployment_triggers.saveperms_handler.handler',
            envname=envname,
            resource_prefix=resource_prefix,
            vpc=vpc,
            vpce_connection=vpce_connection,
            image_tag=image_tag,
            ecr_repository=repo,
            execute_after=[db_migrations.trigger_function],
            connectables=[aurora_stack.cluster],
            env_var_encryption_key=lambda_env_key,
            **kwargs,
        )

        if deploy_dms_stack:
            self.dms_stack = DMSTaskStack(
                self,
                'DMSTaskStack',
                secret_id_aurora_v1=old_aurora_connection_secret_arn,
                region=self.region,
                secret_id_aurora_v2=aurora_stack.db_credentials.secret_arn,
                kms_key_for_secret_arn=aurora_stack.kms_key.key_arn,
                database_name=aurora_stack.db_name,
                vpc_security_group=db_migrations.security_group.security_group_id,
                replication_subnet_group_identifier=f'default-{vpc.vpc_id}',
            )

        self.monitoring_stack = MonitoringStack(
            self,
            'CWDashboards',
            envname=envname,
            resource_prefix=resource_prefix,
            lambdas=[
                self.lambda_api_stack.aws_handler,
                self.lambda_api_stack.api_handler,
                self.lambda_api_stack.elasticsearch_proxy_handler,
            ],
            database=aurora_stack.cluster.cluster_identifier,
            ecs_cluster=self.ecs_stack.ecs_cluster,
            ecs_task_definitions_families=self.ecs_stack.ecs_task_definitions_families,
            backend_api=self.lambda_api_stack.backend_api_name,
            queue_name=sqs_stack.queue.queue_name,
            **kwargs,
        )

        self.opensearch_args = {
            'envname': envname,
            'resource_prefix': resource_prefix,
            'vpc': vpc,
            'vpc_endpoints_sg': vpc_endpoints_sg,
            'lambdas': [
                self.lambda_api_stack.aws_handler,
                self.lambda_api_stack.api_handler,
                self.lambda_api_stack.elasticsearch_proxy_handler,
            ],
            'ecs_security_groups': self.ecs_stack.ecs_security_groups,
            'ecs_task_role': self.ecs_stack.ecs_task_role,
            'prod_sizing': prod_sizing,
            'log_retention_duration': log_retention_duration,
            **kwargs,
        }
        if enable_opensearch_serverless:
            self.create_opensearch_serverless_stack()
        else:
            self.create_opensearch_stack()

        if enable_cw_rum and custom_auth is None:
            CloudWatchRumStack(
                self,
                'CWRumStack',
                envname=envname,
                resource_prefix=resource_prefix,
                tooling_account_id=tooling_account_id,
                cw_alarm_action=self.monitoring_stack.cw_alarm_action,
                cognito_identity_pool_id=cognito_stack.identity_pool.ref,
                cognito_identity_pool_role_arn=cognito_stack.identity_pool_role.role_arn,
                custom_domain_name=custom_domain.get('hosted_zone_name') if custom_domain else None,
            )

        if enable_cw_canaries:
            CloudWatchCanariesStack(
                self,
                'CWCanariesStack',
                envname=envname,
                resource_prefix=resource_prefix,
                vpc=vpc,
                logs_bucket=s3_resources_stack.logs_bucket,
                cw_alarm_action=self.monitoring_stack.cw_alarm_action,
                internet_facing=internet_facing,
            )

    @run_if(['core.features.enable_quicksight_monitoring'])
    def create_quicksight_role_sg_group(self, envname, resource_prefix, vpc):
        pivot_role_in_account = iam.Role(
            self,
            id='PivotRoleLimited',
            role_name='dataallPivotRole',
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal('lambda.amazonaws.com'),
                iam.AccountPrincipal(self.account),
            ),
        )

        pivot_role_in_account_policies = [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=['ssm:GetParametersByPath', 'ssm:GetParameters', 'ssm:GetParameter', 'ssm:PutParameter'],
                resources=[f'arn:aws:ssm:*:{self.account}:parameter/dataall*'],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=['secretsmanager:DescribeSecret', 'secretsmanager:GetSecretValue'],
                resources=[f'arn:aws:secretsmanager:*:{self.account}:secret:dataall*'],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    'ssm:DescribeParameters',
                    'quicksight:GetSessionEmbedUrl',
                    'quicksight:ListUserGroups',
                    'secretsmanager:ListSecrets',
                ],
                resources=['*'],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    'quicksight:RegisterUser',
                    'quicksight:DescribeUser',
                    'quicksight:DescribeGroup',
                    'quicksight:CreateGroup',
                    'quicksight:CreateGroupMembership',
                    'quicksight:UpdateUser',
                    'quicksight:CreateDataSource',
                    'quicksight:DescribeDataSource',
                    'quicksight:PassDataSource',
                    'quicksight:GetDashboardEmbedUrl',
                    'quicksight:DescribeDashboardPermissions',
                    'quicksight:SearchDashboards',
                    'quicksight:GetAuthCode',
                    'quicksight:CreateDataSet',
                ],
                resources=[
                    f'arn:aws:quicksight:*:{self.account}:user/*',
                    f'arn:aws:quicksight:*:{self.account}:group/*',
                    f'arn:aws:quicksight:*:{self.account}:datasource/*',
                    f'arn:aws:quicksight:*:{self.account}:dashboard/*',
                    f'arn:aws:quicksight:*:{self.account}:dataset/*',
                ],
            ),
        ]

        for policy in pivot_role_in_account_policies:
            pivot_role_in_account.add_to_policy(policy)

        quicksight_monitoring_sg = ec2.SecurityGroup(
            self,
            f'QuicksightMonitoringDBSG{envname}',
            security_group_name=f'{resource_prefix}-{envname}-quicksight-monitoring-sg',
            vpc=vpc,
            allow_all_outbound=False,
            disable_inline_rules=True,
        )
        return quicksight_monitoring_sg

    @run_if(['modules.datasets_base.features.share_notifications.email.active'])
    def create_ses_stack(self, custom_domain, envname, kwargs, resource_prefix):
        if custom_domain is None or None in [
            custom_domain.get('hosted_zone_name', None),
            custom_domain.get('hosted_zone_id', None),
        ]:
            raise Exception(
                'Cannot Create SES Stack For email notification as Custom Domain is not present or is missing hosted_zone_id or name. Either Disable Email Notification Config or add Custom Domain'
            )

        return SesStack(
            self,
            'SesStack',
            envname=envname,
            resource_prefix=resource_prefix,
            custom_domain=custom_domain,
            **kwargs,
        )

    def create_opensearch_stack(self):
        os_stack = OpenSearchStack(self, 'OpenSearch', **self.opensearch_args)
        self.monitoring_stack.set_es_alarms(
            alarm_name=f'{self.resource_prefix}-{self.envname}-opensearch-alarm',
            domain_name=os_stack.domain_name,
        )

    def create_opensearch_serverless_stack(self):
        aoss_stack = OpenSearchServerlessStack(self, 'OpenSearchServerless', **self.opensearch_args)
        self.monitoring_stack.set_aoss_alarms(
            alarm_name=f'{self.resource_prefix}-{self.envname}-opensearch-serverless-alarm',
            collection_id=aoss_stack.collection_id,
            collection_name=aoss_stack.collection_name,
        )

    def get_s3_prefix_list(self):
        try:
            ec2_client = boto3.client('ec2', region_name=self.region)
            response = ec2_client.describe_prefix_lists(
                Filters=[
                    {'Name': 'prefix-list-name', 'Values': [f'com.amazonaws.{self.region}.s3']},
                ]
            )
        except Exception as e:
            print(e)
            return ''
        return response['PrefixLists'][0].get('PrefixListId')

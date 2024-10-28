import json
import os

from aws_cdk import (
    aws_iam as iam,
    aws_apigateway as apigw,
    aws_lambda as _lambda,
    aws_lambda_event_sources as lambda_event_sources,
    aws_lambda_destinations as lambda_destination,
    aws_wafv2 as wafv2,
    aws_ssm as ssm,
    aws_sns as sns,
    aws_ec2 as ec2,
    aws_kms as kms,
    aws_sqs as sqs,
    aws_logs as logs,
    Duration,
    CfnOutput,
    Fn,
    RemovalPolicy,
    BundlingOptions,
)
from aws_cdk.aws_ec2 import (
    InterfaceVpcEndpoint,
    InterfaceVpcEndpointAwsService,
    Port,
    Peer,
)

from .pyNestedStack import pyNestedClass
from .solution_bundling import SolutionBundling
from .waf_rules import get_waf_rules
from .run_if import run_if


class LambdaApiStack(pyNestedClass):
    def __init__(
        self,
        scope,
        id,
        envname='dev',
        resource_prefix='dataall',
        vpc=None,
        vpce_connection=None,
        sqs_queue: sqs.Queue = None,
        ecr_repository=None,
        image_tag=None,
        internet_facing=True,
        custom_waf_rules=None,
        ip_ranges=None,
        apig_vpce=None,
        prod_sizing=False,
        user_pool=None,
        pivot_role_name=None,
        reauth_ttl=5,
        email_notification_sender_email_id=None,
        email_custom_domain=None,
        ses_configuration_set=None,
        custom_domain=None,
        custom_auth=None,
        allowed_origins='*',
        log_retention_duration=None,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        self.log_retention_duration = log_retention_duration

        if self.node.try_get_context('image_tag'):
            image_tag = self.node.try_get_context('image_tag')

        image_tag = f'lambdas-{image_tag}'

        lambda_env_key = kms.Key(
            self,
            f'{resource_prefix}-lambda-env-var-key',
            removal_policy=RemovalPolicy.DESTROY,
            alias=f'{resource_prefix}-lambda-env-var-key',
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

        self.esproxy_dlq = self.set_dlq(f'{resource_prefix}-{envname}-esproxy-dlq')
        esproxy_sg = self.create_lambda_sgs(envname, 'esproxy', resource_prefix, vpc)
        esproxy_env = {'envname': envname, 'LOG_LEVEL': 'INFO', 'ALLOWED_ORIGINS': allowed_origins}
        if custom_auth:
            esproxy_env['custom_auth'] = custom_auth.get('provider', None)
        self.elasticsearch_proxy_handler = _lambda.DockerImageFunction(
            self,
            'ElasticSearchProxyHandler',
            function_name=f'{resource_prefix}-{envname}-esproxy',
            log_group=logs.LogGroup(
                self,
                'esproxyloggroup',
                log_group_name=f'/aws/lambda/{resource_prefix}-{envname}-backend-esproxy',
                retention=getattr(logs.RetentionDays, self.log_retention_duration),
            ),
            description='dataall es search function',
            role=self.create_function_role(envname, resource_prefix, 'esproxy', pivot_role_name, vpc),
            code=_lambda.DockerImageCode.from_ecr(
                repository=ecr_repository, tag=image_tag, cmd=['search_handler.handler']
            ),
            vpc=vpc,
            security_groups=[esproxy_sg],
            memory_size=1664 if prod_sizing else 256,
            timeout=Duration.minutes(15),
            environment=esproxy_env,
            environment_encryption=lambda_env_key,
            dead_letter_queue_enabled=True,
            dead_letter_queue=self.esproxy_dlq,
            on_failure=lambda_destination.SqsDestination(self.esproxy_dlq),
            tracing=_lambda.Tracing.ACTIVE,
        )

        self.api_handler_dlq = self.set_dlq(f'{resource_prefix}-{envname}-graphql-dlq')
        api_handler_sg = self.create_lambda_sgs(envname, 'apihandler', resource_prefix, vpc)
        api_handler_env = {
            'envname': envname,
            'LOG_LEVEL': 'INFO',
            'REAUTH_TTL': str(reauth_ttl),
            'ALLOWED_ORIGINS': allowed_origins,
        }
        # Check if custom domain exists and if it exists email notifications could be enabled. Create a env variable which stores the domain url. This is used for sending data.all share weblinks in the email notifications.
        if custom_domain and custom_domain.get('hosted_zone_name', None):
            api_handler_env['frontend_domain_url'] = f'https://{custom_domain.get("hosted_zone_name", None)}'
        if custom_auth:
            api_handler_env['custom_auth'] = custom_auth.get('provider', None)
        self.api_handler = _lambda.DockerImageFunction(
            self,
            'LambdaGraphQL',
            function_name=f'{resource_prefix}-{envname}-graphql',
            log_group=logs.LogGroup(
                self,
                'graphqlloggroup',
                log_group_name=f'/aws/lambda/{resource_prefix}-{envname}-backend-graphql',
                retention=getattr(logs.RetentionDays, self.log_retention_duration),
            ),
            description='dataall graphql function',
            role=self.create_function_role(
                envname, resource_prefix, 'graphql', pivot_role_name, vpc, self._get_bedrock_policy_statement() or []
            ),
            code=_lambda.DockerImageCode.from_ecr(
                repository=ecr_repository, tag=image_tag, cmd=['api_handler.handler']
            ),
            vpc=vpc,
            security_groups=[api_handler_sg],
            memory_size=3008 if prod_sizing else 1024,
            timeout=Duration.minutes(15),
            environment=api_handler_env,
            environment_encryption=lambda_env_key,
            dead_letter_queue_enabled=True,
            dead_letter_queue=self.api_handler_dlq,
            on_failure=lambda_destination.SqsDestination(self.api_handler_dlq),
            tracing=_lambda.Tracing.ACTIVE,
        )

        self.aws_handler_dlq = self.set_dlq(f'{resource_prefix}-{envname}-awsworker-dlq')
        awsworker_sg = self.create_lambda_sgs(envname, 'awsworker', resource_prefix, vpc)
        awshandler_env = {
            'envname': envname,
            'LOG_LEVEL': 'INFO',
            'email_sender_id': email_notification_sender_email_id,
        }
        self.aws_handler = _lambda.DockerImageFunction(
            self,
            'AWSWorker',
            function_name=f'{resource_prefix}-{envname}-awsworker',
            log_group=logs.LogGroup(
                self,
                'awsworkerloggroup',
                log_group_name=f'/aws/lambda/{resource_prefix}-{envname}-backend-awsworker',
                retention=getattr(logs.RetentionDays, self.log_retention_duration),
            ),
            description='dataall aws worker for aws asynchronous tasks function',
            role=self.create_function_role(envname, resource_prefix, 'awsworker', pivot_role_name, vpc),
            code=_lambda.DockerImageCode.from_ecr(
                repository=ecr_repository, tag=image_tag, cmd=['aws_handler.handler']
            ),
            environment=awshandler_env,
            environment_encryption=lambda_env_key,
            memory_size=1664 if prod_sizing else 256,
            timeout=Duration.minutes(15),
            vpc=vpc,
            security_groups=[awsworker_sg],
            dead_letter_queue_enabled=True,
            dead_letter_queue=self.aws_handler_dlq,
            on_failure=lambda_destination.SqsDestination(self.aws_handler_dlq),
            tracing=_lambda.Tracing.ACTIVE,
        )
        self.aws_handler.add_event_source(
            lambda_event_sources.SqsEventSource(
                queue=sqs_queue,
                batch_size=1,
            )
        )

        # Add the SES Sendemail policy
        if email_custom_domain is not None:
            self.aws_handler.add_to_role_policy(
                iam.PolicyStatement(
                    actions=['ses:SendEmail'],
                    resources=[
                        f'arn:aws:ses:{self.region}:{self.account}:identity/{email_custom_domain}',
                        f'arn:aws:ses:{self.region}:{self.account}:configuration-set/{ses_configuration_set}',
                    ],
                )
            )

        if custom_auth is not None:
            # Create the custom authorizer lambda
            custom_authorizer_assets = os.path.realpath(
                os.path.join(
                    os.path.dirname(__file__),
                    '..',
                    'custom_resources',
                    'custom_authorizer',
                )
            )

            if not os.path.isdir(custom_authorizer_assets):
                raise Exception(f'Custom Authorizer Folder not found at {custom_authorizer_assets}')

            custom_lambda_env = {
                'envname': envname,
                'LOG_LEVEL': 'DEBUG',
                'custom_auth_provider': custom_auth.get('provider'),
                'custom_auth_url': custom_auth.get('url'),
                'custom_auth_client': custom_auth.get('client_id'),
                'custom_auth_jwks_url': custom_auth.get('jwks_url'),
            }

            for claims_map in custom_auth.get('claims_mapping', {}):
                custom_lambda_env[claims_map] = custom_auth.get('claims_mapping', '').get(claims_map, '')

            authorizer_fn_sg = self.create_lambda_sgs(envname, 'customauthorizer', resource_prefix, vpc)
            self.authorizer_fn = _lambda.Function(
                self,
                f'CustomAuthorizerFunction-{envname}',
                function_name=f'{resource_prefix}-{envname}-custom-authorizer',
                log_group=logs.LogGroup(
                    self,
                    'customauthorizerloggroup',
                    log_group_name=f'/aws/lambda/{resource_prefix}-{envname}-custom-authorizer',
                    retention=getattr(logs.RetentionDays, self.log_retention_duration),
                ),
                handler='custom_authorizer_lambda.lambda_handler',
                code=_lambda.Code.from_asset(
                    path=custom_authorizer_assets,
                    bundling=BundlingOptions(
                        image=_lambda.Runtime.PYTHON_3_9.bundling_image,
                        local=SolutionBundling(source_path=custom_authorizer_assets),
                    ),
                ),
                memory_size=512 if prod_sizing else 256,
                description='dataall Custom authorizer replacing cognito authorizer',
                timeout=Duration.seconds(20),
                environment=custom_lambda_env,
                environment_encryption=lambda_env_key,
                vpc=vpc,
                security_groups=[authorizer_fn_sg],
                runtime=_lambda.Runtime.PYTHON_3_9,
            )

            # Add NAT Connectivity For Custom Authorizer Lambda
            self.authorizer_fn.connections.allow_to(
                ec2.Peer.any_ipv4(), ec2.Port.tcp(443), 'Allow NAT Internet Access SG Egress'
            )

            # Store custom authorizer's ARN in ssm
            ssm.StringParameter(
                self,
                f'{resource_prefix}-{envname}-custom-authorizer-arn',
                parameter_name=f'/dataall/{envname}/customauth/customauthorizerarn',
                string_value=self.authorizer_fn.function_arn,
            )

        # Add VPC Endpoint Connectivity
        if vpce_connection:
            for lmbda in [
                self.aws_handler,
                self.api_handler,
                self.elasticsearch_proxy_handler,
            ]:
                lmbda.connections.allow_from(
                    vpce_connection,
                    ec2.Port.tcp_range(start_port=1024, end_port=65535),
                    'Allow Lambda from VPC Endpoint',
                )
                lmbda.connections.allow_to(vpce_connection, ec2.Port.tcp(443), 'Allow Lambda to VPC Endpoint')

        # Add NAT Connectivity For API Handler
        self.api_handler.connections.allow_to(
            ec2.Peer.any_ipv4(), ec2.Port.tcp(443), 'Allow NAT Internet Access SG Egress'
        )
        self.aws_handler.connections.allow_to(
            ec2.Peer.any_ipv4(), ec2.Port.tcp(443), 'Allow NAT Internet Access SG Egress'
        )

        self.backend_api_name = f'{resource_prefix}-{envname}-api'

        self.graphql_api, self.acl = self.create_api_gateway(
            apig_vpce,
            envname,
            internet_facing,
            custom_waf_rules,
            ip_ranges,
            resource_prefix,
            vpc,
            user_pool,
            custom_auth,
        )

        self.create_sns_topic(
            envname=envname,
            construct_id='BackendTopic',
            lambda_function=self.api_handler,
            param_name='backend_sns_topic_arn',
            topic_name=f'{resource_prefix}-{envname}-backend-topic',
        )

    def create_lambda_sgs(self, envname, name, resource_prefix, vpc):
        lambda_sg = ec2.SecurityGroup(
            self,
            f'{name}SG{envname}',
            security_group_name=f'{resource_prefix}-{envname}-{name}-sg',
            vpc=vpc,
            allow_all_outbound=False,
            disable_inline_rules=True,
        )
        return lambda_sg

    @run_if(['modules.worksheets.features.nlq.active'])
    def _get_bedrock_policy_statement(self):
        return [
            iam.PolicyStatement(
                actions=[
                    'bedrock:InvokeModel',
                    'bedrock:GetPrompt',
                    'bedrock:CreateFoundationModelAgreement',
                    'bedrock:InvokeFlow',
                ],
                resources=[
                    f'arn:aws:bedrock:{self.region}:{self.account}:flow/*',
                    f'arn:aws:bedrock:{self.region}:{self.account}:prompt/*',
                    f'arn:aws:bedrock:{self.region}::foundation-model/*',
                ],
            )
        ]

    def create_function_role(self, envname, resource_prefix, fn_name, pivot_role_name, vpc, extra_statements=[]):
        role_name = f'{resource_prefix}-{envname}-{fn_name}-role'

        role_inline_policy = iam.Policy(
            self,
            f'{resource_prefix}-{envname}-{fn_name}-policy',
            policy_name=f'{resource_prefix}-{envname}-{fn_name}-policy',
            statements=[
                iam.PolicyStatement(
                    actions=[
                        'secretsmanager:GetSecretValue',
                        'kms:Decrypt',
                        'secretsmanager:DescribeSecret',
                        'ecs:RunTask',
                        'kms:Encrypt',
                        'sqs:ReceiveMessage',
                        'kms:GenerateDataKey',
                        'sqs:SendMessage',
                        'ecs:DescribeClusters',
                        'ssm:GetParametersByPath',
                        'ssm:GetParameters',
                        'ssm:GetParameter',
                    ],
                    resources=[
                        f'arn:aws:secretsmanager:{self.region}:{self.account}:secret:*{resource_prefix}*',
                        f'arn:aws:secretsmanager:{self.region}:{self.account}:secret:*dataall*',
                        f'arn:aws:ecs:{self.region}:{self.account}:cluster/*{resource_prefix}*',
                        f'arn:aws:ecs:{self.region}:{self.account}:task-definition/*{resource_prefix}*:*',
                        f'arn:aws:kms:{self.region}:{self.account}:key/*',
                        f'arn:aws:sqs:{self.region}:{self.account}:*{resource_prefix}*',
                        f'arn:aws:ssm:*:{self.account}:parameter/*dataall*',
                        f'arn:aws:ssm:*:{self.account}:parameter/*{resource_prefix}*',
                    ],
                ),
                iam.PolicyStatement(
                    actions=[
                        'sts:AssumeRole',
                    ],
                    resources=[
                        f'arn:aws:iam::*:role/{pivot_role_name}*',
                        'arn:aws:iam::*:role/cdk-hnb659fds-lookup-role-*',
                    ],
                ),
                iam.PolicyStatement(
                    actions=[
                        'ecs:ListTasks',
                    ],
                    resources=['*'],
                    conditions={
                        'ArnEquals': {
                            'ecs:cluster': f'arn:aws:ecs:{self.region}:{self.account}:cluster/*{resource_prefix}*'
                        }
                    },
                ),
                iam.PolicyStatement(
                    actions=[
                        'iam:PassRole',
                    ],
                    resources=[f'arn:aws:iam::{self.account}:role/{resource_prefix}-{envname}*'],
                ),
                iam.PolicyStatement(
                    actions=[
                        's3:GetObject',
                        's3:ListBucketVersions',
                        's3:ListBucket',
                        's3:GetBucketLocation',
                        's3:GetObjectVersion',
                        'logs:StartQuery',
                        'logs:DescribeLogGroups',
                        'logs:DescribeLogStreams',
                        'logs:DescribeQueries',
                        'logs:StopQuery',
                        'logs:GetQueryResults',
                        'logs:CreateLogGroup',
                        'logs:CreateLogStream',
                        'logs:PutLogEvents',
                    ],
                    resources=[
                        f'arn:aws:s3:::{resource_prefix}-{envname}-{self.account}-{self.region}-resources/*',
                        f'arn:aws:s3:::{resource_prefix}-{envname}-{self.account}-{self.region}-resources',
                        f'arn:aws:logs:{self.region}:{self.account}:log-group:*{resource_prefix}*:log-stream:*',
                        f'arn:aws:logs:{self.region}:{self.account}:log-group:*{resource_prefix}*',
                    ],
                ),
                iam.PolicyStatement(
                    actions=[
                        'ec2:DescribeNetworkInterfaces',
                        'xray:PutTraceSegments',
                        'xray:PutTelemetryRecords',
                        'xray:GetSamplingRules',
                        'xray:GetSamplingTargets',
                        'xray:GetSamplingStatisticSummaries',
                        'cognito-idp:ListGroups',
                        'cognito-idp:ListUsersInGroup',
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
                    conditions={'StringEquals': {'ec2:VpcID': f'{vpc.vpc_id}'}},
                ),
                iam.PolicyStatement(
                    actions=[
                        'aoss:APIAccessAll',
                    ],
                    resources=[
                        f'arn:aws:aoss:{self.region}:{self.account}:collection/*',
                    ],
                ),
                iam.PolicyStatement(
                    actions=['events:EnableRule', 'events:DisableRule'],
                    resources=[f'arn:aws:events:{self.region}:{self.account}:rule/dataall*'],
                ),
            ]
            + extra_statements,
        )
        role = iam.Role(
            self,
            role_name,
            role_name=role_name,
            inline_policies={f'{resource_prefix}-{envname}-{fn_name}-inline': role_inline_policy.document},
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
        )
        return role

    def create_api_gateway(
        self,
        apig_vpce,
        envname,
        internet_facing,
        custom_waf_rules,
        ip_ranges,
        resource_prefix,
        vpc,
        user_pool,
        custom_auth,
    ):
        api_deploy_options = apigw.StageOptions(
            throttling_rate_limit=10000,
            throttling_burst_limit=5000,
            logging_level=apigw.MethodLoggingLevel.INFO,
            tracing_enabled=True,
            data_trace_enabled=True,
            metrics_enabled=True,
        )

        graphql_api = self.set_up_graphql_api_gateway(
            api_deploy_options,
            self.api_handler,
            self.backend_api_name,
            self.elasticsearch_proxy_handler,
            envname,
            internet_facing,
            vpc,
            ip_ranges,
            apig_vpce,
            resource_prefix,
            user_pool,
            custom_auth,
        )

        # Create IP set if IP filtering enabled in CDK.json
        ip_set_regional = None
        if custom_waf_rules and custom_waf_rules.get('allowed_ip_list'):
            ip_set_regional = wafv2.CfnIPSet(
                self,
                'DataallRegionalIPSet',
                name=f'{resource_prefix}-{envname}-ipset-regional',
                description=f'IP addresses allowed for Dataall {envname}',
                addresses=custom_waf_rules.get('allowed_ip_list'),
                ip_address_version='IPV4',
                scope='REGIONAL',
            )

        acl = wafv2.CfnWebACL(
            self,
            'ACL-ApiGW',
            default_action=wafv2.CfnWebACL.DefaultActionProperty(allow={}),
            scope='REGIONAL',
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name='waf-apigw',
                sampled_requests_enabled=True,
            ),
            rules=get_waf_rules(envname, 'APIGateway', custom_waf_rules, ip_set_regional),
        )

        wafv2.CfnWebACLAssociation(
            self,
            'WafApiGW',
            resource_arn=f'arn:aws:apigateway:{self.region}::'
            f'/restapis/{graphql_api.rest_api_id}/stages/{graphql_api.deployment_stage.stage_name}',
            web_acl_arn=acl.get_att('Arn').to_string(),
        )

        CfnOutput(
            self,
            f'WebAclId{envname}',
            export_name=f'{resource_prefix}-{envname}-api-webacl',
            value=Fn.select(0, Fn.split('|', Fn.ref(acl.logical_id))),
        )
        CfnOutput(self, f'Url{envname}', value=graphql_api.url)

        return graphql_api, acl

    def set_up_graphql_api_gateway(
        self,
        api_deploy_options,
        api_handler,
        backend_api_name,
        elasticsearch_proxy_handler,
        envname,
        internet_facing,
        vpc: ec2.Vpc,
        ip_ranges,
        apig_vpce,
        resource_prefix,
        user_pool,
        custom_auth,
    ):
        if custom_auth is None:
            cognito_authorizer = apigw.CognitoUserPoolsAuthorizer(
                self,
                'CognitoAuthorizer',
                cognito_user_pools=[user_pool],
                authorizer_name=f'{resource_prefix}-{envname}-cognito-authorizer',
                identity_source='method.request.header.Authorization',
                results_cache_ttl=Duration.minutes(60),
            )
        else:
            # Create a custom Authorizer
            custom_authorizer_role = iam.Role(
                self,
                f'{resource_prefix}-{envname}-custom-authorizer-role',
                role_name=f'{resource_prefix}-{envname}-custom-authorizer-role',
                assumed_by=iam.ServicePrincipal('apigateway.amazonaws.com'),
                description='Allow Custom Authorizer to call custom auth lambda',
            )
            custom_authorizer_role.add_to_policy(
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=['lambda:InvokeFunction'],
                    resources=[self.authorizer_fn.function_arn],
                )
            )

            custom_authorizer = apigw.RequestAuthorizer(
                self,
                'CustomAuthorizer',
                handler=self.authorizer_fn,
                identity_sources=[apigw.IdentitySource.header('Authorization')],
                authorizer_name=f'{resource_prefix}-{envname}-custom-authorizer',
                assume_role=custom_authorizer_role,
                results_cache_ttl=Duration.minutes(60),
            )
        if not internet_facing:
            if apig_vpce:
                api_vpc_endpoint = InterfaceVpcEndpoint.from_interface_vpc_endpoint_attributes(
                    self,
                    f'APIVpcEndpoint{envname}',
                    vpc_endpoint_id=apig_vpce,
                    port=443,
                )
            else:
                api_vpc_endpoint = InterfaceVpcEndpoint(
                    self,
                    f'APIVpcEndpoint{envname}',
                    vpc=vpc,
                    service=InterfaceVpcEndpointAwsService.APIGATEWAY,
                    private_dns_enabled=True,
                )
                api_vpc_endpoint.connections.allow_from(
                    Peer.ipv4(vpc.vpc_cidr_block), Port.tcp(443), 'Allow inbound HTTPS'
                )

            api_vpc_endpoint_id = api_vpc_endpoint.vpc_endpoint_id
            api_policy = iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        principals=[iam.AnyPrincipal()],
                        actions=['execute-api:Invoke'],
                        resources=['execute-api:/*'],
                        effect=iam.Effect.DENY,
                        conditions={'StringNotEquals': {'aws:SourceVpce': api_vpc_endpoint_id}},
                    ),
                    iam.PolicyStatement(
                        principals=[iam.AnyPrincipal()],
                        actions=['execute-api:Invoke'],
                        resources=['execute-api:/*'],
                        effect=iam.Effect.ALLOW,
                    ),
                ]
            )
            gw = apigw.RestApi(
                self,
                backend_api_name,
                rest_api_name=backend_api_name,
                deploy_options=api_deploy_options,
                endpoint_configuration=apigw.EndpointConfiguration(
                    types=[apigw.EndpointType.PRIVATE], vpc_endpoints=[api_vpc_endpoint]
                ),
                policy=api_policy,
            )
        else:
            gw = apigw.RestApi(
                self,
                backend_api_name,
                rest_api_name=backend_api_name,
                deploy_options=api_deploy_options,
            )
        api_url = gw.url
        integration = apigw.LambdaIntegration(api_handler)
        request_validator = apigw.RequestValidator(
            self,
            f'{resource_prefix}-{envname}-api-validator',
            rest_api=gw,
            validate_request_body=True,
        )
        graphql_validation_model = apigw.Model(
            self,
            'GraphQLValidationModel',
            rest_api=gw,
            schema=apigw.JsonSchema(
                schema=apigw.JsonSchemaVersion.DRAFT4,
                title='GraphQL',
                type=apigw.JsonSchemaType.OBJECT,
                properties={
                    'operationName': apigw.JsonSchema(
                        type=apigw.JsonSchemaType.STRING,
                        description='GraphQL Operation name',
                    ),
                    'query': apigw.JsonSchema(
                        type=apigw.JsonSchemaType.STRING,
                        description='GraphQL operation body',
                    ),
                    'variables': apigw.JsonSchema(
                        type=apigw.JsonSchemaType.OBJECT,
                        description='GraphQL operation variables',
                    ),
                },
                required=['operationName', 'query', 'variables'],
            ),
        )
        ssm.StringParameter(
            self,
            'BackendApi',
            parameter_name=f'/dataall/{envname}/apiGateway/backendUrl',
            string_value=api_url,
        )
        graphql = gw.root.add_resource(path_part='graphql')
        graphql_proxy = graphql.add_resource(
            path_part='{proxy+}',
            default_integration=integration,
            default_cors_preflight_options=apigw.CorsOptions(
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_headers=['*'],
            ),
        )
        graphql_proxy.add_method(
            'POST',
            authorizer=cognito_authorizer if custom_auth is None else custom_authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
            if custom_auth is None
            else apigw.AuthorizationType.CUSTOM,
            request_validator=request_validator,
            request_models={'application/json': graphql_validation_model},
        )

        search_integration = apigw.LambdaIntegration(elasticsearch_proxy_handler)
        search = gw.root.add_resource(path_part='search')
        search_validation_model = apigw.Model(
            self,
            'SearchValidationModel',
            rest_api=gw,
            schema=apigw.JsonSchema(
                schema=apigw.JsonSchemaVersion.DRAFT4,
                title='SearchAPI',
                type=apigw.JsonSchemaType.OBJECT,
                properties={
                    'preference': apigw.JsonSchema(
                        type=apigw.JsonSchemaType.STRING,
                        description='Search Preference',
                    ),
                    'query': apigw.JsonSchema(
                        type=apigw.JsonSchemaType.OBJECT,
                        description='Search Query',
                    ),
                },
                required=['preference', 'query'],
            ),
        )
        search_proxy = search.add_resource(
            path_part='{proxy+}',
            default_integration=search_integration,
            default_cors_preflight_options=apigw.CorsOptions(
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_headers=['*'],
            ),
        )
        search_proxy.add_method(
            'POST',
            authorizer=cognito_authorizer if custom_auth is None else custom_authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
            if custom_auth is None
            else apigw.AuthorizationType.CUSTOM,
            request_validator=request_validator,
            request_models={'application/json': search_validation_model},
        )

        apigateway_log_group = logs.LogGroup(
            self,
            f'{resource_prefix}/{envname}/apigateway',
            log_group_name=f'{resource_prefix}/{envname}/apigateway',
            removal_policy=RemovalPolicy.DESTROY,
            retention=getattr(logs.RetentionDays, self.log_retention_duration),
        )

        iam_policy = iam.PolicyDocument(
            assign_sids=True,
            statements=[
                iam.PolicyStatement(
                    actions=[
                        'logs:CreateLogStream',
                        'logs:PutLogEvents',
                        'logs:DescribeLogGroups',
                        'logs:DescribeLogStreams',
                    ],
                    effect=iam.Effect.ALLOW,
                    resources=[apigateway_log_group.log_group_arn],
                )
            ],
        )

        iam.Role(
            self,
            f'{resource_prefix}-{envname}-apigatewaylogs-role',
            assumed_by=iam.ServicePrincipal('apigateway.amazonaws.com'),
            inline_policies={f'{resource_prefix}-{envname}-apigateway-policy': iam_policy},
        )
        stage: apigw.CfnStage = gw.deployment_stage.node.default_child
        stage.access_log_setting = apigw.CfnStage.AccessLogSettingProperty(
            destination_arn=apigateway_log_group.log_group_arn,
            format=json.dumps(
                {
                    'requestId': '$context.requestId',
                    'userAgent': '$context.identity.userAgent',
                    'sourceIp': '$context.identity.sourceIp',
                    'requestTime': '$context.requestTime',
                    'requestTimeEpoch': '$context.requestTimeEpoch',
                    'httpMethod': '$context.httpMethod',
                    'path': '$context.path',
                    'status': '$context.status',
                    'protocol': '$context.protocol',
                    'responseLength': '$context.responseLength',
                    'domainName': '$context.domainName',
                }
            ),
        )
        return gw

    @staticmethod
    def get_api_resource_policy(vpc, ip_ranges):
        statements = [
            iam.PolicyStatement(
                principals=[iam.AnyPrincipal()],
                actions=['execute-api:Invoke'],
                resources=['execute-api:/*'],
                effect=iam.Effect.DENY,
                conditions={'NotIpAddress': {'aws:VpcSourceIp': vpc.vpc_cidr_block}},
            ),
            iam.PolicyStatement(
                principals=[iam.AnyPrincipal()],
                actions=['execute-api:Invoke'],
                resources=['execute-api:/*'],
                effect=iam.Effect.ALLOW,
            ),
        ]
        if ip_ranges:
            statements.append(
                iam.PolicyStatement(
                    principals=[iam.AnyPrincipal()],
                    actions=['execute-api:Invoke'],
                    resources=['execute-api:/*'],
                    effect=iam.Effect.DENY,
                    conditions={'NotIpAddress': {'aws:SourceIp': ip_ranges}},
                )
            )
        api_policy = iam.PolicyDocument(statements=statements)
        return api_policy

    def create_sns_topic(self, construct_id, envname, lambda_function, param_name, topic_name=None):
        key = kms.Key(
            self,
            topic_name,
            removal_policy=RemovalPolicy.DESTROY,
            alias=topic_name,
            enable_key_rotation=True,
        )
        topic = sns.Topic(self, construct_id, topic_name=topic_name, master_key=key)
        ssm.StringParameter(
            self,
            f'{construct_id}Parameter',
            parameter_name=f'/dataall/{envname}/sns_topics/{param_name}',
            string_value=topic.topic_arn,
        )
        service_principal_name = 'sns.amazonaws.com'
        lambda_function.add_permission(
            f'{construct_id}Permission',
            action='lambda:InvokeFunction',
            principal=iam.ServicePrincipal(service_principal_name),
            source_arn=topic.topic_arn,
        )
        sns.Subscription(
            self,
            f'{construct_id}Subscription',
            protocol=sns.SubscriptionProtocol.LAMBDA,
            topic=topic,
            endpoint=lambda_function.function_arn,
        )
        return topic

    def set_dlq(self, queue_name) -> sqs.Queue:
        queue_key = kms.Key(
            self,
            f'{queue_name}-key',
            removal_policy=RemovalPolicy.DESTROY,
            alias=f'{queue_name}-key',
            enable_key_rotation=True,
        )

        dlq = sqs.Queue(
            self,
            f'{queue_name}-queue',
            queue_name=f'{queue_name}',
            retention_period=Duration.days(14),
            encryption=sqs.QueueEncryption.KMS,
            encryption_master_key=queue_key,
            data_key_reuse=Duration.days(1),
            removal_policy=RemovalPolicy.DESTROY,
        )

        enforce_tls_statement = iam.PolicyStatement(
            sid='Enforce TLS for all principals',
            effect=iam.Effect.DENY,
            principals=[
                iam.AnyPrincipal(),
            ],
            actions=[
                'sqs:*',
            ],
            resources=[dlq.queue_arn],
            conditions={
                'Bool': {'aws:SecureTransport': 'false'},
            },
        )

        dlq.add_to_resource_policy(enforce_tls_statement)
        return dlq

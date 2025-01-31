from typing import List

from aws_cdk import Duration
from aws_cdk import (
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_ecr as ecr,
    aws_lambda as _lambda,
)
from aws_cdk.aws_kms import IKey
from aws_cdk.triggers import TriggerFunction
from constructs import Construct

from .pyNestedStack import pyNestedClass


class TriggerFunctionStack(pyNestedClass):
    def __init__(
        self,
        scope: Construct,
        id: str,
        ecr_repository: ecr.IRepository,
        image_tag: str,
        handler: str,
        envname='dev',
        resource_prefix='dataall',
        vpc: ec2.IVpc = None,
        vpce_connection: ec2.IConnectable = None,
        connectables: List[ec2.IConnectable] = [],
        execute_after: List[Construct] = [],
        additional_policy_statements: List[iam.PolicyStatement] = [],
        env_var_encryption_key: IKey = None,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        if self.node.try_get_context('image_tag'):
            image_tag = self.node.try_get_context('image_tag')
        image_tag = f'lambdas-{image_tag}'

        env = {'envname': envname, 'resource_prefix': resource_prefix, 'LOG_LEVEL': 'INFO'}

        function_sgs = self.create_lambda_sgs(envname, handler, resource_prefix, vpc)
        statements = self.get_policy_statements(resource_prefix) + (additional_policy_statements or [])
        self.trigger_function = TriggerFunction(
            self,
            f'TriggerFunction-{handler}',
            function_name=f'{resource_prefix}-{envname}-{handler.replace(".", "_")}',
            description=f'dataall {handler} trigger function',
            initial_policy=statements,
            code=_lambda.Code.from_ecr_image(repository=ecr_repository, tag=image_tag, cmd=[handler]),
            vpc=vpc,
            security_groups=[function_sgs],
            memory_size=256,
            timeout=Duration.minutes(15),
            environment=env,
            environment_encryption=env_var_encryption_key,
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            runtime=_lambda.Runtime.FROM_IMAGE,
            handler=_lambda.Handler.FROM_IMAGE,
            execute_after=execute_after,
            execute_on_handler_change=True,
        )

        for connectable in connectables:
            function_sgs.connections.allow_to_default_port(
                connectable, f'Allow dataall {self.trigger_function.function_name}'
            )

        if vpce_connection:
            self.trigger_function.connections.allow_from(
                vpce_connection,
                ec2.Port.tcp_range(start_port=1024, end_port=65535),
                'Allow Lambda from VPC Endpoint',
            )
            self.trigger_function.connections.allow_to(
                vpce_connection, ec2.Port.tcp(443), 'Allow Lambda to VPC Endpoint'
            )

        self.trigger_function.connections.allow_to(
            ec2.Peer.any_ipv4(), ec2.Port.tcp(443), 'Allow NAT Internet Access SG Egress'
        )
        self.security_group = function_sgs

    def get_policy_statements(self, resource_prefix) -> List[iam.PolicyStatement]:
        return [
            iam.PolicyStatement(
                actions=[
                    'secretsmanager:GetSecretValue',
                    'kms:Decrypt',
                    'secretsmanager:DescribeSecret',
                    'kms:Encrypt',
                    'kms:GenerateDataKey',
                    'ssm:GetParametersByPath',
                    'ssm:GetParameters',
                    'ssm:GetParameter',
                ],
                resources=[
                    f'arn:aws:secretsmanager:{self.region}:{self.account}:secret:*{resource_prefix}*',
                    f'arn:aws:secretsmanager:{self.region}:{self.account}:secret:*dataall*',
                    f'arn:aws:kms:{self.region}:{self.account}:key/*',
                    f'arn:aws:ssm:*:{self.account}:parameter/*dataall*',
                    f'arn:aws:ssm:*:{self.account}:parameter/*{resource_prefix}*',
                ],
            ),
        ]

    def create_lambda_sgs(self, envname, name, resource_prefix, vpc) -> ec2.SecurityGroup:
        return ec2.SecurityGroup(
            self,
            f'{name}SG{envname}',
            security_group_name=f'{resource_prefix}-{envname}-{name}-sg',
            vpc=vpc,
            allow_all_outbound=False,
            disable_inline_rules=True,
        )

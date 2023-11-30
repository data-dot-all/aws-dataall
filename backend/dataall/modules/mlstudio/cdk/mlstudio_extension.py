""""
Extends an environment stack for SageMaker Studio Domain
"""
import logging

from aws_cdk import (
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_kms as kms,
    aws_logs as logs,
    aws_sagemaker as sagemaker,
    aws_ssm as ssm,
    RemovalPolicy,
)
from botocore.exceptions import ClientError
from dataall.modules.mlstudio.db.mlstudio_repositories import SageMakerStudioRepository

from dataall.base.aws.parameter_store import ParameterStoreManager
from dataall.base.aws.sts import SessionHelper
from dataall.core.environment.cdk.environment_stack import EnvironmentSetup, EnvironmentStackExtension
from dataall.core.environment.services.environment_service import EnvironmentService
from dataall.modules.mlstudio.aws.ec2_client import EC2
from dataall.modules.mlstudio.aws.sagemaker_studio_client import get_sagemaker_studio_domain

logger = logging.getLogger(__name__)


class SageMakerDomainExtension(EnvironmentStackExtension):

    @staticmethod
    def extent(setup: EnvironmentSetup):
        _environment = setup.environment()
        with setup.get_engine().scoped_session() as session:
            enabled = EnvironmentService.get_boolean_env_param(session, _environment, "mlStudiosEnabled")
            domain = SageMakerStudioRepository.get_sagemaker_studio_domain_by_env_uri(session, _environment.environmentUri)
            if not enabled or not domain:
                return

        sagemaker_principals = [setup.default_role] + setup.group_roles
        logger.info(f'Creating SageMaker base resources for sagemaker_principals = {sagemaker_principals}..')

        existing_vpc_id = None
        existing_subnet_ids = None
        if setup.payload:
            existing_vpc_id = setup.payload.get('mlstudio_vpc_id', None)
            existing_subnet_ids = setup.payload.get('mlstudio_subnet_ids', [])
            logger.info(f'VPC ID = {existing_vpc_id}')
            logger.info(f'Subnet IDs = {existing_subnet_ids}')

        if existing_vpc_id and existing_subnet_ids:
            logger.info(f'Using VPC {existing_vpc_id} and subnets {existing_subnet_ids} for SageMaker Studio domain')
            vpc = ec2.Vpc.from_lookup(setup, 'VPCStudio', vpc_id=existing_vpc_id)
            subnet_ids = existing_subnet_ids
            security_groups = []
        else:
            cdk_look_up_role_arn = SessionHelper.get_cdk_look_up_role_arn(
                accountid=_environment.AwsAccountId, region=_environment.region
            )
            existing_default_vpc = EC2.check_default_vpc_exists(
                AwsAccountId=_environment.AwsAccountId, region=_environment.region, role=cdk_look_up_role_arn
            )
            if existing_default_vpc:
                logger.info("Using default VPC for Sagemaker Studio domain")
                # Use default VPC - initial configuration (to be migrated)
                vpc = ec2.Vpc.from_lookup(setup, 'VPCStudio', is_default=True)
                subnet_ids = [private_subnet.subnet_id for private_subnet in vpc.private_subnets]
                subnet_ids += [public_subnet.subnet_id for public_subnet in vpc.public_subnets]
                subnet_ids += [isolated_subnet.subnet_id for isolated_subnet in vpc.isolated_subnets]
                security_groups = []
            else:
                logger.info("Default VPC not found, Exception. Creating a VPC for SageMaker resources...")
                # Create VPC with 3 Public Subnets and 3 Private subnets wit NAT Gateways
                log_group = logs.LogGroup(
                    setup,
                    f'SageMakerStudio{_environment.name}',
                    log_group_name=f'/{_environment.resourcePrefix}/{_environment.name}/vpc/sagemakerstudio',
                    retention=logs.RetentionDays.ONE_MONTH,
                    removal_policy=RemovalPolicy.DESTROY,
                )
                vpc_flow_role = iam.Role(
                    setup, 'FlowLog',
                    assumed_by=iam.ServicePrincipal('vpc-flow-logs.amazonaws.com')
                )
                vpc = ec2.Vpc(
                    setup,
                    "SageMakerVPC",
                    max_azs=3,
                    cidr="10.10.0.0/16",
                    subnet_configuration=[
                        ec2.SubnetConfiguration(
                            subnet_type=ec2.SubnetType.PUBLIC,
                            name="Public",
                            cidr_mask=24
                        ),
                        ec2.SubnetConfiguration(
                            subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT,
                            name="Private",
                            cidr_mask=24
                        ),
                    ],
                    enable_dns_hostnames=True,
                    enable_dns_support=True,
                )
                ec2.FlowLog(
                    setup, "StudioVPCFlowLog",
                    resource_type=ec2.FlowLogResourceType.from_vpc(vpc),
                    destination=ec2.FlowLogDestination.to_cloud_watch_logs(log_group, vpc_flow_role)
                )
                # setup security group to be used for sagemaker studio domain
                sagemaker_sg = ec2.SecurityGroup(
                    setup,
                    "SecurityGroup",
                    vpc=vpc,
                    description="Security Group for SageMaker Studio",
                )

                sagemaker_sg.add_ingress_rule(sagemaker_sg, ec2.Port.all_traffic())
                security_groups = [sagemaker_sg.security_group_id]
                subnet_ids = [private_subnet.subnet_id for private_subnet in vpc.private_subnets]

        vpc_id = vpc.vpc_id

        sagemaker_domain_role = iam.Role(
            setup,
            'RoleForSagemakerStudioUsers',
            assumed_by=iam.ServicePrincipal('sagemaker.amazonaws.com'),
            role_name='RoleSagemakerStudioUsers',
            managed_policies=[
                iam.ManagedPolicy.from_managed_policy_arn(
                    setup,
                    id='SagemakerFullAccess',
                    managed_policy_arn='arn:aws:iam::aws:policy/AmazonSageMakerFullAccess',
                ),
                iam.ManagedPolicy.from_managed_policy_arn(
                    setup, id='S3FullAccess', managed_policy_arn='arn:aws:iam::aws:policy/AmazonS3FullAccess'
                ),
            ],
        )

        sagemaker_domain_key = kms.Key(
            setup,
            'SagemakerDomainKmsKey',
            alias='SagemakerStudioDomain',
            enable_key_rotation=True,
            admins=[
                iam.ArnPrincipal(_environment.CDKRoleArn)
            ],
            policy=iam.PolicyDocument(
                assign_sids=True,
                statements=[
                    iam.PolicyStatement(
                        actions=[
                            "kms:Encrypt",
                            "kms:Decrypt",
                            "kms:ReEncrypt*",
                            "kms:GenerateDataKey*",
                            "kms:CreateGrant"
                        ],
                        effect=iam.Effect.ALLOW,
                        principals=[
                            sagemaker_domain_role,
                            iam.ArnPrincipal(_environment.CDKRoleArn)
                        ] + sagemaker_principals,
                        resources=["*"],
                        conditions={
                            "StringEquals": {
                                "kms:ViaService": [
                                    f"sagemaker.{_environment.region}.amazonaws.com",
                                    f"elasticfilesystem.{_environment.region}.amazonaws.com",
                                    f"ec2.{_environment.region}.amazonaws.com",
                                    f"s3.{_environment.region}.amazonaws.com"
                                ]
                            }
                        }
                    ),
                    iam.PolicyStatement(
                        actions=[
                            "kms:DescribeKey",
                            "kms:List*",
                            "kms:GetKeyPolicy",
                        ],
                        effect=iam.Effect.ALLOW,
                        principals=[
                            sagemaker_domain_role,
                        ] + sagemaker_principals,
                        resources=["*"],
                    )
                ],
            ),
        )

        sagemaker_domain = sagemaker.CfnDomain(
            setup,
            'SagemakerStudioDomain',
            domain_name=f'SagemakerStudioDomain-{_environment.region}-{_environment.AwsAccountId}',
            auth_mode='IAM',
            default_user_settings=sagemaker.CfnDomain.UserSettingsProperty(
                execution_role=sagemaker_domain_role.role_arn,
                security_groups=security_groups,
                sharing_settings=sagemaker.CfnDomain.SharingSettingsProperty(
                    notebook_output_option='Allowed',
                    s3_kms_key_id=sagemaker_domain_key.key_id,
                    s3_output_path=f's3://sagemaker-{_environment.region}-{_environment.AwsAccountId}',
                ),
            ),
            vpc_id=vpc_id,
            subnet_ids=subnet_ids,
            app_network_access_type='VpcOnly',
            kms_key_id=sagemaker_domain_key.key_id,
        )

        ssm.StringParameter(
            setup,
            'SagemakerStudioDomainId',
            string_value=sagemaker_domain.attr_domain_id,
            parameter_name=f'/{_environment.resourcePrefix}/{_environment.environmentUri}/sagemaker/sagemakerstudio/domain_id',
        )
        return sagemaker_domain

    @staticmethod
    def check_existing_sagemaker_studio_domain(environment):
        logger.info('Check if there is an existing sagemaker studio domain in the account')
        try:
            logger.info('check sagemaker studio domain created as part of data.all environment stack.')
            cdk_look_up_role_arn = SessionHelper.get_cdk_look_up_role_arn(
                accountid=environment.AwsAccountId, region=environment.region
            )
            dataall_created_domain = ParameterStoreManager.client(
                AwsAccountId=environment.AwsAccountId, region=environment.region, role=cdk_look_up_role_arn
            ).get_parameter(Name=f'/{environment.resourcePrefix}/{environment.environmentUri}/sagemaker/sagemakerstudio/domain_id')
            return False
        except ClientError as e:
            logger.info(f'check sagemaker studio domain created outside of data.all. Parameter data.all not found: {e}')
            existing_domain = get_sagemaker_studio_domain(
                AwsAccountId=environment.AwsAccountId, region=environment.region, role=cdk_look_up_role_arn
            )
            return existing_domain.get('DomainId', False)

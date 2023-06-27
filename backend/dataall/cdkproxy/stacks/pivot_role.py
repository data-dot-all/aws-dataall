from constructs import Construct
from aws_cdk import Duration, aws_iam as iam, NestedStack


class PivotRole(NestedStack):
    def __init__(self, scope: Construct, construct_id: str, config, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # Create Pivot IAM Role
        self.pivot_role = self.create_pivot_role(
            name=config['roleName'],
            principal_id=config['accountId'],
            external_id=config['externalId'],
            env_resource_prefix=config['resourcePrefix'],
        )
        # Data.All IAM Lake Formation service role creation
        self.lf_service_role = iam.CfnServiceLinkedRole(
            self, 'LakeFormationSLR', aws_service_name='lakeformation.amazonaws.com'
        )

    def create_pivot_role(self, name: str, principal_id: str, external_id: str, env_resource_prefix: str) -> iam.Role:
        """
        Creates an IAM Role that will enable data.all to interact with this Data Account

        :param str name: Role name
        :param str principal_id: AWS Account ID of central data.all
        :param str external_id: External ID provided by data.all
        :param str env_resource_prefix: Environment Resource Prefix provided by data.all
        :returns: Created IAM Role
        :rtype: iam.Role
        """

        role = iam.Role(
            self,
            'DataAllPivotRole-cdk',
            role_name=name,
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal('lakeformation.amazonaws.com'),
                iam.ServicePrincipal('glue.amazonaws.com'),
                iam.ServicePrincipal('lambda.amazonaws.com'),
            ),
            path='/',
            max_session_duration=Duration.hours(12),
            managed_policies=[
                self._create_dataall_policy0(env_resource_prefix),
                self._create_dataall_policy1(env_resource_prefix),
                self._create_dataall_policy2(env_resource_prefix),
                self._create_dataall_policy3(env_resource_prefix, name),
            ],
        )

        role.assume_role_policy.add_statements(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                principals=[iam.AccountPrincipal(account_id=principal_id)],
                actions=['sts:AssumeRole'],
                conditions={
                    'StringEquals': {'sts:ExternalId': external_id},
                    'StringLike': {"aws:PrincipalArn": [
                        f"arn:aws:iam::{principal_id}:role/*graphql-role",
                        f"arn:aws:iam::{principal_id}:role/*awsworker-role",
                        f"arn:aws:iam::{principal_id}:role/*ecs-tasks-role"
                    ]}
                },
            )
        )

        return role

    def _create_dataall_policy0(self, env_resource_prefix: str) -> iam.ManagedPolicy:
        """
        Creates the first managed IAM Policy required for the Pivot Role used by data.all

        :param str env_resource_prefix: Environment Resource Prefix provided by data.all
        :returns: Created IAM Policy
        :rtype: iam.ManagedPolicy
        """
        return iam.ManagedPolicy(
            self,
            'PivotRolePolicy0',
            managed_policy_name=f'{env_resource_prefix}-pivotrole-cdk-policy-0',
            statements=[
                # Read Buckets
                iam.PolicyStatement(
                    sid='ReadBuckets',
                    effect=iam.Effect.ALLOW,
                    actions=[
                        's3:ListAllMyBuckets',
                        's3:GetBucketLocation',
                        's3:PutBucketTagging'
                    ],
                    resources=['*'],
                ),
                # S3 Managed Buckets
                iam.PolicyStatement(
                    sid='ManagedBuckets',
                    effect=iam.Effect.ALLOW,
                    actions=[
                        's3:List*',
                        's3:Delete*',
                        's3:Get*',
                        's3:Put*'
                    ],
                    resources=[f'arn:aws:s3:::{env_resource_prefix}*'],
                ),
                # S3 Imported Buckets - restrict resources via bucket policies
                iam.PolicyStatement(
                    sid='ImportedBuckets',
                    effect=iam.Effect.ALLOW,
                    actions=[
                        's3:List*',
                        's3:GetBucket*',
                        's3:GetLifecycleConfiguration',
                        's3:GetObject',
                        's3:PutBucketPolicy',
                        's3:PutBucketTagging',
                        's3:PutObject',
                        's3:PutObjectAcl',
                        's3:PutBucketOwnershipControls',
                    ],
                    resources=['arn:aws:s3:::*'],
                ),
                # KMS - needed for imported buckets
                iam.PolicyStatement(
                    sid='KMS',
                    effect=iam.Effect.ALLOW,
                    actions=[
                        'kms:Decrypt',
                        'kms:Encrypt',
                        'kms:GenerateDataKey*',
                        'kms:PutKeyPolicy',
                        'kms:ReEncrypt*',
                        'kms:TagResource',
                        'kms:UntagResource',
                    ],
                    resources=['*'],
                ),
                iam.PolicyStatement(
                    sid='KMSList',
                    effect=iam.Effect.ALLOW,
                    actions=[
                        'kms:List*',
                        'kms:DescribeKey',
                    ],
                    resources=['*'],
                ),
                # Athena - needed for Worksheets feature
                iam.PolicyStatement(
                    sid='AthenaWorkgroups',
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "athena:GetQueryExecution",
                        "athena:GetQueryResults",
                        "athena:GetWorkGroup",
                        "athena:StartQueryExecution"
                    ],
                    resources=[f'arn:aws:athena:*:{self.account}:workgroup/{env_resource_prefix}*'],
                ),
                # S3 Access points - needed for access points sharing
                iam.PolicyStatement(
                    sid='ManagedAccessPoints',
                    effect=iam.Effect.ALLOW,
                    actions=[
                        's3:GetAccessPoint',
                        's3:GetAccessPointPolicy',
                        's3:ListAccessPoints',
                        's3:CreateAccessPoint',
                        's3:DeleteAccessPoint',
                        's3:GetAccessPointPolicyStatus',
                        's3:DeleteAccessPointPolicy',
                        's3:PutAccessPointPolicy',
                    ],
                    resources=[f'arn:aws:s3:*:{self.account}:accesspoint/*'],
                ),
                # Glue - needed to handle databases and tables
                iam.PolicyStatement(
                    sid='GlueCatalog',
                    effect=iam.Effect.ALLOW,
                    actions=[
                        'glue:BatchCreatePartition',
                        'glue:BatchDeletePartition',
                        'glue:BatchDeleteTable',
                        'glue:CreateDatabase',
                        'glue:CreatePartition',
                        'glue:CreateTable',
                        'glue:DeleteDatabase',
                        'glue:DeletePartition',
                        'glue:DeleteTable',
                        'glue:BatchGet*',
                        'glue:Get*',
                        'glue:List*',
                        'glue:SearchTables',
                        'glue:UpdateDatabase',
                        'glue:UpdatePartition',
                        'glue:UpdateTable',
                        'glue:TagResource',
                    ],
                    resources=['*'],
                ),
                # Glue ETL - needed to start crawler and profiling jobs
                iam.PolicyStatement(
                    sid='GlueETL',
                    effect=iam.Effect.ALLOW,
                    actions=[
                        'glue:StartCrawler',
                        'glue:StartJobRun',
                        'glue:StartTrigger',
                        'glue:UpdateTrigger',
                        'glue:UpdateJob',
                        'glue:UpdateCrawler',
                    ],
                    resources=[
                        f'arn:aws:glue:*:{self.account}:crawler/{env_resource_prefix}*',
                        f'arn:aws:glue:*:{self.account}:job/{env_resource_prefix}*',
                        f'arn:aws:glue:*:{self.account}:trigger/{env_resource_prefix}*',
                    ],
                ),
                # SNS - For subscriptions
                iam.PolicyStatement(
                    sid='SNSPublish',
                    effect=iam.Effect.ALLOW,
                    actions=[
                        'sns:Publish',
                        'sns:SetTopicAttributes',
                        'sns:GetTopicAttributes',
                        'sns:DeleteTopic',
                        'sns:Subscribe',
                        'sns:TagResource',
                        'sns:UntagResource',
                        'sns:CreateTopic',
                    ],
                    resources=[f'arn:aws:sns:*:{self.account}:{env_resource_prefix}*'],
                ),
                iam.PolicyStatement(
                    sid='SNSList', effect=iam.Effect.ALLOW, actions=['sns:ListTopics'], resources=['*']
                ),
                # SQS - support SQS queues
                iam.PolicyStatement(
                    sid='SQSList', effect=iam.Effect.ALLOW, actions=['sqs:ListQueues'], resources=['*']
                ),
                iam.PolicyStatement(
                    sid='SQS',
                    effect=iam.Effect.ALLOW,
                    actions=[
                        'sqs:ReceiveMessage',
                        'sqs:SendMessage'
                    ],
                    resources=[f'arn:aws:sqs:*:{self.account}:{env_resource_prefix}*'],
                ),
                # AWS Logging Buckets
                iam.PolicyStatement(
                    sid='AWSLoggingBuckets',
                    effect=iam.Effect.ALLOW,
                    actions=[
                        's3:PutBucketAcl',
                        's3:PutBucketNotification'
                    ],
                    resources=[f'arn:aws:s3:::{env_resource_prefix}-logging-*'],
                ),
                # CloudWatch Metrics
                iam.PolicyStatement(
                    sid='CWMetrics',
                    effect=iam.Effect.ALLOW,
                    actions=[
                        'cloudwatch:PutMetricData',
                        'cloudwatch:GetMetricData',
                        'cloudwatch:GetMetricStatistics'
                    ],
                    resources=['*'],
                ),
                # Logs
                iam.PolicyStatement(
                    sid='Logs',
                    effect=iam.Effect.ALLOW,
                    actions=[
                        'logs:CreateLogGroup',
                        'logs:CreateLogStream',
                    ],
                    resources=[
                        f'arn:aws:logs:*:{self.account}:log-group:/aws/lambda/*',
                        f'arn:aws:logs:*:{self.account}:log-group:/{env_resource_prefix}*',
                    ],
                ),
                # Logging
                iam.PolicyStatement(
                    sid='Logging', effect=iam.Effect.ALLOW, actions=['logs:PutLogEvents'], resources=['*']
                ),
            ],
        )

    def _create_dataall_policy1(self, env_resource_prefix: str) -> iam.ManagedPolicy:
        """
        Creates the second managed IAM Policy required for the Pivot Role used by data.all

        :param str env_resource_prefix: Environment Resource Prefix provided by data.all
        :returns: Created IAM Policy
        :rtype: iam.ManagedPolicy
        """
        return iam.ManagedPolicy(
            self,
            'PivotRolePolicy1',
            managed_policy_name=f'{env_resource_prefix}-pivotrole-cdk-policy-1',
            statements=[
                # EC2 describe needed for SageMaker
                iam.PolicyStatement(
                    sid='EC2SG',
                    effect=iam.Effect.ALLOW,
                    actions=[
                        'ec2:DescribeSubnets',
                        'ec2:DescribeSecurityGroups',
                        'ec2:DescribeVpcs',
                        'ec2:DescribeInstances',
                        'ec2:DescribeNetworkInterfaces',
                    ],
                    resources=['*'],
                ),
                # SageMaker
                iam.PolicyStatement(
                    sid='SageMakerNotebookActions',
                    effect=iam.Effect.ALLOW,
                    actions=[
                        'sagemaker:ListTags',
                        'sagemaker:DescribeUserProfile',
                        'sagemaker:StopNotebookInstance',
                        'sagemaker:CreatePresignedNotebookInstanceUrl',
                        'sagemaker:DescribeNotebookInstance',
                        'sagemaker:StartNotebookInstance',
                        'sagemaker:AddTags',
                        'sagemaker:DescribeDomain',
                        'sagemaker:CreatePresignedDomainUrl',
                    ],
                    resources=[
                        f'arn:aws:sagemaker:*:{self.account}:notebook-instance/{env_resource_prefix}*',
                        f'arn:aws:sagemaker:*:{self.account}:domain/*',
                        f'arn:aws:sagemaker:*:{self.account}:user-profile/*/*',
                    ],
                ),
                iam.PolicyStatement(
                    sid='SageMakerNotebookInstances',
                    effect=iam.Effect.ALLOW,
                    actions=[
                        'sagemaker:ListNotebookInstances',
                        'sagemaker:ListDomains',
                        'sagemaker:ListApps',
                        'sagemaker:DeleteApp',
                    ],
                    resources=['*'],
                ),
                # RAM
                iam.PolicyStatement(
                    sid='RamTag',
                    effect=iam.Effect.ALLOW,
                    actions=['ram:TagResource'],
                    resources=['*'],
                    conditions={'ForAllValues:StringLike': {'ram:ResourceShareName': ['LakeFormation*']}},
                ),
                iam.PolicyStatement(
                    sid='RamCreateResource',
                    effect=iam.Effect.ALLOW,
                    actions=['ram:CreateResourceShare'],
                    resources=['*'],
                    conditions={
                        'ForAllValues:StringEquals': {
                            'ram:RequestedResourceType': ['glue:Table', 'glue:Database', 'glue:Catalog']
                        }
                    },
                ),
                iam.PolicyStatement(
                    sid='RamUpdateResource',
                    effect=iam.Effect.ALLOW,
                    actions=['ram:UpdateResourceShare'],
                    resources=[f'arn:aws:ram:*:{self.account}:resource-share/*'],
                    conditions={
                        'StringEquals': {'aws:ResourceTag/dataall': 'true'},
                        'ForAllValues:StringLike': {'ram:ResourceShareName': ['LakeFormation*']},
                    },
                ),
                iam.PolicyStatement(
                    sid='RamAssociateResource',
                    effect=iam.Effect.ALLOW,
                    actions=[
                        'ram:AssociateResourceShare',
                        'ram:DisassociateResourceShare'
                    ],
                    resources=[f'arn:aws:ram:*:{self.account}:resource-share/*'],
                    conditions={'ForAllValues:StringLike': {'ram:ResourceShareName': ['LakeFormation*']}},
                ),
                iam.PolicyStatement(
                    sid='RamDeleteResource',
                    effect=iam.Effect.ALLOW,
                    actions=['ram:DeleteResourceShare'],
                    resources=[f'arn:aws:ram:*:{self.account}:resource-share/*'],
                ),
                iam.PolicyStatement(
                    sid='RamInvitations',
                    effect=iam.Effect.ALLOW,
                    actions=[
                        'ram:AcceptResourceShareInvitation',
                        'ram:RejectResourceShareInvitation',
                        'ram:EnableSharingWithAwsOrganization',
                    ],
                    resources=['*'],
                ),
                iam.PolicyStatement(
                    sid='RamRead',
                    effect=iam.Effect.ALLOW,
                    actions=[
                        'ram:Get*',
                        'ram:List*'
                    ],
                    resources=['*'],
                ),
                # CloudFormation
                iam.PolicyStatement(
                    sid='CloudFormation',
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "cloudformation:DeleteStack",
                        "cloudformation:DescribeStacks",
                        "cloudformation:DescribeStackEvents",
                        "cloudformation:DescribeStackResources"
                    ],
                    resources=[
                        f'arn:aws:cloudformation:*:{self.account}:stack/{env_resource_prefix}*/*',
                        f'arn:aws:cloudformation:*:{self.account}:stack/*/*',
                    ],
                ),
            ],
        )

    def _create_dataall_policy2(self, env_resource_prefix: str) -> iam.ManagedPolicy:
        """
        Creates the third managed IAM Policy required for the Pivot Role used by data.all

        :param str env_resource_prefix: Environment Resource Prefix provided by data.all
        :returns: Created IAM Policy
        :rtype: iam.ManagedPolicy
        """
        return iam.ManagedPolicy(
            self,
            'PivotRolePolicy2',
            managed_policy_name=f'{env_resource_prefix}-pivotrole-cdk-policy-2',
            statements=[
                # LakeFormation
                iam.PolicyStatement(
                    sid='LakeFormation',
                    effect=iam.Effect.ALLOW,
                    actions=[
                        'lakeformation:UpdateResource',
                        'lakeformation:DescribeResource',
                        'lakeformation:AddLFTagsToResource',
                        'lakeformation:RemoveLFTagsFromResource',
                        'lakeformation:GetResourceLFTags',
                        'lakeformation:ListLFTags',
                        'lakeformation:CreateLFTag',
                        'lakeformation:GetLFTag',
                        'lakeformation:UpdateLFTag',
                        'lakeformation:DeleteLFTag',
                        'lakeformation:SearchTablesByLFTags',
                        'lakeformation:SearchDatabasesByLFTags',
                        'lakeformation:ListResources',
                        'lakeformation:ListPermissions',
                        'lakeformation:GrantPermissions',
                        'lakeformation:BatchGrantPermissions',
                        'lakeformation:RevokePermissions',
                        'lakeformation:BatchRevokePermissions',
                        'lakeformation:PutDataLakeSettings',
                        'lakeformation:GetDataLakeSettings',
                        'lakeformation:GetDataAccess',
                        'lakeformation:GetWorkUnits',
                        'lakeformation:StartQueryPlanning',
                        'lakeformation:GetWorkUnitResults',
                        'lakeformation:GetQueryState',
                        'lakeformation:GetQueryStatistics',
                        'lakeformation:GetTableObjects',
                        'lakeformation:UpdateTableObjects',
                        'lakeformation:DeleteObjectsOnCancel',
                    ],
                    resources=['*'],
                ),
                # QuickSight
                iam.PolicyStatement(
                    sid='QuickSight',
                    effect=iam.Effect.ALLOW,
                    actions=[
                        'quicksight:CreateGroup',
                        'quicksight:DescribeGroup',
                        'quicksight:ListDashboards',
                        'quicksight:DescribeDataSource',
                        'quicksight:DescribeDashboard',
                        'quicksight:DescribeUser',
                        'quicksight:SearchDashboards',
                        'quicksight:GetDashboardEmbedUrl',
                        'quicksight:GenerateEmbedUrlForAnonymousUser',
                        'quicksight:UpdateUser',
                        'quicksight:ListUserGroups',
                        'quicksight:RegisterUser',
                        'quicksight:DescribeDashboardPermissions',
                        'quicksight:UpdateDashboardPermissions',
                        'quicksight:GetAuthCode',
                        'quicksight:CreateGroupMembership',
                        'quicksight:DescribeAccountSubscription',
                    ],
                    resources=[
                        f'arn:aws:quicksight:*:{self.account}:group/default/*',
                        f'arn:aws:quicksight:*:{self.account}:user/default/*',
                        f'arn:aws:quicksight:*:{self.account}:datasource/*',
                        f'arn:aws:quicksight:*:{self.account}:user/*',
                        f'arn:aws:quicksight:*:{self.account}:dashboard/*',
                        f'arn:aws:quicksight:*:{self.account}:namespace/default',
                        f'arn:aws:quicksight:*:{self.account}:account/*',
                        f'arn:aws:quicksight:*:{self.account}:*',
                    ],
                ),
                iam.PolicyStatement(
                    sid='QuickSightSession',
                    effect=iam.Effect.ALLOW,
                    actions=['quicksight:GetSessionEmbedUrl'],
                    resources=['*'],
                ),
            ],
        )

    def _create_dataall_policy3(self, env_resource_prefix: str, role_name: str) -> iam.ManagedPolicy:
        """
        Creates the fourth managed IAM Policy required for the Pivot Role used by data.all

        :param str env_resource_prefix: Environment Resource Prefix provided by data.all
        :param str role_name: IAM Role name
        :returns: Created IAM Policy
        :rtype: iam.ManagedPolicy
        """
        return iam.ManagedPolicy(
            self,
            'PivotRolePolicy3',
            managed_policy_name=f'{env_resource_prefix}-pivotrole-cdk-policy-3',
            statements=[
                # SSM Parameter Store
                iam.PolicyStatement(
                    sid='ParameterStore',
                    effect=iam.Effect.ALLOW,
                    actions=['ssm:GetParameter'],
                    resources=[
                        f'arn:aws:ssm:*:{self.account}:parameter/{env_resource_prefix}/*',
                        f'arn:aws:ssm:*:{self.account}:parameter/dataall/*',
                        f'arn:aws:ssm:*:{self.account}:parameter/ddk/*',
                    ],
                ),
                # IAM - needed for consumption roles and for S3 sharing
                iam.PolicyStatement(
                    sid='IAMListGet',
                    effect=iam.Effect.ALLOW,
                    actions=[
                        'iam:ListRoles',
                        'iam:Get*'
                    ], resources=['*']
                ),
                iam.PolicyStatement(
                    sid='IAMRolePolicy',
                    effect=iam.Effect.ALLOW,
                    actions=[
                        'iam:PutRolePolicy',
                        'iam:DeleteRolePolicy'
                    ],
                    resources=['*'],
                ),
                iam.PolicyStatement(
                    sid="PassRole",
                    actions=[
                        'iam:PassRole',
                    ],
                    resources=[
                        f'arn:aws:iam::{self.account}:role/{role_name}',
                    ],
                ),
                iam.PolicyStatement(
                    sid="PassRoleGlue",
                    actions=[
                        'iam:PassRole',
                    ],
                    resources=[
                        f'arn:aws:iam::{self.account}:role/{env_resource_prefix}*',
                    ],
                    conditions={
                        "StringEquals": {
                            "iam:PassedToService": [
                                "glue.amazonaws.com",
                            ]
                        }
                    }
                ),
                # STS
                iam.PolicyStatement(
                    sid='STS',
                    effect=iam.Effect.ALLOW,
                    actions=['sts:AssumeRole'],
                    resources=[
                        f'arn:aws:iam::{self.account}:role/{env_resource_prefix}*',
                        f'arn:aws:iam::{self.account}:role/ddk-*',
                    ],
                ),
                # CodeCommit - used in Pipelines
                iam.PolicyStatement(
                    sid='CodeCommit',
                    effect=iam.Effect.ALLOW,
                    actions=[
                        'codecommit:GetFile',
                        'codecommit:ListBranches',
                        'codecommit:GetFolder',
                        'codecommit:GetCommit',
                        'codecommit:GitPull',
                        'codecommit:GetRepository',
                        'codecommit:TagResource',
                        'codecommit:UntagResource',
                        'codecommit:CreateBranch',
                        'codecommit:CreateCommit',
                        'codecommit:CreateRepository',
                        'codecommit:DeleteRepository',
                        'codecommit:GitPush',
                        'codecommit:PutFile',
                        'codecommit:GetBranch',
                    ],
                    resources=[f'arn:aws:codecommit:*:{self.account}:{env_resource_prefix}*'],
                ),
            ],
        )

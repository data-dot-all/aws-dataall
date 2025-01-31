import os
from aws_cdk import aws_iam as iam

from dataall.base import db
from dataall.base.aws.sts import SessionHelper
from dataall.base.utils.iam_cdk_utils import process_and_split_policy_with_resources_in_statements
from dataall.core.environment.cdk.pivot_role_stack import PivotRoleStatementSet
from dataall.modules.redshift_datasets.db.redshift_connection_repositories import RedshiftConnectionRepository
from dataall.modules.redshift_datasets.aws.redshift_serverless import redshift_serverless_client


class RedshiftDatasetsPivotRole(PivotRoleStatementSet):
    """
    Class including all permissions needed  by the pivot role to work with Amazon Redshift.
    """

    def get_statements(self):
        base_statements = [
            iam.PolicyStatement(
                sid='RedshiftSecretsManager',
                effect=iam.Effect.ALLOW,
                actions=[
                    'secretsmanager:GetSecretValue',
                ],
                resources=[
                    f'arn:aws:secretsmanager:{self.region}:{self.account}:secret:*',
                ],
                conditions={
                    'StringEquals': {
                        'aws:ResourceTag/dataall': 'True',
                    },
                },
            ),
            iam.PolicyStatement(
                sid='RedshiftReadAllResources',  # These permissions can only be applied to *
                effect=iam.Effect.ALLOW,
                actions=[
                    'redshift-data:DescribeStatement',
                    'redshift:DescribeClusters',
                    'redshift-serverless:ListNamespaces',
                    'redshift-serverless:ListWorkgroups',
                ],
                resources=[
                    '*',
                ],
            ),
            iam.PolicyStatement(
                sid='RedshiftRead',
                effect=iam.Effect.ALLOW,
                actions=[
                    'redshift-data:ListDatabases',
                    'redshift-serverless:GetWorkgroup',
                    'redshift:GetClusterCredentials',
                ],
                resources=[
                    f'arn:aws:redshift-serverless:{self.region}:{self.account}:workgroup/*',
                    f'arn:aws:redshift:{self.region}:{self.account}:cluster:*',
                    f'arn:aws:redshift:{self.region}:{self.account}:dbuser:*/*',
                    f'arn:aws:redshift:{self.region}:{self.account}:dbname:*/*',
                ],
            ),
        ]
        engine = db.get_engine(envname=os.environ.get('envname', 'local'))
        with engine.scoped_session() as session:
            connections = RedshiftConnectionRepository.list_environment_redshift_connections(
                session, environment_uri=self.environmentUri
            )
            additional_statements = []
            if connections:
                cdk_look_up_role_arn = SessionHelper.get_cdk_look_up_role_arn(
                    accountid=self.account, region=self.region
                )
                rs_client = redshift_serverless_client(
                    account_id=self.account, region=self.region, role=cdk_look_up_role_arn
                )
                cluster_arns = [
                    f'arn:aws:redshift:{self.region}:{self.account}:cluster:{conn.clusterId}'
                    for conn in connections
                    if conn.clusterId
                ]
                workgroup_arns = [
                    rs_client.get_workgroup_arn(workgroup_name=conn.workgroup) for conn in connections if conn.workgroup
                ]
                redshift_data_statements = process_and_split_policy_with_resources_in_statements(
                    base_sid='RedshiftData',
                    effect=iam.Effect.ALLOW.value,
                    actions=[
                        'redshift-data:ListSchemas',
                        'redshift-data:ListTables',
                        'redshift-data:ExecuteStatement',
                        'redshift-data:DescribeTable',
                    ],
                    resources=cluster_arns + workgroup_arns,
                )
                additional_statements.extend(redshift_data_statements)

            return base_statements + additional_statements

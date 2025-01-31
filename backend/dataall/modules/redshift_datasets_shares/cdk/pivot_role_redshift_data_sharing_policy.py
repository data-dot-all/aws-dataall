import os
from dataall.base import db
from dataall.base.utils.iam_cdk_utils import process_and_split_policy_with_resources_in_statements
from dataall.core.environment.cdk.pivot_role_stack import PivotRoleStatementSet
from dataall.modules.redshift_datasets.db.redshift_connection_repositories import RedshiftConnectionRepository

from aws_cdk import aws_iam as iam


class RedshiftDataSharingPivotRole(PivotRoleStatementSet):
    """
    Class including all permissions needed  by the pivot role to process Redshift data shares
    """

    def get_statements(self):
        statements = [
            iam.PolicyStatement(
                sid='RedshiftReadShareResources',
                effect=iam.Effect.ALLOW,
                actions=[
                    'redshift-data:GetStatementResult',  # It can only be applied to *
                    'redshift:AssociateDataShareConsumer',  # From consumer we can accept any share
                    'redshift:DescribeDataShares',  # Read
                ],
                resources=[
                    '*',
                ],
            ),
        ]
        additional_statements = []
        engine = db.get_engine(envname=os.environ.get('envname', 'local'))
        with engine.scoped_session() as session:
            connections = RedshiftConnectionRepository.list_environment_redshift_connections(
                session, environment_uri=self.environmentUri
            )
            if connections:
                source_datashare_arns = [
                    f'arn:aws:redshift:{self.region}:{self.account}:datashare:{conn.nameSpaceId}/*'
                    for conn in connections
                ]
                additional_statements.extend(
                    process_and_split_policy_with_resources_in_statements(
                        base_sid='RedshiftDataShare',
                        effect=iam.Effect.ALLOW.value,
                        actions=['redshift:AuthorizeDataShare'],
                        resources=source_datashare_arns,
                    )
                )
        return statements + additional_statements

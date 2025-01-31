from dataall.core.environment.cdk.pivot_role_stack import PivotRoleStatementSet
from aws_cdk import aws_iam as iam


class ServiceQuotaPivotRole(PivotRoleStatementSet):
    """
    Class including all permissions needed  by the pivot role to work with AWS Service Quota.
    It allows pivot role to:
    - List and Get Service Quota details
    """

    def get_statements(self):
        statements = [
            # Service Quota - Needed to determine the number of service quotas for managed policies which can be attached
            iam.PolicyStatement(
                sid='ServiceQuotaListGet',
                effect=iam.Effect.ALLOW,
                actions=['servicequotas:List*', 'servicequotas:Get*'],
                resources=['*'],
            )
        ]
        return statements

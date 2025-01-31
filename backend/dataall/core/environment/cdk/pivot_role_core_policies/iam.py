from dataall.core.environment.cdk.pivot_role_stack import PivotRoleStatementSet
from aws_cdk import aws_iam as iam


class IAMPivotRole(PivotRoleStatementSet):
    """
    Class including all permissions needed  by the pivot role to work with AWS IAM.
    It allows pivot role to:
    - ....
    """

    def get_statements(self):
        statements = [
            # IAM - needed for consumption roles and for S3 sharing
            iam.PolicyStatement(
                sid='IAMListGet', effect=iam.Effect.ALLOW, actions=['iam:List*', 'iam:Get*'], resources=['*']
            ),
            iam.PolicyStatement(
                sid='PassRole',
                actions=[
                    'iam:PassRole',
                ],
                resources=[
                    f'arn:aws:iam::{self.account}:role/{self.role_name}',
                ],
            ),
            # DENY to prevent pivot role to grant itself permissions
            iam.PolicyStatement(
                sid='IAMDenyForPivotRole',
                effect=iam.Effect.DENY,
                actions=['iam:Put*', 'iam:Delete*', 'iam:Update*', 'iam:AttachRolePolicy', 'iam:DetachRolePolicy'],
                resources=[f'arn:aws:iam::{self.account}:role/{self.role_name}'],
            ),
        ]
        return statements

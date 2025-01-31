import logging
import os
from typing import List
from constructs import Construct
from aws_cdk import Duration, aws_iam as iam, NestedStack

from dataall.base.utils.iam_cdk_utils import (
    process_and_split_statements_in_chunks,
)


logger = logging.getLogger(__name__)

ENVNAME = os.getenv('envname', 'local')


class PivotRoleStatementSet(object):
    def __init__(self, stack, env_resource_prefix, role_name, account, region, environmentUri):
        self.stack = stack
        self.env_resource_prefix = env_resource_prefix
        self.role_name = role_name
        self.account = account
        self.region = region
        self.environmentUri = environmentUri

    def generate_policies(self) -> List[iam.ManagedPolicy]:
        """
        Creates a list of aws_iam.Policy based on declared subclasses of Policy object
        """
        policies = []
        statements = []
        services = PivotRoleStatementSet.__subclasses__()
        logger.info(f'Found {len(services)} subclasses of PivotRoleStatementSet')
        logger.info(
            f'PivotroleStatement variables: {self.env_resource_prefix}, {self.role_name}, {self.account}, {self.region}'
        )

        for service in services:
            logger.info(f'Adding {service.__name__} statements to policy')
            statements.extend(service.get_statements(self))
            logger.info(f'statements: {str(service.get_statements(self))}')

        statements_json = [statement.to_json() for statement in statements]
        statements_chunks: List[List[iam.PolicyStatement]] = process_and_split_statements_in_chunks(statements_json)

        for index, chunk in enumerate(statements_chunks):
            policies.append(
                iam.ManagedPolicy(
                    self.stack,
                    f'PivotRolePolicy-{index + 1}',
                    managed_policy_name=f'{self.env_resource_prefix}-pivot-role-cdk-policy-{self.region}-{index + 1}',
                    statements=chunk,
                )
            )
        return policies

    def get_statements(self) -> List[iam.PolicyStatement]:
        """
        This method returns the list of IAM policy statements needed to be added to the pivot role policies
        :return: list
        """
        raise NotImplementedError('PivotRoleStatementSet subclasses need to implement the get_statements class method')


# IT IS HERE TO AVOID CIRCULAR IMPORT
# disable ruff-format, because this unused imports are important
# pivot_role_core_policies is used to fill PivotRoleStatementSet subclasses (line 31)
# ruff: noqa: E402
from dataall.core.environment.cdk import pivot_role_core_policies


class PivotRole(NestedStack):
    def __init__(self, scope: Construct, construct_id: str, config, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.env_resource_prefix = config['resourcePrefix']
        self.role_name = config['roleName']
        self.environmentUri = config['environmentUri']

        # Create Pivot IAM Role
        self.pivot_role = self.create_pivot_role(
            principal_id=config['accountId'],
            external_id=config['externalId'],
        )

    def create_pivot_role(self, principal_id: str, external_id: str) -> iam.Role:
        """
        Creates an IAM Role that will enable data.all to interact with this Data Account

        :param str principal_id: AWS Account ID of central data.all
        :param str external_id: External ID provided by data.all
        :returns: Created IAM Role
        :rtype: iam.Role
        """
        managed_policies = PivotRoleStatementSet(
            stack=self,
            env_resource_prefix=self.env_resource_prefix,
            role_name=self.role_name,
            account=self.account,
            region=self.region,
            environmentUri=self.environmentUri,
        ).generate_policies()

        logger.info(f'Managed Policies: {managed_policies}')
        role = iam.Role(
            self,
            'DataAllPivotRole-cdk',
            role_name=self.role_name,
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal('lakeformation.amazonaws.com'),
                iam.ServicePrincipal('glue.amazonaws.com'),
                iam.ServicePrincipal('lambda.amazonaws.com'),
            ),
            path='/',
            max_session_duration=Duration.hours(12),
            managed_policies=managed_policies,
        )

        if ENVNAME in ['local', 'dkrcompose']:
            # Less restrictive trust policy for local development
            role.assume_role_policy.add_statements(
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    principals=[iam.AccountPrincipal(account_id=principal_id)],
                    actions=['sts:AssumeRole'],
                )
            )
        else:
            role.assume_role_policy.add_statements(
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    principals=[iam.AccountPrincipal(account_id=principal_id)],
                    actions=['sts:AssumeRole'],
                    conditions={
                        'StringEquals': {'sts:ExternalId': external_id},
                        'StringLike': {
                            'aws:PrincipalArn': [
                                f'arn:aws:iam::{principal_id}:role/*graphql-role',
                                f'arn:aws:iam::{principal_id}:role/*awsworker-role',
                                f'arn:aws:iam::{principal_id}:role/*ecs-tasks-role',
                            ]
                        },
                    },
                )
            )

        return role

import logging
from botocore.exceptions import ClientError
import re

from .sts import SessionHelper

log = logging.getLogger(__name__)


class IAM:
    @staticmethod
    def client(account_id: str, region: str, role=None):
        session = SessionHelper.remote_session(accountid=account_id, region=region, role=role)
        return session.client('iam')

    @staticmethod
    def get_role(account_id: str, region: str, role_arn: str, role=None):
        log.info(f'Getting IAM role = {role_arn}')
        try:
            client = IAM.client(account_id=account_id, region=region, role=role)
            response = client.get_role(RoleName=role_arn.split('/')[-1])
            assert response['Role']['Arn'] == role_arn, "Arn doesn't match the role name. Check Arn and try again."
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                raise Exception(
                    f'Data.all Environment Pivot Role does not have permissions to get role {role_arn}: {e}'
                )
            log.error(f'Failed to get role {role_arn} due to: {e}')
            return None
        else:
            return response['Role']

    @staticmethod
    def get_role_arn_by_name(account_id: str, region: str, role_name: str, role=None):
        log.info(f'Getting IAM role name= {role_name}')
        try:
            client = IAM.client(account_id=account_id, region=region, role=role)
            response = client.get_role(RoleName=role_name)
            return response['Role']['Arn']
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                raise Exception(
                    f'Data.all Environment Pivot Role does not have permissions to get role {role_name}: {e}'
                )
            log.error(f'Failed to get role {role_name} due to: {e}')
            return None

    @staticmethod
    def get_role_policy(
        account_id: str,
        region: str,
        role_name: str,
        policy_name: str,
    ):
        try:
            client = IAM.client(account_id, region)
            response = client.get_role_policy(
                RoleName=role_name,
                PolicyName=policy_name,
            )
            return response['PolicyDocument']
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                raise Exception(
                    f'Data.all Environment Pivot Role does not have permissions to get policy {policy_name} of role {role_name}: {e}'
                )
            log.error(f'Failed to get policy {policy_name} of role {role_name} : {e}')
            return None

    @staticmethod
    def list_policy_names_by_policy_pattern(account_id: str, region: str, policy_filter_pattern: str):
        try:
            client = IAM.client(account_id, region)
            # Setting Scope to 'Local' to fetch all the policies created in this account
            paginator = client.get_paginator('list_policies')
            policies = []
            for page in paginator.paginate(Scope='Local'):
                policies.extend(page['Policies'])
            policy_names = [policy.get('PolicyName') for policy in policies]
            return [policy_nm for policy_nm in policy_names if re.search(policy_filter_pattern, policy_nm)]
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                raise Exception(
                    f'Data.all Environment Pivot Role does not have permissions to get policies with pattern {policy_filter_pattern} due to: {e}'
                )
            log.error(f'Failed to get policies for policy pattern due to: {e}')
            return []

    @staticmethod
    def delete_role_policy(
        account_id: str,
        region: str,
        role_name: str,
        policy_name: str,
    ):
        try:
            client = IAM.client(account_id, region)
            client.delete_role_policy(
                RoleName=role_name,
                PolicyName=policy_name,
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                raise Exception(
                    f'Data.all Environment Pivot Role does not have permissions to delete policy {policy_name} of role {role_name}: {e}'
                )
            log.error(f'Failed to delete policy {policy_name} of role {role_name} : {e}')

    @staticmethod
    def get_managed_policy_by_name(account_id: str, region: str, policy_name: str):
        try:
            arn = f'arn:aws:iam::{account_id}:policy/{policy_name}'
            client = IAM.client(account_id, region)
            response = client.get_policy(PolicyArn=arn)
            return response['Policy']
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                raise Exception(
                    f'Data.all Environment Pivot Role does not have permissions to to get policy {policy_name}: {e}'
                )
            log.error(f'Failed to get policy {policy_name}: {e}')
            return None

    @staticmethod
    def get_managed_policy_document_by_name(account_id: str, region: str, policy_name: str):
        try:
            arn = f'arn:aws:iam::{account_id}:policy/{policy_name}'
            client = IAM.client(account_id, region)
            policy = IAM.get_managed_policy_by_name(account_id, region, policy_name)
            policyVersionId = policy['DefaultVersionId']
            response = client.get_policy_version(PolicyArn=arn, VersionId=policyVersionId)
            return response['PolicyVersion']['Document']
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                raise Exception(
                    f'Data.all Environment Pivot Role does not have permissions to to get policy {policy_name}: {e}'
                )
            log.error(f'Failed to get policy {policy_name}: {e}')
            return None

    @staticmethod
    def create_managed_policy(account_id: str, region: str, policy_name: str, policy: str):
        try:
            client = IAM.client(account_id, region)
            response = client.create_policy(
                PolicyName=policy_name,
                PolicyDocument=policy,
            )
            arn = response['Policy']['Arn']
            log.info(f'Created managed policy {arn}')
            return arn
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                raise Exception(
                    f'Data.all Environment Pivot Role does not have permissions to create managed policy {policy_name}: {e}'
                )
            raise Exception(f'Failed to create managed policy {policy_name} : {e}')

    @staticmethod
    def delete_managed_policy_by_name(account_id: str, region: str, policy_name):
        try:
            arn = f'arn:aws:iam::{account_id}:policy/{policy_name}'
            client = IAM.client(account_id, region)
            client.delete_policy(PolicyArn=arn)
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                raise Exception(
                    f'Data.all Environment Pivot Role does not have permissions to delete managed policy {policy_name}: {e}'
                )
            raise Exception(f'Failed to delete managed policy {policy_name} : {e}')

    @staticmethod
    def get_managed_policy_default_version(account_id: str, region: str, policy_name: str):
        try:
            arn = f'arn:aws:iam::{account_id}:policy/{policy_name}'
            client = IAM.client(account_id, region)
            response = client.get_policy(PolicyArn=arn)
            versionId = response['Policy']['DefaultVersionId']
            policyVersion = client.get_policy_version(PolicyArn=arn, VersionId=versionId)
            policyDocument = policyVersion['PolicyVersion']['Document']
            return versionId, policyDocument
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                raise Exception(
                    f'Data.all Environment Pivot Role does not have permissions to get policy {policy_name}: {e}'
                )
            log.error(f'Failed to get policy {policy_name} : {e}')
            return None, None

    @staticmethod
    def update_managed_policy_default_version(
        account_id: str, region: str, policy_name: str, old_version_id: str, policy_document: str
    ):
        try:
            arn = f'arn:aws:iam::{account_id}:policy/{policy_name}'
            client = IAM.client(account_id, region)
            client.create_policy_version(PolicyArn=arn, PolicyDocument=policy_document, SetAsDefault=True)

            client.delete_policy_version(PolicyArn=arn, VersionId=old_version_id)
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                raise Exception(
                    f'Data.all Environment Pivot Role does not have permissions to update policy {policy_name}: {e}'
                )
            raise Exception(f'Failed to update policy {policy_name} : {e}')

    @staticmethod
    def delete_managed_policy_non_default_versions(
        account_id: str,
        region: str,
        policy_name: str,
    ):
        try:
            arn = f'arn:aws:iam::{account_id}:policy/{policy_name}'
            client = IAM.client(account_id, region)

            # List all policy versions
            paginator = client.get_paginator('list_policy_versions')
            pages = paginator.paginate(PolicyArn=arn)
            versions = []
            for page in pages:
                versions += page['Versions']
            non_default_versions = [
                version['VersionId'] for version in versions if version['IsDefaultVersion'] is False
            ]
            # Delete all non-default versions
            for version_id in non_default_versions:
                client.delete_policy_version(PolicyArn=arn, VersionId=version_id)

            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                raise Exception(
                    f'Data.all Environment Pivot Role does not have permissions to get policy {policy_name}: {e}'
                )
            log.error(f'Failed to get policy {policy_name} : {e}')
            return None, None

    @staticmethod
    def is_policy_attached(account_id: str, region: str, policy_name: str, role_name: str):
        try:
            client = IAM.client(account_id, region)
            paginator = client.get_paginator('list_attached_role_policies')
            pages = paginator.paginate(RoleName=role_name)
            policies = []
            for page in pages:
                policies += page['AttachedPolicies']
            return policy_name in [p['PolicyName'] for p in policies]
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                raise Exception(
                    f'Data.all Environment Pivot Role does not have permissions to to get the list of attached policies to the role {role_name}: {e}'
                )
            log.error(f'Failed to get the list of attached policies to the role {role_name}: {e}')
            return False

    @staticmethod
    def attach_role_policy(account_id, region: str, role_name, policy_arn):
        try:
            client = IAM.client(account_id, region)
            response = client.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                raise Exception(
                    f'Data.all Environment Pivot Role does not have permissions to to attach policy {policy_arn} to the role {role_name}: {e}'
                )
            log.error(f'Failed to attach policy {policy_arn} to the role {role_name}: {e}')
            raise e

    @staticmethod
    def detach_policy_from_role(account_id: str, region: str, role_name: str, policy_name: str):
        try:
            arn = f'arn:aws:iam::{account_id}:policy/{policy_name}'
            client = IAM.client(account_id, region)
            client.detach_role_policy(RoleName=role_name, PolicyArn=arn)
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                raise Exception(
                    f'Data.all Environment Pivot Role does not have permissions to detach policy {policy_name} from role {role_name}: {e}'
                )
            raise Exception(f'Failed to detach policy {policy_name} from role {role_name}: {e}')

    @staticmethod
    def get_all_role_ids(account_id: str, region: str):
        """
        Get all role ids of an account. Without any filter, it's not supported by boto3
        :param account_id:
        :param region:
        :return:
        """
        try:
            client = IAM.client(account_id, region)
            response = client.list_roles()['Roles']
            return [role['RoleId'] for role in response]
        except Exception as e:
            log.error(f'Failed to get all role ids of {account_id} : {e}')
            return []

    @staticmethod
    def remove_invalid_role_ids(account_id: str, region: str, principal_list):
        """
        Gets all ids of account roles and
        removes all other role ids from the principal list.
        :param account_id:
        :param region:
        :param principal_list:
        :return:
        """
        all_role_ids = IAM.get_all_role_ids(account_id, region)
        for p_id in principal_list[:]:
            if 'AROA' in p_id:
                if p_id not in all_role_ids:
                    principal_list.remove(p_id)

    @staticmethod
    def get_attached_managed_policies_to_role(account_id: str, region: str, role_name: str):
        try:
            client = IAM.client(account_id, region)
            response = client.list_attached_role_policies(RoleName=role_name)
            return [policy.get('PolicyName') for policy in response['AttachedPolicies']]
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                raise Exception(
                    f'Data.all Environment Pivot Role does not have permissions to get attached managed policies for {role_name}: {e}'
                )
            raise Exception(f'Failed to get attached managed policies for {role_name}: {e}')

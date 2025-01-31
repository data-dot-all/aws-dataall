import logging
import json
import time
from itertools import count
from typing import List
from warnings import warn

from dataall.base.db.exceptions import AWSServiceQuotaExceeded
from dataall.core.environment.services.environment_service import EnvironmentService
from dataall.base.db import utils
from dataall.base.aws.sts import SessionHelper
from dataall.modules.s3_datasets_shares.aws.s3_client import (
    S3ControlClient,
    S3Client,
    DATAALL_ALLOW_OWNER_SID,
    DATAALL_DELEGATE_TO_ACCESS_POINT,
)
from dataall.modules.s3_datasets_shares.aws.kms_client import (
    KmsClient,
    DATAALL_KMS_PIVOT_ROLE_PERMISSIONS_SID,
)
from dataall.base.aws.iam import IAM
from dataall.modules.s3_datasets_shares.services.s3_share_alarm_service import S3ShareAlarmService
from dataall.modules.s3_datasets_shares.services.share_managers.s3_utils import (
    get_principal_list,
    add_target_arn_to_statement_principal,
    generate_policy_statement,
    perms_to_sids,
    SidType,
    perms_to_actions,
)
from dataall.modules.shares_base.db.share_object_repositories import ShareObjectRepository
from dataall.modules.shares_base.services.share_exceptions import PrincipalRoleNotFound
from dataall.modules.shares_base.services.share_manager_utils import ShareErrorFormatter
from dataall.modules.s3_datasets_shares.services.s3_share_managed_policy_service import (
    S3SharePolicyService,
    IAM_S3_ACCESS_POINTS_STATEMENT_SID,
)
from dataall.modules.shares_base.services.share_notification_service import ShareNotificationService
from dataall.modules.shares_base.services.shares_enums import PrincipalType
from dataall.modules.s3_datasets.db.dataset_models import DatasetStorageLocation, S3Dataset
from dataall.modules.shares_base.services.sharing_service import ShareData

logger = logging.getLogger(__name__)


class S3AccessPointShareManager:
    def __init__(
        self,
        session,
        share_data: ShareData,
        target_folder: DatasetStorageLocation,
    ):
        self.session = session
        self.source_env_group = share_data.source_env_group
        self.env_group = share_data.env_group
        self.dataset = share_data.dataset
        self.share = share_data.share
        self.target_folder = target_folder
        self.source_environment = share_data.source_environment
        self.target_environment = share_data.target_environment
        self.share_item = ShareObjectRepository.find_sharable_item(
            session,
            share_data.share.shareUri,
            target_folder.locationUri,
        )
        self.access_point_name = self.build_access_point_name(share=share_data.share)

        self.source_account_id = share_data.dataset.AwsAccountId
        self.target_account_id = share_data.target_environment.AwsAccountId
        self.source_env_admin = share_data.source_env_group.environmentIAMRoleArn
        self.target_requester_IAMRoleName = share_data.share.principalRoleName
        self.bucket_name = target_folder.S3BucketName
        self.dataset_admin = share_data.dataset.IAMDatasetAdminRoleArn
        self.dataset_account_id = share_data.dataset.AwsAccountId
        self.dataset_region = share_data.dataset.region
        self.s3_prefix = target_folder.S3Prefix
        self.folder_errors = []

    @staticmethod
    def build_access_point_name(share):
        S3AccessPointName = utils.slugify(
            share.datasetUri + '-' + share.principalId,
            max_length=50,
            lowercase=True,
            regex_pattern='[^a-zA-Z0-9-]',
            separator='-',
        )
        logger.info(f'S3AccessPointName={S3AccessPointName}')
        return S3AccessPointName

    def check_bucket_policy(self) -> None:
        """
        This function will check if delegate access to access point statemnt is in the bucket policy
        and add to folder errors if check fails
        :return: None
        """
        s3_client = S3Client(self.source_account_id, self.source_environment.region)
        bucket_policy = s3_client.get_bucket_policy(self.bucket_name)
        error = False
        if not bucket_policy:
            error = True
        else:
            bucket_policy = json.loads(bucket_policy)
            counter = count()
            statements = {item.get('Sid', next(counter)): item for item in bucket_policy.get('Statement', {})}

            if DATAALL_DELEGATE_TO_ACCESS_POINT not in statements.keys():
                error = True
        if error:
            self.folder_errors.append(
                ShareErrorFormatter.dne_error_msg(
                    f'Bucket Policy {DATAALL_DELEGATE_TO_ACCESS_POINT}', f'{self.bucket_name}'
                )
            )

    def manage_bucket_policy(self):
        """
        This function will manage bucket policy by grant admin access to dataset admin, pivot role
        and environment admin. All of the policies will only be added once.
        :return:
        """
        logger.info(f'Manage Bucket policy for {self.bucket_name}')

        bucket_policy = self.get_bucket_policy_or_default()
        counter = count()
        statements = {item.get('Sid', next(counter)): item for item in bucket_policy.get('Statement', {})}

        if DATAALL_DELEGATE_TO_ACCESS_POINT not in statements.keys():
            statements[DATAALL_DELEGATE_TO_ACCESS_POINT] = {
                'Sid': DATAALL_DELEGATE_TO_ACCESS_POINT,
                'Effect': 'Allow',
                'Principal': '*',
                'Action': 's3:*',
                'Resource': [f'arn:aws:s3:::{self.bucket_name}', f'arn:aws:s3:::{self.bucket_name}/*'],
                'Condition': {'StringEquals': {'s3:DataAccessPointAccount': f'{self.source_account_id}'}},
            }
        bucket_policy['Statement'] = list(statements.values())
        s3_client = S3Client(self.source_account_id, self.source_environment.region)
        s3_client.create_bucket_policy(self.bucket_name, json.dumps(bucket_policy))

    def get_bucket_policy_or_default(self):
        """
        Fetches the existing bucket policy for the S3 bucket if one exists otherwise returns the default bucket policy
        :return:
        """
        s3_client = S3Client(self.source_account_id, self.source_environment.region)
        bucket_policy = s3_client.get_bucket_policy(self.bucket_name)
        if bucket_policy:
            logger.info(
                f'There is already an existing policy for bucket {self.bucket_name}, will be updating policy...'
            )
            bucket_policy = json.loads(bucket_policy)
        else:
            logger.info('Bucket policy for {self.bucket_name} does not exist, generating default policy...')
            bucket_policy = S3ControlClient.generate_default_bucket_policy(self.bucket_name)
        return bucket_policy

    def check_target_role_access_policy(self) -> None:
        """
        Checks if requester IAM role policy includes requested S3 bucket and access point
        and add to folder errors if check fails
        :return: None
        """
        logger.info(f'Check target role {self.target_requester_IAMRoleName} access policy')

        key_alias = f'alias/{self.dataset.KmsAlias}'
        kms_client = KmsClient(self.dataset_account_id, self.source_environment.region)
        kms_key_id = kms_client.get_key_id(key_alias)
        share_policy_service = S3SharePolicyService(
            role_name=self.target_requester_IAMRoleName,
            account=self.target_environment.AwsAccountId,
            region=self.target_environment.region,
            environmentUri=self.target_environment.environmentUri,
            resource_prefix=self.target_environment.resourcePrefix,
        )
        share_policy_service.initialize_statements()

        share_resource_policy_name = share_policy_service.generate_indexed_policy_name(index=0)
        is_managed_policies_exists = True if share_policy_service.get_managed_policies() else False

        # Checking if managed policies without indexes are present. This is used for backward compatibility
        if not is_managed_policies_exists:
            warn(
                "Convert all your share's requestor policies to managed policies with indexes.",
                DeprecationWarning,
                stacklevel=2,
            )
            old_managed_policy_name = share_policy_service.generate_old_policy_name()
            old_policy_exist = share_policy_service.check_if_policy_exists(policy_name=old_managed_policy_name)
            if not old_policy_exist:
                logger.info(
                    f'No managed policy exists for the role: {self.target_requester_IAMRoleName}, Reapply share to create indexed managed policies.'
                )
                self.folder_errors.append(ShareErrorFormatter.dne_error_msg('IAM Policy', share_resource_policy_name))
                return
            else:
                logger.info(
                    f'Old managed policy exists for the role: {self.target_requester_IAMRoleName}. Reapply share to create indexed managed policies.'
                )
                self.folder_errors.append(ShareErrorFormatter.dne_error_msg('IAM Policy', share_resource_policy_name))
                return

        unattached_policies: List[str] = share_policy_service.get_policies_unattached_to_role()
        if len(unattached_policies) > 0:
            logger.info(
                f'IAM Policies {unattached_policies} exists but are not attached to role {self.share.principalRoleName}'
            )
            self.folder_errors.append(ShareErrorFormatter.dne_error_msg('IAM Policy attached', unattached_policies))
            return

        s3_target_resources = [
            f'arn:aws:s3:::{self.bucket_name}',
            f'arn:aws:s3:::{self.bucket_name}/*',
            f'arn:aws:s3:{self.dataset_region}:{self.dataset_account_id}:accesspoint/{self.access_point_name}',
            f'arn:aws:s3:{self.dataset_region}:{self.dataset_account_id}:accesspoint/{self.access_point_name}/*',
        ]

        if not S3SharePolicyService.check_if_sid_exists(
            f'{IAM_S3_ACCESS_POINTS_STATEMENT_SID}S3', share_policy_service.total_s3_access_point_stmts
        ):
            logger.info(
                f'IAM Policy Statement with Sid: {IAM_S3_ACCESS_POINTS_STATEMENT_SID}S3<index> - where <index> can be 0,1,2.. -  does not exist'
            )
            self.folder_errors.append(
                ShareErrorFormatter.missing_permission_error_msg(
                    self.target_requester_IAMRoleName,
                    'IAM Policy Statement Sid',
                    f'{IAM_S3_ACCESS_POINTS_STATEMENT_SID}S3<index>',
                    'S3 Bucket',
                    f'{self.bucket_name}',
                )
            )
        elif not share_policy_service.check_resource_in_policy_statements(
            target_resources=s3_target_resources,
            existing_policy_statements=share_policy_service.total_s3_access_point_stmts,
        ):
            logger.info(
                f'IAM Policy Statement with Sid {IAM_S3_ACCESS_POINTS_STATEMENT_SID}S3<index> - where <index> can be 0,1,2.. - does not contain resources {s3_target_resources}'
            )
            self.folder_errors.append(
                ShareErrorFormatter.missing_permission_error_msg(
                    self.target_requester_IAMRoleName,
                    'IAM Policy Resource(s)',
                    f'{IAM_S3_ACCESS_POINTS_STATEMENT_SID}S3<index>',
                    'S3 Bucket',
                    f'{self.bucket_name}',
                )
            )
        else:
            policy_sid_actions_map = share_policy_service.check_s3_actions_in_policy_statements(
                existing_policy_statements=share_policy_service.total_s3_access_point_stmts
            )
            for sid in policy_sid_actions_map:
                policy_check = policy_sid_actions_map[sid].get('policy_check')
                missing_permissions = policy_sid_actions_map[sid].get('missing_permissions')
                extra_permissions = policy_sid_actions_map[sid].get('extra_permissions')
                # Check if policy violations are present
                if policy_check:
                    logger.info(f'IAM Policy Statement {sid} has invalid actions')
                    if missing_permissions:
                        self.folder_errors.append(
                            ShareErrorFormatter.missing_permission_error_msg(
                                self.target_requester_IAMRoleName,
                                'IAM Policy Action',
                                missing_permissions,
                                'S3 Bucket',
                                f'{self.bucket_name}',
                            )
                        )
                    if extra_permissions:
                        self.folder_errors.append(
                            ShareErrorFormatter.not_allowed_permission_error_msg(
                                self.target_requester_IAMRoleName,
                                'IAM Policy Action',
                                extra_permissions,
                                'S3 Bucket',
                                f'{self.bucket_name}',
                            )
                        )

        if kms_key_id:
            kms_target_resources = [f'arn:aws:kms:{self.dataset_region}:{self.dataset_account_id}:key/{kms_key_id}']

            if not S3SharePolicyService.check_if_sid_exists(
                f'{IAM_S3_ACCESS_POINTS_STATEMENT_SID}KMS', share_policy_service.total_s3_access_point_kms_stmts
            ):
                logger.info(
                    f'IAM Policy Statement with Sid: {IAM_S3_ACCESS_POINTS_STATEMENT_SID}KMS<index> - where <index> can be 0,1,2.. - does not exist'
                )
                self.folder_errors.append(
                    ShareErrorFormatter.missing_permission_error_msg(
                        self.target_requester_IAMRoleName,
                        'IAM Policy Statement',
                        f'{IAM_S3_ACCESS_POINTS_STATEMENT_SID}KMS<index>',
                        'KMS Key',
                        f'{kms_key_id}',
                    )
                )
            elif not share_policy_service.check_resource_in_policy_statements(
                target_resources=kms_target_resources,
                existing_policy_statements=share_policy_service.total_s3_access_point_kms_stmts,
            ):
                logger.info(
                    f'IAM Policy Statement {IAM_S3_ACCESS_POINTS_STATEMENT_SID}KMS<index> - where <index> can be 0,1,2.. - does not contain resources {kms_target_resources}'
                )
                self.folder_errors.append(
                    ShareErrorFormatter.missing_permission_error_msg(
                        self.target_requester_IAMRoleName,
                        'IAM Policy Resource',
                        f'{IAM_S3_ACCESS_POINTS_STATEMENT_SID}KMS<index>',
                        'KMS Key',
                        f'{kms_key_id}',
                    )
                )

    def grant_target_role_access_policy(self):
        """
        Updates requester IAM role policy to include requested S3 bucket and access point
        :returns: None or raises exception if something fails
        """
        logger.info(f'Grant target role {self.target_requester_IAMRoleName} access policy')

        share_policy_service = S3SharePolicyService(
            role_name=self.target_requester_IAMRoleName,
            account=self.target_environment.AwsAccountId,
            region=self.target_environment.region,
            environmentUri=self.target_environment.environmentUri,
            resource_prefix=self.target_environment.resourcePrefix,
        )
        # Process all backwards compatibility tasks and convert to indexed policies
        share_policy_service.process_backwards_compatibility_for_target_iam_roles()

        # Parses all policy documents and extracts s3 and kms statements
        share_policy_service.initialize_statements()

        key_alias = f'alias/{self.dataset.KmsAlias}'
        kms_client = KmsClient(self.dataset_account_id, self.source_environment.region)
        kms_key_id = kms_client.get_key_id(key_alias)

        s3_target_resources = [
            f'arn:aws:s3:::{self.bucket_name}',
            f'arn:aws:s3:::{self.bucket_name}/*',
            f'arn:aws:s3:{self.dataset_region}:{self.dataset_account_id}:accesspoint/{self.access_point_name}',
            f'arn:aws:s3:{self.dataset_region}:{self.dataset_account_id}:accesspoint/{self.access_point_name}/*',
        ]
        kms_target_resources = []
        if kms_key_id:
            kms_target_resources = [f'arn:aws:kms:{self.dataset_region}:{self.dataset_account_id}:key/{kms_key_id}']

        s3_statements = share_policy_service.total_s3_access_point_stmts
        s3_statement_chunks = share_policy_service.add_resources_and_generate_split_statements(
            statements=s3_statements,
            target_resources=s3_target_resources,
            sid=f'{IAM_S3_ACCESS_POINTS_STATEMENT_SID}S3',
            resource_type='s3',
        )
        logger.info(f'Number of S3 statements created after splitting: {len(s3_statement_chunks)}')
        logger.debug(f'S3 statements after adding resources and splitting: {s3_statement_chunks}')

        s3_kms_statements = share_policy_service.total_s3_access_point_kms_stmts
        s3_kms_statement_chunks = share_policy_service.add_resources_and_generate_split_statements(
            statements=s3_kms_statements,
            target_resources=kms_target_resources,
            sid=f'{IAM_S3_ACCESS_POINTS_STATEMENT_SID}KMS',
            resource_type='kms',
        )
        logger.info(f'Number of S3 KMS statements created after splitting: {len(s3_kms_statement_chunks)}')
        logger.debug(f'S3 KMS statements after adding resources and splitting: {s3_kms_statement_chunks}')

        try:
            share_policy_service.merge_statements_and_update_policies(
                target_sid=IAM_S3_ACCESS_POINTS_STATEMENT_SID,
                target_s3_statements=s3_statement_chunks,
                target_s3_kms_statements=s3_kms_statement_chunks,
            )
        except AWSServiceQuotaExceeded as e:
            error_message = e.message
            try:
                ShareNotificationService(
                    session=None, dataset=self.dataset, share=self.share
                ).notify_managed_policy_limit_exceeded_action(email_id=self.share.owner)
            except Exception as e:
                logger.error(
                    f'Error sending email for notifying that managed policy limit exceeded on role due to: {e}'
                )
            finally:
                raise Exception(error_message)

        is_unattached_policies = share_policy_service.get_policies_unattached_to_role()
        if is_unattached_policies:
            logger.info(
                f'Found some policies are not attached to the target IAM role: {self.target_requester_IAMRoleName}. Attaching policies now'
            )
            if self.share.principalType == PrincipalType.Group.value:
                share_managed_policies = share_policy_service.get_managed_policies()
                share_policy_service.attach_policies(share_managed_policies)
            else:
                consumption_role = EnvironmentService.get_consumption_role(
                    session=self.session, uri=self.share.principalId
                )
                if consumption_role.dataallManaged:
                    share_managed_policies = share_policy_service.get_managed_policies()
                    share_policy_service.attach_policies(share_managed_policies)

    def check_access_point_and_policy(self) -> None:
        """
        Checks if access point created with correct permissions
        and add to folder errors if check fails
        :return: None
        """
        s3_client = S3ControlClient(self.source_account_id, self.source_environment.region)
        access_point_arn = s3_client.get_bucket_access_point_arn(self.access_point_name)
        if not access_point_arn:
            self.folder_errors.append(ShareErrorFormatter.dne_error_msg('Access Point', self.access_point_name))
            return

        existing_policy = s3_client.get_access_point_policy(self.access_point_name)
        if not existing_policy:
            self.folder_errors.append(ShareErrorFormatter.dne_error_msg('Access Point Policy', self.access_point_name))
            return

        existing_policy = json.loads(existing_policy)
        statements = {item['Sid']: item for item in existing_policy['Statement']}
        target_requester_id = SessionHelper.get_role_id(
            self.target_account_id, self.target_environment.region, self.target_requester_IAMRoleName
        )
        error = False
        if f'{target_requester_id}0' not in statements.keys():
            error = True
        else:
            prefix_list = (
                statements[f'{target_requester_id}0'].get('Condition', {}).get('StringLike', {}).get('s3:prefix', [])
            )
            if isinstance(prefix_list, str):
                prefix_list = [prefix_list]
            if f'{self.s3_prefix}/*' not in prefix_list:
                error = True
        if error:
            self.folder_errors.append(
                ShareErrorFormatter.missing_permission_error_msg(
                    self.target_requester_IAMRoleName,
                    'Policy',
                    f'{target_requester_id}0',
                    'Access Point',
                    self.access_point_name,
                )
            )

        error1 = False
        if f'{target_requester_id}1' not in statements.keys():
            error1 = True
        else:
            resource_list = statements[f'{target_requester_id}1'].get('Resource', [])
            if isinstance(resource_list, str):
                resource_list = [resource_list]
            if f'{access_point_arn}/object/{self.s3_prefix}/*' not in resource_list:
                error1 = True
        if error1:
            self.folder_errors.append(
                ShareErrorFormatter.missing_permission_error_msg(
                    self.target_requester_IAMRoleName,
                    'Policy',
                    f'{target_requester_id}1',
                    'Access Point',
                    self.access_point_name,
                )
            )

    def manage_access_point_and_policy(self):
        """
        :return:
        """

        s3_client = S3ControlClient(self.source_account_id, self.source_environment.region)
        access_point_arn = s3_client.create_bucket_access_point(self.bucket_name, self.access_point_name)
        if not access_point_arn:
            raise Exception('Failed to create access point')
        existing_policy = s3_client.get_access_point_policy(self.access_point_name)
        # requester will use this role to access resources
        target_requester_id = SessionHelper.get_role_id(
            self.target_account_id, self.target_environment.region, self.target_requester_IAMRoleName
        )
        if existing_policy:
            # Update existing access point policy
            logger.info(
                f'There is already an existing access point {access_point_arn} with an existing policy, updating policy...'
            )
            existing_policy = json.loads(existing_policy)
            statements = {item['Sid']: item for item in existing_policy['Statement']}
            if f'{target_requester_id}0' in statements.keys():
                prefix_list = statements[f'{target_requester_id}0']['Condition']['StringLike']['s3:prefix']
                if isinstance(prefix_list, str):
                    prefix_list = [prefix_list]
                if f'{self.s3_prefix}/*' not in prefix_list:
                    prefix_list.append(f'{self.s3_prefix}/*')
                    statements[f'{target_requester_id}0']['Condition']['StringLike']['s3:prefix'] = prefix_list
                resource_list = statements[f'{target_requester_id}1']['Resource']
                if isinstance(resource_list, str):
                    resource_list = [resource_list]
                if f'{access_point_arn}/object/{self.s3_prefix}/*' not in resource_list:
                    resource_list.append(f'{access_point_arn}/object/{self.s3_prefix}/*')
                    statements[f'{target_requester_id}1']['Resource'] = resource_list
                existing_policy['Statement'] = list(statements.values())
            else:
                additional_policy = S3ControlClient.generate_access_point_policy_template(
                    target_requester_id,
                    access_point_arn,
                    self.s3_prefix,
                    perms_to_actions(self.share.permissions, SidType.BucketPolicy),
                )
                existing_policy['Statement'].extend(additional_policy['Statement'])
            access_point_policy = existing_policy
        else:
            # First time to create access point policy
            logger.info(f'Access point policy for access point {access_point_arn} does not exists, creating policy...')
            access_point_policy = S3ControlClient.generate_access_point_policy_template(
                target_requester_id,
                access_point_arn,
                self.s3_prefix,
                perms_to_actions(self.share.permissions, SidType.BucketPolicy),
            )
        s3_client.attach_access_point_policy(
            access_point_name=self.access_point_name, policy=json.dumps(access_point_policy)
        )

    def check_dataset_bucket_key_policy(self) -> None:
        """
        Checks if dataset kms key policy includes read permissions for requestors IAM Role
        and add to folder errors if check fails
        :return: None
        """
        key_alias = f'alias/{self.dataset.KmsAlias}'
        kms_client = KmsClient(self.source_account_id, self.source_environment.region)
        kms_key_id = kms_client.get_key_id(key_alias)
        existing_policy = kms_client.get_key_policy(kms_key_id)

        if not existing_policy:
            self.folder_errors.append(ShareErrorFormatter.dne_error_msg('KMS Key Policy', kms_key_id))
            return

        target_requester_arn = IAM.get_role_arn_by_name(
            self.target_account_id, self.target_environment.region, self.target_requester_IAMRoleName
        )
        existing_policy = json.loads(existing_policy)
        counter = count()
        statements = {item.get('Sid', next(counter)): item for item in existing_policy.get('Statement', {})}

        for target_sid in perms_to_sids(self.share.permissions, SidType.KmsAccessPointPolicy):
            if target_sid not in statements.keys() or target_requester_arn not in get_principal_list(
                statements[target_sid]
            ):
                self.folder_errors.append(
                    ShareErrorFormatter.missing_permission_error_msg(
                        self.target_requester_IAMRoleName,
                        'KMS Key Policy',
                        target_sid,
                        'KMS Key',
                        f'{kms_key_id}',
                    )
                )

    def update_dataset_bucket_key_policy(self):
        logger.info('Updating dataset Bucket KMS key policy...')
        key_alias = f'alias/{self.dataset.KmsAlias}'
        kms_client = KmsClient(self.source_account_id, self.source_environment.region)
        kms_key_id = kms_client.get_key_id(key_alias)
        existing_policy = kms_client.get_key_policy(kms_key_id)
        target_requester_arn = IAM.get_role_arn_by_name(
            self.target_account_id, self.target_environment.region, self.target_requester_IAMRoleName
        )

        if not target_requester_arn:
            raise PrincipalRoleNotFound(
                'update dataset bucket key policy',
                f'Principal role {self.target_requester_IAMRoleName} is not found. Failed to update KMS key policy',
            )

        pivot_role_name = SessionHelper.get_delegation_role_name(self.source_environment.region)

        if existing_policy:
            existing_policy = json.loads(existing_policy)
            counter = count()
            statements = {item.get('Sid', next(counter)): item for item in existing_policy.get('Statement', {})}

            if DATAALL_KMS_PIVOT_ROLE_PERMISSIONS_SID in statements.keys():
                logger.info(
                    f'KMS key policy already contains share statement {DATAALL_KMS_PIVOT_ROLE_PERMISSIONS_SID}, updating existing statement'
                )

            else:
                logger.info(
                    f'KMS key policy does not contain statement {DATAALL_KMS_PIVOT_ROLE_PERMISSIONS_SID}, generating a new one'
                )
            statements[DATAALL_KMS_PIVOT_ROLE_PERMISSIONS_SID] = (
                self.generate_enable_pivot_role_permissions_policy_statement(pivot_role_name, self.dataset_account_id)
            )

            for target_sid in perms_to_sids(self.share.permissions, SidType.KmsAccessPointPolicy):
                if target_sid in statements.keys():
                    logger.info(f'KMS key policy contains share statement {target_sid}, updating the current one')
                    statements[target_sid] = add_target_arn_to_statement_principal(
                        statements[target_sid], target_requester_arn
                    )
                else:
                    logger.info(f'KMS key does not contain share statement {target_sid}, generating a new one')
                    statements[target_sid] = self.generate_default_kms_policy_statement(
                        target_requester_arn, target_sid
                    )
            existing_policy['Statement'] = list(statements.values())

        else:
            logger.info('KMS key policy does not contain any statements, generating a new one')
            existing_policy = {
                'Version': '2012-10-17',
                'Statement': [
                    self.generate_enable_pivot_role_permissions_policy_statement(
                        pivot_role_name, self.dataset_account_id
                    ),
                ]
                + [
                    self.generate_default_kms_policy_statement(target_requester_arn, target_sid)
                    for target_sid in perms_to_sids(self.share.permissions, SidType.KmsAccessPointPolicy)
                ],
            }
        kms_client.put_key_policy(kms_key_id, json.dumps(existing_policy))

    def revoke_access_in_access_point_policy(self):
        logger.info(f'Generating new access point policy for access point {self.access_point_name}...')
        s3_client = S3ControlClient(self.source_account_id, self.source_environment.region)
        access_point_policy = json.loads(s3_client.get_access_point_policy(self.access_point_name))
        access_point_arn = s3_client.get_bucket_access_point_arn(self.access_point_name)
        target_requester_id = SessionHelper.get_role_id(
            self.target_account_id, self.target_environment.region, self.target_requester_IAMRoleName
        )
        statements = {item['Sid']: item for item in access_point_policy['Statement']}
        if f'{target_requester_id}0' in statements.keys():
            prefix_list = statements[f'{target_requester_id}0']['Condition']['StringLike']['s3:prefix']
            if f'{self.s3_prefix}/*' in prefix_list:
                logger.info(f'Removing folder {self.s3_prefix} from access point policy...')
                if isinstance(prefix_list, list):
                    prefix_list.remove(f'{self.s3_prefix}/*')
                    statements[f'{target_requester_id}1']['Resource'].remove(
                        f'{access_point_arn}/object/{self.s3_prefix}/*'
                    )
                    access_point_policy['Statement'] = list(statements.values())
                elif isinstance(prefix_list, str):
                    prefix_list = []
            else:
                logger.info(f'Folder {self.s3_prefix} already removed from access point policy, skipping...')

            if len(prefix_list) == 0:
                logger.info('Removing empty statements from access point policy...')
                access_point_policy['Statement'].remove(statements[f'{target_requester_id}0'])
                access_point_policy['Statement'].remove(statements[f'{target_requester_id}1'])
                # We need to handle DATAALL_ALLOW_OWNER_SID for backwards compatibility
                if statements.get(DATAALL_ALLOW_OWNER_SID, None) is not None:
                    access_point_policy['Statement'].remove(statements[DATAALL_ALLOW_OWNER_SID])
        return access_point_policy

    def attach_new_access_point_policy(self, access_point_policy):
        logger.info(f'Attaching access point policy {access_point_policy} for access point {self.access_point_name}...')
        s3_client = S3ControlClient(self.source_account_id, self.source_environment.region)
        s3_client.attach_access_point_policy(
            access_point_name=self.access_point_name, policy=json.dumps(access_point_policy)
        )

    def delete_access_point(self):
        logger.info(f'Deleting access point {self.access_point_name}...')
        s3_client = S3ControlClient(self.source_account_id, self.source_environment.region)
        s3_client.delete_bucket_access_point(self.access_point_name)

    def revoke_target_role_access_policy(self):
        logger.info('Deleting target role IAM statements...')

        share_policy_service = S3SharePolicyService(
            role_name=self.target_requester_IAMRoleName,
            account=self.target_environment.AwsAccountId,
            region=self.target_environment.region,
            environmentUri=self.target_environment.environmentUri,
            resource_prefix=self.target_environment.resourcePrefix,
        )
        # Process all backwards compatibility tasks and convert to indexed policies
        share_policy_service.process_backwards_compatibility_for_target_iam_roles()

        # Parses all policy documents and extracts s3 and kms statements
        share_policy_service.initialize_statements()

        key_alias = f'alias/{self.dataset.KmsAlias}'
        kms_client = KmsClient(self.dataset_account_id, self.source_environment.region)
        kms_key_id = kms_client.get_key_id(key_alias)

        s3_target_resources = [
            f'arn:aws:s3:::{self.bucket_name}',
            f'arn:aws:s3:::{self.bucket_name}/*',
            f'arn:aws:s3:{self.dataset_region}:{self.dataset_account_id}:accesspoint/{self.access_point_name}',
            f'arn:aws:s3:{self.dataset_region}:{self.dataset_account_id}:accesspoint/{self.access_point_name}/*',
        ]

        kms_target_resources = []
        if kms_key_id:
            kms_target_resources = [f'arn:aws:kms:{self.dataset_region}:{self.dataset_account_id}:key/{kms_key_id}']

        managed_policy_exists = True if share_policy_service.get_managed_policies() else False

        if not managed_policy_exists:
            logger.info(f'Managed policies for share with uri: {self.share.shareUri} are not found')
            return

        s3_statements = share_policy_service.total_s3_access_point_stmts
        s3_statement_chunks = share_policy_service.remove_resources_and_generate_split_statements(
            statements=s3_statements,
            target_resources=s3_target_resources,
            sid=f'{IAM_S3_ACCESS_POINTS_STATEMENT_SID}S3',
            resource_type='s3',
        )
        logger.info(f'Number of S3 statements created after splitting: {len(s3_statement_chunks)}')
        logger.debug(f'S3 statements after adding resources and splitting: {s3_statement_chunks}')

        s3_kms_statements = share_policy_service.total_s3_access_point_kms_stmts
        s3_kms_statement_chunks = share_policy_service.remove_resources_and_generate_split_statements(
            statements=s3_kms_statements,
            target_resources=kms_target_resources,
            sid=f'{IAM_S3_ACCESS_POINTS_STATEMENT_SID}KMS',
            resource_type='kms',
        )
        logger.info(f'Number of S3 KMS statements created after splitting: {len(s3_kms_statement_chunks)}')
        logger.debug(f'S3 KMS statements after adding resources and splitting: {s3_kms_statement_chunks}')

        share_policy_service.merge_statements_and_update_policies(
            target_sid=IAM_S3_ACCESS_POINTS_STATEMENT_SID,
            target_s3_statements=s3_statement_chunks,
            target_s3_kms_statements=s3_kms_statement_chunks,
        )

    def delete_dataset_bucket_key_policy(
        self,
        dataset: S3Dataset,
    ):
        logger.info('Deleting dataset bucket KMS key policy...')
        key_alias = f'alias/{dataset.KmsAlias}'
        kms_client = KmsClient(dataset.AwsAccountId, dataset.region)
        kms_key_id = kms_client.get_key_id(key_alias)
        existing_policy = json.loads(kms_client.get_key_policy(kms_key_id))
        target_requester_arn = IAM.get_role_arn_by_name(
            self.target_account_id, self.target_environment.region, self.target_requester_IAMRoleName
        )
        counter = count()
        statements = {item.get('Sid', next(counter)): item for item in existing_policy.get('Statement', {})}

        for target_sid in perms_to_sids(self.share.permissions, SidType.KmsAccessPointPolicy):
            if target_sid in statements.keys():
                principal_list = get_principal_list(statements[target_sid])
                if f'{target_requester_arn}' in principal_list:
                    principal_list.remove(f'{target_requester_arn}')
                    if len(principal_list) == 0:
                        statements.pop(target_sid)
                    else:
                        statements[target_sid]['Principal']['AWS'] = principal_list
                    existing_policy['Statement'] = list(statements.values())
                    kms_client.put_key_policy(kms_key_id, json.dumps(existing_policy))

    def handle_share_failure(self, error: Exception) -> None:
        """
        Handles share failure by raising an alarm to alarmsTopic
        Returns
        -------
        True if alarm published successfully
        """
        logger.error(
            f'Failed to share folder {self.s3_prefix} '
            f'from source account {self.source_environment.AwsAccountId}//{self.source_environment.region} '
            f'with target account {self.target_environment.AwsAccountId}/{self.target_environment.region} '
            f'due to: {error}'
        )
        S3ShareAlarmService().trigger_folder_sharing_failure_alarm(
            self.target_folder, self.share, self.target_environment
        )

    def handle_revoke_failure(self, error: Exception) -> bool:
        """
        Handles share failure by raising an alarm to alarmsTopic
        Returns
        -------
        True if alarm published successfully
        """
        logger.error(
            f'Failed to revoke S3 permissions to folder {self.s3_prefix} '
            f'from source account {self.source_environment.AwsAccountId}//{self.source_environment.region} '
            f'with target account {self.target_environment.AwsAccountId}/{self.target_environment.region} '
            f'due to: {error}'
        )
        S3ShareAlarmService().trigger_revoke_folder_sharing_failure_alarm(
            self.target_folder, self.share, self.target_environment
        )
        return True

    @staticmethod
    def generate_default_kms_policy_statement(target_requester_arn, target_sid):
        return generate_policy_statement(target_sid, [target_requester_arn], ['*'])

    @staticmethod
    def generate_enable_pivot_role_permissions_policy_statement(pivot_role_name, dataset_account_id):
        return generate_policy_statement(
            DATAALL_KMS_PIVOT_ROLE_PERMISSIONS_SID, [f'arn:aws:iam::{dataset_account_id}:role/{pivot_role_name}'], ['*']
        )

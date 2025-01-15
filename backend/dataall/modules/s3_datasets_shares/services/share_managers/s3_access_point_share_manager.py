import logging
import json
from itertools import count


from dataall.core.environment.services.environment_service import EnvironmentService
from dataall.base.db import utils
from dataall.base.aws.sts import SessionHelper
from dataall.modules.notifications.services.admin_notifications import AdminNotificationService
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
    EMPTY_STATEMENT_SID,
)
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
            environmentUri=self.target_environment.environmentUri,
            account=self.target_environment.AwsAccountId,
            region=self.target_environment.region,
            role_name=self.target_requester_IAMRoleName,
            resource_prefix=self.target_environment.resourcePrefix,
        )
        share_resource_policy_name = share_policy_service.generate_policy_name()

        if not share_policy_service.check_if_policy_exists():
            logger.info(f'IAM Policy {share_resource_policy_name} does not exist')
            self.folder_errors.append(ShareErrorFormatter.dne_error_msg('IAM Policy', share_resource_policy_name))
            return

        if not share_policy_service.check_if_policy_attached():
            logger.info(
                f'IAM Policy {share_resource_policy_name} exists but is not attached to role {self.share.principalRoleName}'
            )
            self.folder_errors.append(
                ShareErrorFormatter.dne_error_msg('IAM Policy attached', share_resource_policy_name)
            )
            return

        s3_target_resources = [
            f'arn:aws:s3:::{self.bucket_name}',
            f'arn:aws:s3:::{self.bucket_name}/*',
            f'arn:aws:s3:{self.dataset_region}:{self.dataset_account_id}:accesspoint/{self.access_point_name}',
            f'arn:aws:s3:{self.dataset_region}:{self.dataset_account_id}:accesspoint/{self.access_point_name}/*',
        ]

        version_id, policy_document = IAM.get_managed_policy_default_version(
            self.target_environment.AwsAccountId, self.target_environment.region, share_resource_policy_name
        )
        logger.info(f'Policy... {policy_document}')

        s3_statement_index = S3SharePolicyService._get_statement_by_sid(
            policy_document, f'{IAM_S3_ACCESS_POINTS_STATEMENT_SID}S3'
        )

        if s3_statement_index is None:
            logger.info(f'IAM Policy Statement {IAM_S3_ACCESS_POINTS_STATEMENT_SID}S3 does not exist')
            self.folder_errors.append(
                ShareErrorFormatter.missing_permission_error_msg(
                    self.target_requester_IAMRoleName,
                    'IAM Policy Statement',
                    f'{IAM_S3_ACCESS_POINTS_STATEMENT_SID}S3',
                    'S3 Bucket',
                    f'{self.bucket_name}',
                )
            )

        elif not share_policy_service.check_resource_in_policy_statement(
            target_resources=s3_target_resources,
            existing_policy_statement=policy_document['Statement'][s3_statement_index],
        ):
            logger.info(
                f'IAM Policy Statement {IAM_S3_ACCESS_POINTS_STATEMENT_SID}S3 does not contain resources {s3_target_resources}'
            )
            self.folder_errors.append(
                ShareErrorFormatter.missing_permission_error_msg(
                    self.target_requester_IAMRoleName,
                    'IAM Policy Resource',
                    f'{IAM_S3_ACCESS_POINTS_STATEMENT_SID}S3',
                    'S3 Bucket',
                    f'{self.bucket_name}',
                )
            )
        else:
            policy_check, missing_permissions, extra_permissions = (
                share_policy_service.check_s3_actions_in_policy_statement(
                    existing_policy_statement=policy_document['Statement'][s3_statement_index]
                )
            )
            if not policy_check:
                logger.info(f'IAM Policy Statement {IAM_S3_ACCESS_POINTS_STATEMENT_SID}S3 has invalid actions')
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
            kms_statement_index = S3SharePolicyService._get_statement_by_sid(
                policy_document, f'{IAM_S3_ACCESS_POINTS_STATEMENT_SID}KMS'
            )
            kms_target_resources = [f'arn:aws:kms:{self.dataset_region}:{self.dataset_account_id}:key/{kms_key_id}']
            if not kms_statement_index:
                logger.info(f'IAM Policy Statement {IAM_S3_ACCESS_POINTS_STATEMENT_SID}KMS does not exist')
                self.folder_errors.append(
                    ShareErrorFormatter.missing_permission_error_msg(
                        self.target_requester_IAMRoleName,
                        'IAM Policy Statement',
                        f'{IAM_S3_ACCESS_POINTS_STATEMENT_SID}KMS',
                        'KMS Key',
                        f'{kms_key_id}',
                    )
                )

            elif not share_policy_service.check_resource_in_policy_statement(
                target_resources=kms_target_resources,
                existing_policy_statement=policy_document['Statement'][kms_statement_index],
            ):
                logger.info(
                    f'IAM Policy Statement {IAM_S3_ACCESS_POINTS_STATEMENT_SID}KMS does not contain resources {kms_target_resources}'
                )
                self.folder_errors.append(
                    ShareErrorFormatter.missing_permission_error_msg(
                        self.target_requester_IAMRoleName,
                        'IAM Policy Resource',
                        f'{IAM_S3_ACCESS_POINTS_STATEMENT_SID}KMS',
                        'KMS Key',
                        f'{kms_key_id}',
                    )
                )

    def grant_target_role_access_policy(self):
        """
        Updates requester IAM role policy to include requested S3 bucket and access point
        :return:
        """
        logger.info(f'Grant target role {self.target_requester_IAMRoleName} access policy')

        share_policy_service = S3SharePolicyService(
            environmentUri=self.target_environment.environmentUri,
            account=self.target_environment.AwsAccountId,
            region=self.target_environment.region,
            role_name=self.target_requester_IAMRoleName,
            resource_prefix=self.target_environment.resourcePrefix,
        )

        # Backwards compatibility
        # we check if a managed share policy exists. If False, the role was introduced to data.all before this update
        # We create the policy from the inline statements and attach it to the role
        if not share_policy_service.check_if_policy_exists():
            share_policy_service.create_managed_policy_from_inline_and_delete_inline()
            share_policy_service.attach_policy()
        # End of backwards compatibility

        if not share_policy_service.check_if_policy_attached():
            if self.share.principalType == PrincipalType.Group.value:
                share_policy_service.attach_policy()
            else:
                consumption_role = EnvironmentService.get_consumption_role(
                    session=self.session, uri=self.share.principalId
                )
                if consumption_role.dataallManaged:
                    share_policy_service.attach_policy()

        share_resource_policy_name = share_policy_service.generate_policy_name()
        version_id, policy_document = IAM.get_managed_policy_default_version(
            self.target_account_id, self.target_environment.region, share_resource_policy_name
        )

        key_alias = f'alias/{self.dataset.KmsAlias}'
        kms_client = KmsClient(self.dataset_account_id, self.source_environment.region)
        kms_key_id = kms_client.get_key_id(key_alias)

        s3_target_resources = [
            f'arn:aws:s3:::{self.bucket_name}',
            f'arn:aws:s3:::{self.bucket_name}/*',
            f'arn:aws:s3:{self.dataset_region}:{self.dataset_account_id}:accesspoint/{self.access_point_name}',
            f'arn:aws:s3:{self.dataset_region}:{self.dataset_account_id}:accesspoint/{self.access_point_name}/*',
        ]

        share_policy_service.add_missing_resources_to_policy_statement(
            resource_type='s3',
            target_resources=s3_target_resources,
            statement_sid=f'{IAM_S3_ACCESS_POINTS_STATEMENT_SID}S3',
            policy_document=policy_document,
        )

        share_policy_service.remove_empty_statement(policy_doc=policy_document, statement_sid=EMPTY_STATEMENT_SID)

        if kms_key_id:
            kms_target_resources = [f'arn:aws:kms:{self.dataset_region}:{self.dataset_account_id}:key/{kms_key_id}']
            share_policy_service.add_missing_resources_to_policy_statement(
                resource_type='kms',
                target_resources=kms_target_resources,
                statement_sid=f'{IAM_S3_ACCESS_POINTS_STATEMENT_SID}KMS',
                policy_document=policy_document,
            )

        IAM.update_managed_policy_default_version(
            self.target_account_id,
            self.target_environment.region,
            share_resource_policy_name,
            version_id,
            json.dumps(policy_document),
        )

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
                    logger.info(f'KMS key policy contains share statement {target_sid}, ' f'updating the current one')
                    statements[target_sid] = add_target_arn_to_statement_principal(
                        statements[target_sid], target_requester_arn
                    )
                else:
                    logger.info(f'KMS key does not contain share statement {target_sid}, ' f'generating a new one')
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
            environmentUri=self.target_environment.environmentUri,
            account=self.target_environment.AwsAccountId,
            region=self.target_environment.region,
            role_name=self.target_requester_IAMRoleName,
            resource_prefix=self.target_environment.resourcePrefix,
        )

        role_arn = IAM.get_role_arn_by_name(
            self.target_account_id, self.target_environment.region, self.target_requester_IAMRoleName
        )

        # Backwards compatibility
        # we check if a managed share policy exists. If False, the role was introduced to data.all before this update
        # We create the policy from the inline statements and attach it to the role
        if not share_policy_service.check_if_policy_exists() and role_arn:
            share_policy_service.create_managed_policy_from_inline_and_delete_inline()
            share_policy_service.attach_policy()
        # End of backwards compatibility

        share_resource_policy_name = share_policy_service.generate_policy_name()

        version_id, policy_document = IAM.get_managed_policy_default_version(
            self.target_account_id, self.target_environment.region, share_resource_policy_name
        )

        if not policy_document:
            logger.info(f'Policy {share_resource_policy_name} is not found')
            return

        key_alias = f'alias/{self.dataset.KmsAlias}'
        kms_client = KmsClient(self.dataset_account_id, self.source_environment.region)
        kms_key_id = kms_client.get_key_id(key_alias)

        s3_target_resources = [
            f'arn:aws:s3:::{self.bucket_name}',
            f'arn:aws:s3:::{self.bucket_name}/*',
            f'arn:aws:s3:{self.dataset_region}:{self.dataset_account_id}:accesspoint/{self.access_point_name}',
            f'arn:aws:s3:{self.dataset_region}:{self.dataset_account_id}:accesspoint/{self.access_point_name}/*',
        ]

        share_policy_service.remove_resource_from_statement(
            target_resources=s3_target_resources,
            statement_sid=f'{IAM_S3_ACCESS_POINTS_STATEMENT_SID}S3',
            policy_document=policy_document,
        )
        if kms_key_id:
            kms_target_resources = [f'arn:aws:kms:{self.dataset_region}:{self.dataset_account_id}:key/{kms_key_id}']
            share_policy_service.remove_resource_from_statement(
                target_resources=kms_target_resources,
                statement_sid=f'{IAM_S3_ACCESS_POINTS_STATEMENT_SID}KMS',
                policy_document=policy_document,
            )
        IAM.update_managed_policy_default_version(
            self.target_account_id,
            self.target_environment.region,
            share_resource_policy_name,
            version_id,
            json.dumps(policy_document),
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
        AdminNotificationService().notify_admins_with_error_log(
            process_error='Error occurred while processing access point share request',
            process_name='s3 access point share processor',
            error_logs=[str(error)],
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
        AdminNotificationService().notify_admins_with_error_log(
            process_error='Error occurred while revoking access point share request',
            process_name='s3 access point share processor',
            error_logs=[str(error)],
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

import abc
import logging
import json
import time
from itertools import count

from dataall.core.environment.db.environment_models import Environment, EnvironmentGroup
from dataall.base.db import utils
from dataall.base.aws.sts import SessionHelper
from dataall.modules.dataset_sharing.aws.s3_client import S3ControlClient, S3Client
from dataall.modules.dataset_sharing.aws.kms_client import KmsClient
from dataall.base.aws.iam import IAM
from dataall.modules.dataset_sharing.db.share_object_models import ShareObject
from dataall.modules.dataset_sharing.services.dataset_alarm_service import DatasetAlarmService
from dataall.modules.dataset_sharing.db.share_object_repositories import ShareObjectRepository
from dataall.modules.dataset_sharing.services.share_managers.share_manager_utils import ShareErrorFormatter
from dataall.modules.dataset_sharing.services.managed_share_policy_service import SharePolicyService, IAM_S3_ACCESS_POINTS_STATEMENT_SID, EMPTY_STATEMENT_SID

from dataall.modules.datasets_base.db.dataset_models import DatasetStorageLocation, Dataset

logger = logging.getLogger(__name__)
ACCESS_POINT_CREATION_TIME = 30
ACCESS_POINT_CREATION_RETRIES = 5
DATAALL_ALLOW_OWNER_SID = "AllowAllToAdmin"
DATAALL_ACCESS_POINT_KMS_DECRYPT_SID = "DataAll-Access-Point-KMS-Decrypt"
DATAALL_KMS_PIVOT_ROLE_PERMISSIONS_SID = "KMSPivotRolePermissions"
DATAALL_DELEGATE_TO_ACCESS_POINT = "DelegateAccessToAccessPoint"


class S3AccessPointShareManager:
    def __init__(
        self,
        session,
        dataset: Dataset,
        share: ShareObject,
        target_folder: DatasetStorageLocation,
        source_environment: Environment,
        target_environment: Environment,
        source_env_group: EnvironmentGroup,
        env_group: EnvironmentGroup,
    ):
        self.session = session
        self.source_env_group = source_env_group
        self.env_group = env_group
        self.dataset = dataset
        self.share = share
        self.target_folder = target_folder
        self.source_environment = source_environment
        self.target_environment = target_environment
        self.share_item = ShareObjectRepository.find_sharable_item(
            session,
            share.shareUri,
            target_folder.locationUri,
        )
        self.access_point_name = self.share_item.S3AccessPointName

        self.source_account_id = dataset.AwsAccountId
        self.target_account_id = target_environment.AwsAccountId
        self.source_env_admin = source_env_group.environmentIAMRoleArn
        self.target_requester_IAMRoleName = share.principalIAMRoleName
        self.bucket_name = target_folder.S3BucketName
        self.dataset_admin = dataset.IAMDatasetAdminRoleArn
        self.dataset_account_id = dataset.AwsAccountId
        self.dataset_region = dataset.region
        self.s3_prefix = target_folder.S3Prefix
        self.folder_errors = []

    @abc.abstractmethod
    def process_approved_shares(self, *kwargs) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def process_revoked_shares(self, *kwargs) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def verify_shares(self, *kwargs) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def clean_up_share(self, *kwargs):
        raise NotImplementedError

    @staticmethod
    def build_access_point_name(share):
        S3AccessPointName = utils.slugify(
            share.datasetUri + "-" + share.principalId,
            max_length=50,
            lowercase=True,
            regex_pattern="[^a-zA-Z0-9-]",
            separator="-",
        )
        logger.info(f"S3AccessPointName={S3AccessPointName}")
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
            statements = {item.get("Sid", next(counter)): item for item in bucket_policy.get("Statement", {})}

            if DATAALL_DELEGATE_TO_ACCESS_POINT not in statements.keys():
                error = True
        if error:
            self.folder_errors.append(
                ShareErrorFormatter.dne_error_msg(
                    f"Bucket Policy {DATAALL_DELEGATE_TO_ACCESS_POINT}", f"{self.bucket_name}"
                )
            )

    def manage_bucket_policy(self):
        """
        This function will manage bucket policy by grant admin access to dataset admin, pivot role
        and environment admin. All of the policies will only be added once.
        :return:
        """
        logger.info(f"Manage Bucket policy for {self.bucket_name}")

        s3_client = S3Client(self.source_account_id, self.source_environment.region)
        bucket_policy = json.loads(s3_client.get_bucket_policy(self.bucket_name))
        for statement in bucket_policy["Statement"]:
            if statement.get("Sid") in [DATAALL_DELEGATE_TO_ACCESS_POINT]:
                return
        exceptions_roleId = [
            f"{item}:*"
            for item in SessionHelper.get_role_ids(
                self.source_account_id,
                [
                    self.dataset_admin,
                    self.source_env_admin,
                    SessionHelper.get_delegation_role_arn(self.source_account_id),
                ],
            )
        ]
        allow_owner_access = {
            "Sid": DATAALL_ALLOW_OWNER_SID,
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:*",
            "Resource": [f"arn:aws:s3:::{self.bucket_name}", f"arn:aws:s3:::{self.bucket_name}/*"],
            "Condition": {"StringLike": {"aws:userId": exceptions_roleId}},
        }
        delegated_to_accesspoint = {
            "Sid": DATAALL_DELEGATE_TO_ACCESS_POINT,
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:*",
            "Resource": [f"arn:aws:s3:::{self.bucket_name}", f"arn:aws:s3:::{self.bucket_name}/*"],
            "Condition": {"StringEquals": {"s3:DataAccessPointAccount": f"{self.source_account_id}"}},
        }
        bucket_policy["Statement"].append(allow_owner_access)
        bucket_policy["Statement"].append(delegated_to_accesspoint)
        s3_client = S3Client(self.source_account_id, self.source_environment.region)
        s3_client.create_bucket_policy(self.bucket_name, json.dumps(bucket_policy))

    def check_target_role_access_policy(self) -> None:
        """
        Checks if requester IAM role policy includes requested S3 bucket and access point
        and add to folder errors if check fails
        :return: None
        """
        # TODO: review after merge
        key_alias = f"alias/{self.dataset.KmsAlias}"
        kms_client = KmsClient(self.dataset_account_id, self.source_environment.region)
        kms_key_id = kms_client.get_key_id(key_alias)
        existing_policy = IAM.get_role_policy(
            self.target_account_id,
            self.target_requester_IAMRoleName,
            IAM_ACCESS_POINT_ROLE_POLICY,
        )
        if not existing_policy:
            self.folder_errors.append(
                ShareErrorFormatter.dne_error_msg(IAM_ACCESS_POINT_ROLE_POLICY, self.target_requester_IAMRoleName)
            )
            return

        share_manager = ShareManagerUtils(
            self.session,
            self.dataset,
            self.share,
            self.source_environment,
            self.target_environment,
            self.source_env_group,
            self.env_group,
        )

        s3_target_resources = [
            f"arn:aws:s3:::{self.bucket_name}",
            f"arn:aws:s3:::{self.bucket_name}/*",
            f"arn:aws:s3:{self.dataset_region}:{self.dataset_account_id}:accesspoint/{self.access_point_name}",
            f"arn:aws:s3:{self.dataset_region}:{self.dataset_account_id}:accesspoint/{self.access_point_name}/*",
        ]
        if not share_manager.check_resource_in_policy_statement(s3_target_resources, existing_policy["Statement"][0]):
            self.folder_errors.append(
                ShareErrorFormatter.missing_permission_error_msg(
                    self.target_requester_IAMRoleName,
                    "IAM Policy",
                    IAM_ACCESS_POINT_ROLE_POLICY,
                    "S3 Bucket",
                    f"{self.bucket_name}",
                )
            )

        if kms_key_id:
            kms_error = False
            kms_target_resources = [f"arn:aws:kms:{self.dataset_region}:{self.dataset_account_id}:key/{kms_key_id}"]
            if len(existing_policy["Statement"]) <= 1:
                kms_error = True
            elif not share_manager.check_resource_in_policy_statement(
                kms_target_resources,
                existing_policy["Statement"][1],
            ):
                kms_error = True

            if kms_error:
                self.folder_errors.append(
                    ShareErrorFormatter.missing_permission_error_msg(
                        self.target_requester_IAMRoleName,
                        "IAM Policy",
                        IAM_ACCESS_POINT_ROLE_POLICY,
                        "KMS Key",
                        f"{kms_key_id}",
                    )
                )

    def grant_target_role_access_policy(self):
        """
        Updates requester IAM role policy to include requested S3 bucket and access point
        :return:
        """
        logger.info(
            f'Grant target role {self.target_requester_IAMRoleName} access policy'
        )

        share_policy_service = SharePolicyService(
            environmentUri=self.target_environment.environmentUri,
            account=self.target_environment.AwsAccountId,
            role_name=self.target_requester_IAMRoleName,
            resource_prefix=self.target_environment.resourcePrefix
        )

        # Backwards compatibility
        # we check if a managed share policy exists. If False, the role was introduced to data.all before this update
        # We create the policy from the inline statements and attach it to the role
        if not share_policy_service.check_if_policy_exists():
            share_policy_service.create_managed_policy_from_inline_and_delete_inline()
            share_policy_service.attach_policy()
        # End of backwards compatibility

        share_resource_policy_name = share_policy_service.generate_policy_name()
        version_id, policy_document = IAM.get_managed_policy_default_version(
            self.target_account_id,
            share_resource_policy_name
        )

        key_alias = f"alias/{self.dataset.KmsAlias}"
        kms_client = KmsClient(self.dataset_account_id, self.source_environment.region)
        kms_key_id = kms_client.get_key_id(key_alias)

        s3_target_resources = [
            f"arn:aws:s3:::{self.bucket_name}",
            f"arn:aws:s3:::{self.bucket_name}/*",
            f"arn:aws:s3:{self.dataset_region}:{self.dataset_account_id}:accesspoint/{self.access_point_name}",
            f"arn:aws:s3:{self.dataset_region}:{self.dataset_account_id}:accesspoint/{self.access_point_name}/*"
        ]

        share_policy_service.add_missing_resources_to_policy_statement(
            resource_type="s3",
            target_resources=s3_target_resources,
            statement_sid=f"{IAM_S3_ACCESS_POINTS_STATEMENT_SID}S3",
            policy_document=policy_document
        )

        share_policy_service.remove_empty_statement(
            policy_doc=policy_document,
            statement_sid=EMPTY_STATEMENT_SID
        )

        if kms_key_id:
            kms_target_resources = [
                f"arn:aws:kms:{self.dataset_region}:{self.dataset_account_id}:key/{kms_key_id}"
            ]
            share_policy_service.add_missing_resources_to_policy_statement(
                resource_type="kms",
                target_resources=kms_target_resources,
                statement_sid=f"{IAM_S3_ACCESS_POINTS_STATEMENT_SID}KMS",
                policy_document=policy_document,
            )

        IAM.update_managed_policy_default_version(
            self.target_account_id,
            share_resource_policy_name,
            version_id,
            json.dumps(policy_document)
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
            self.folder_errors.append(ShareErrorFormatter.dne_error_msg("Access Point", self.access_point_name))
            return

        existing_policy = s3_client.get_access_point_policy(self.access_point_name)
        if not existing_policy:
            self.folder_errors.append(
                ShareErrorFormatter.dne_error_msg("Access Point Policy", self.access_point_name)
            )
            return

        existing_policy = json.loads(existing_policy)
        statements = {item["Sid"]: item for item in existing_policy["Statement"]}
        target_requester_id = SessionHelper.get_role_id(self.target_account_id, self.target_requester_IAMRoleName)
        error = False
        if f"{target_requester_id}0" not in statements.keys():
            error = True
        else:
            prefix_list = statements[f"{target_requester_id}0"].get("Condition", {}).get("StringLike", {}).get("s3:prefix", [])
            if isinstance(prefix_list, str):
                prefix_list = [prefix_list]
            if f"{self.s3_prefix}/*" not in prefix_list:
                error = True
        if error:
            self.folder_errors.append(
                ShareErrorFormatter.missing_permission_error_msg(
                    self.target_requester_IAMRoleName,
                    "Policy",
                    f"{target_requester_id}0",
                    "Access Point",
                    self.access_point_name,
                )
            )

        error1 = False
        if f"{target_requester_id}1" not in statements.keys():
            error1 = True
        else:
            resource_list = statements[f"{target_requester_id}1"].get("Resource", [])
            if isinstance(resource_list, str):
                resource_list = [resource_list]
            if f"{access_point_arn}/object/{self.s3_prefix}/*" not in resource_list:
                error1 = True
        if error1:
            self.folder_errors.append(
                ShareErrorFormatter.missing_permission_error_msg(
                    self.target_requester_IAMRoleName,
                    "Policy",
                    f"{target_requester_id}1",
                    "Access Point",
                    self.access_point_name,
                )
            )

    def manage_access_point_and_policy(self):
        """
        :return:
        """

        s3_client = S3ControlClient(self.source_account_id, self.source_environment.region)
        access_point_arn = s3_client.get_bucket_access_point_arn(self.access_point_name)
        if not access_point_arn:
            logger.info(f"Access point {self.access_point_name} does not exists, creating...")
            access_point_arn = s3_client.create_bucket_access_point(self.bucket_name, self.access_point_name)
            # Access point creation is slow
            retries = 1
            while (
                not s3_client.get_bucket_access_point_arn(self.access_point_name)
                and retries < ACCESS_POINT_CREATION_RETRIES
            ):
                logger.info("Waiting 30s for access point creation to complete..")
                time.sleep(ACCESS_POINT_CREATION_TIME)
                retries += 1
        existing_policy = s3_client.get_access_point_policy(self.access_point_name)
        # requester will use this role to access resources
        target_requester_id = SessionHelper.get_role_id(self.target_account_id, self.target_requester_IAMRoleName)
        if existing_policy:
            # Update existing access point policy
            logger.info(
                f"There is already an existing access point {access_point_arn} with an existing policy, updating policy..."
            )
            existing_policy = json.loads(existing_policy)
            statements = {item["Sid"]: item for item in existing_policy["Statement"]}
            if f"{target_requester_id}0" in statements.keys():
                prefix_list = statements[f"{target_requester_id}0"]["Condition"]["StringLike"]["s3:prefix"]
                if isinstance(prefix_list, str):
                    prefix_list = [prefix_list]
                if f"{self.s3_prefix}/*" not in prefix_list:
                    prefix_list.append(f"{self.s3_prefix}/*")
                    statements[f"{target_requester_id}0"]["Condition"]["StringLike"]["s3:prefix"] = prefix_list
                resource_list = statements[f"{target_requester_id}1"]["Resource"]
                if isinstance(resource_list, str):
                    resource_list = [resource_list]
                if f"{access_point_arn}/object/{self.s3_prefix}/*" not in resource_list:
                    resource_list.append(f"{access_point_arn}/object/{self.s3_prefix}/*")
                    statements[f"{target_requester_id}1"]["Resource"] = resource_list
                existing_policy["Statement"] = list(statements.values())
            else:
                additional_policy = S3ControlClient.generate_access_point_policy_template(
                    target_requester_id,
                    access_point_arn,
                    self.s3_prefix,
                )
                existing_policy["Statement"].extend(additional_policy["Statement"])
            access_point_policy = existing_policy
        else:
            # First time to create access point policy
            logger.info(f"Access point policy for access point {access_point_arn} does not exists, creating policy...")
            access_point_policy = S3ControlClient.generate_access_point_policy_template(
                target_requester_id,
                access_point_arn,
                self.s3_prefix,
            )
            exceptions_roleId = [
                f"{item}:*"
                for item in SessionHelper.get_role_ids(
                    self.source_account_id,
                    [
                        self.dataset_admin,
                        self.source_env_admin,
                        SessionHelper.get_delegation_role_arn(self.source_account_id),
                    ],
                )
            ]
            admin_statement = {
                "Sid": DATAALL_ALLOW_OWNER_SID,
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:*",
                "Resource": f"{access_point_arn}",
                "Condition": {"StringLike": {"aws:userId": exceptions_roleId}},
            }
            access_point_policy["Statement"].append(admin_statement)
        s3_client.attach_access_point_policy(
            access_point_name=self.access_point_name, policy=json.dumps(access_point_policy)
        )

    def check_dataset_bucket_key_policy(self) -> None:
        """
        Checks if dataset kms key policy includes read permissions for requestors IAM Role
        and add to folder errors if check fails
        :return: None
        """
        key_alias = f"alias/{self.dataset.KmsAlias}"
        kms_client = KmsClient(self.source_account_id, self.source_environment.region)
        kms_key_id = kms_client.get_key_id(key_alias)
        existing_policy = kms_client.get_key_policy(kms_key_id)

        if not existing_policy:
            self.folder_errors.append(ShareErrorFormatter.dne_error_msg("KMS Key Policy", kms_key_id))
            return

        target_requester_arn = IAM.get_role_arn_by_name(self.target_account_id, self.target_requester_IAMRoleName)
        existing_policy = json.loads(existing_policy)
        counter = count()
        statements = {item.get("Sid", next(counter)): item for item in existing_policy.get("Statement", {})}

        error = False
        if DATAALL_ACCESS_POINT_KMS_DECRYPT_SID not in statements.keys():
            error = True
        elif f"{target_requester_arn}" not in self.get_principal_list(statements[DATAALL_ACCESS_POINT_KMS_DECRYPT_SID]):
            error = True

        if error:
            self.folder_errors.append(
                ShareErrorFormatter.missing_permission_error_msg(
                    self.target_requester_IAMRoleName,
                    "KMS Key Policy",
                    DATAALL_ACCESS_POINT_KMS_DECRYPT_SID,
                    "KMS Key",
                    f"{kms_key_id}",
                )
            )

    def update_dataset_bucket_key_policy(self):
        logger.info("Updating dataset Bucket KMS key policy...")
        key_alias = f"alias/{self.dataset.KmsAlias}"
        kms_client = KmsClient(self.source_account_id, self.source_environment.region)
        kms_key_id = kms_client.get_key_id(key_alias)
        existing_policy = kms_client.get_key_policy(kms_key_id)
        target_requester_arn = IAM.get_role_arn_by_name(self.target_account_id, self.target_requester_IAMRoleName)
        pivot_role_name = SessionHelper.get_delegation_role_name()

        if existing_policy:
            existing_policy = json.loads(existing_policy)
            counter = count()
            statements = {item.get("Sid", next(counter)): item for item in existing_policy.get("Statement", {})}

            if DATAALL_KMS_PIVOT_ROLE_PERMISSIONS_SID in statements.keys():
                logger.info(f"KMS key policy already contains share statement {DATAALL_KMS_PIVOT_ROLE_PERMISSIONS_SID}")
            else:
                logger.info(
                    f"KMS key policy does not contain statement {DATAALL_KMS_PIVOT_ROLE_PERMISSIONS_SID}, generating a new one"
                )
                statements[
                    DATAALL_KMS_PIVOT_ROLE_PERMISSIONS_SID
                ] = self.generate_enable_pivot_role_permissions_policy_statement(
                    pivot_role_name, self.dataset_account_id
                )

            if DATAALL_ACCESS_POINT_KMS_DECRYPT_SID in statements.keys():
                logger.info(
                    f"KMS key policy contains share statement {DATAALL_ACCESS_POINT_KMS_DECRYPT_SID}, "
                    f"updating the current one"
                )
                statements[DATAALL_ACCESS_POINT_KMS_DECRYPT_SID] = self.add_target_arn_to_statement_principal(
                    statements[DATAALL_ACCESS_POINT_KMS_DECRYPT_SID], target_requester_arn
                )
            else:
                logger.info(
                    f"KMS key does not contain share statement {DATAALL_ACCESS_POINT_KMS_DECRYPT_SID}, "
                    f"generating a new one"
                )
                statements[DATAALL_ACCESS_POINT_KMS_DECRYPT_SID] = self.generate_default_kms_decrypt_policy_statement(
                    target_requester_arn
                )
            existing_policy["Statement"] = list(statements.values())

        else:
            logger.info("KMS key policy does not contain any statements, generating a new one")
            existing_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    self.generate_default_kms_decrypt_policy_statement(target_requester_arn),
                    self.generate_enable_pivot_role_permissions_policy_statement(
                        pivot_role_name, self.dataset_account_id
                    ),
                ],
            }
        kms_client.put_key_policy(kms_key_id, json.dumps(existing_policy))

    def delete_access_point_policy(self):
        logger.info(f"Deleting access point policy for access point {self.access_point_name}...")
        s3_client = S3ControlClient(self.source_account_id, self.source_environment.region)
        access_point_policy = json.loads(s3_client.get_access_point_policy(self.access_point_name))
        access_point_arn = s3_client.get_bucket_access_point_arn(self.access_point_name)
        target_requester_id = SessionHelper.get_role_id(self.target_account_id, self.target_requester_IAMRoleName)
        statements = {item["Sid"]: item for item in access_point_policy["Statement"]}
        if f"{target_requester_id}0" in statements.keys():
            prefix_list = statements[f"{target_requester_id}0"]["Condition"]["StringLike"]["s3:prefix"]
            if isinstance(prefix_list, list) and f"{self.s3_prefix}/*" in prefix_list:
                prefix_list.remove(f"{self.s3_prefix}/*")
                statements[f"{target_requester_id}1"]["Resource"].remove(
                    f"{access_point_arn}/object/{self.s3_prefix}/*"
                )
                access_point_policy["Statement"] = list(statements.values())
            else:
                access_point_policy["Statement"].remove(statements[f"{target_requester_id}0"])
                access_point_policy["Statement"].remove(statements[f"{target_requester_id}1"])
        s3_client.attach_access_point_policy(
            access_point_name=self.access_point_name, policy=json.dumps(access_point_policy)
        )

    @staticmethod
    def delete_access_point(
        share: ShareObject,
        dataset: Dataset,
    ):
        access_point_name = S3AccessPointShareManager.build_access_point_name(share)
        logger.info(f"Deleting access point {access_point_name}...")

        s3_client = S3ControlClient(dataset.AwsAccountId, dataset.region)
        access_point_policy = json.loads(s3_client.get_access_point_policy(access_point_name))
        if len(access_point_policy["Statement"]) <= 1:
            # At least we have the 'AllowAllToAdmin' statement
            s3_client.delete_bucket_access_point(access_point_name)
            return True
        else:
            return False

    @staticmethod
    def delete_target_role_access_policy(
        share: ShareObject,
        dataset: Dataset,
        target_environment: Environment,
    ):
        logger.info(
            'Deleting target role IAM statements...'
        )

        share_policy_service = SharePolicyService(
            role_name=share.principalIAMRoleName,
            account=target_environment.AwsAccountId,
            environmentUri=target_environment.environmentUri,
            resource_prefix=target_environment.resourcePrefix
        )

        # Backwards compatibility
        # we check if a managed share policy exists. If False, the role was introduced to data.all before this update
        # We create the policy from the inline statements and attach it to the role
        if not share_policy_service.check_if_policy_exists():
            share_policy_service.create_managed_policy_from_inline_and_delete_inline()
            share_policy_service.attach_policy()
        # End of backwards compatibility

        share_resource_policy_name = share_policy_service.generate_policy_name()
        version_id, policy_document = IAM.get_managed_policy_default_version(
            target_environment.AwsAccountId,
            share_resource_policy_name)

        access_point_name = S3AccessPointShareManager.build_access_point_name(share)

        key_alias = f"alias/{dataset.KmsAlias}"
        kms_client = KmsClient(dataset.AwsAccountId, dataset.region)
        kms_key_id = kms_client.get_key_id(key_alias)

        s3_target_resources = [
            f"arn:aws:s3:::{dataset.S3BucketName}",
            f"arn:aws:s3:::{dataset.S3BucketName}/*",
            f"arn:aws:s3:{dataset.region}:{dataset.AwsAccountId}:accesspoint/{access_point_name}",
            f"arn:aws:s3:{dataset.region}:{dataset.AwsAccountId}:accesspoint/{access_point_name}/*"
        ]

        share_policy_service.remove_resource_from_statement(
            target_resources=s3_target_resources,
            statement_sid=f"{IAM_S3_ACCESS_POINTS_STATEMENT_SID}S3",
            policy_document=policy_document
        )
        if kms_key_id:
            kms_target_resources = [
                f"arn:aws:kms:{dataset.region}:{dataset.AwsAccountId}:key/{kms_key_id}"
            ]
            share_policy_service.remove_resource_from_statement(
                target_resources=kms_target_resources,
                statement_sid=f"{IAM_S3_ACCESS_POINTS_STATEMENT_SID}KMS",
                policy_document=policy_document
            )
        IAM.update_managed_policy_default_version(
            target_environment.AwsAccountId,
            share_resource_policy_name,
            version_id,
            json.dumps(policy_document)
        )

    def delete_dataset_bucket_key_policy(
        self,
        dataset: Dataset,
    ):
        logger.info("Deleting dataset bucket KMS key policy...")
        key_alias = f"alias/{dataset.KmsAlias}"
        kms_client = KmsClient(dataset.AwsAccountId, dataset.region)
        kms_key_id = kms_client.get_key_id(key_alias)
        existing_policy = json.loads(kms_client.get_key_policy(kms_key_id))
        target_requester_arn = IAM.get_role_arn_by_name(self.target_account_id, self.target_requester_IAMRoleName)
        counter = count()
        statements = {item.get("Sid", next(counter)): item for item in existing_policy.get("Statement", {})}
        if DATAALL_ACCESS_POINT_KMS_DECRYPT_SID in statements.keys():
            principal_list = self.get_principal_list(statements[DATAALL_ACCESS_POINT_KMS_DECRYPT_SID])
            if f"{target_requester_arn}" in principal_list:
                principal_list.remove(f"{target_requester_arn}")
                if len(principal_list) == 0:
                    statements.pop(DATAALL_ACCESS_POINT_KMS_DECRYPT_SID)
                else:
                    statements[DATAALL_ACCESS_POINT_KMS_DECRYPT_SID]["Principal"]["AWS"] = principal_list
                existing_policy["Statement"] = list(statements.values())
                kms_client.put_key_policy(kms_key_id, json.dumps(existing_policy))

    def handle_share_failure(self, error: Exception) -> None:
        """
        Handles share failure by raising an alarm to alarmsTopic
        Returns
        -------
        True if alarm published successfully
        """
        logger.error(
            f"Failed to share folder {self.s3_prefix} "
            f"from source account {self.source_environment.AwsAccountId}//{self.source_environment.region} "
            f"with target account {self.target_environment.AwsAccountId}/{self.target_environment.region} "
            f"due to: {error}"
        )
        DatasetAlarmService().trigger_folder_sharing_failure_alarm(
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
            f"Failed to revoke S3 permissions to folder {self.s3_prefix} "
            f"from source account {self.source_environment.AwsAccountId}//{self.source_environment.region} "
            f"with target account {self.target_environment.AwsAccountId}/{self.target_environment.region} "
            f"due to: {error}"
        )
        DatasetAlarmService().trigger_revoke_folder_sharing_failure_alarm(
            self.target_folder, self.share, self.target_environment
        )
        return True

    @staticmethod
    def generate_default_kms_decrypt_policy_statement(target_requester_arn):
        return {
            "Sid": f"{DATAALL_ACCESS_POINT_KMS_DECRYPT_SID}",
            "Effect": "Allow",
            "Principal": {"AWS": [f"{target_requester_arn}"]},
            "Action": "kms:Decrypt",
            "Resource": "*",
        }

    @staticmethod
    def generate_enable_pivot_role_permissions_policy_statement(pivot_role_name, dataset_account_id):
        return {
            "Sid": f"{DATAALL_KMS_PIVOT_ROLE_PERMISSIONS_SID}",
            "Effect": "Allow",
            "Principal": {"AWS": [f"arn:aws:iam::{dataset_account_id}:role/{pivot_role_name}"]},
            "Action": [
                "kms:Decrypt",
                "kms:Encrypt",
                "kms:GenerateDataKey*",
                "kms:PutKeyPolicy",
                "kms:GetKeyPolicy",
                "kms:ReEncrypt*",
                "kms:TagResource",
                "kms:UntagResource",
            ],
            "Resource": "*",
        }

    def add_target_arn_to_statement_principal(self, statement, target_requester_arn):
        principal_list = self.get_principal_list(statement)
        if f"{target_requester_arn}" not in principal_list:
            principal_list.append(f"{target_requester_arn}")
        statement["Principal"]["AWS"] = principal_list
        return statement

    @staticmethod
    def get_principal_list(statement):
        principal_list = statement["Principal"]["AWS"]
        if isinstance(principal_list, str):
            principal_list = [principal_list]
        return principal_list

import logging
from datetime import datetime
from logging import exception
from typing import List

from dataall.modules.notifications.services.admin_notifications import AdminNotificationService
from dataall.modules.shares_base.services.share_exceptions import PrincipalRoleNotFound
from dataall.modules.s3_datasets_shares.services.share_managers import S3BucketShareManager
from dataall.modules.s3_datasets_shares.services.s3_share_service import S3ShareService
from dataall.modules.shares_base.services.shares_enums import (
    ShareItemHealthStatus,
    ShareItemStatus,
    ShareObjectActions,
    ShareItemActions,
)
from dataall.modules.shares_base.db.share_object_repositories import ShareObjectRepository
from dataall.modules.shares_base.db.share_state_machines_repositories import ShareStatusRepository
from dataall.modules.s3_datasets.db.dataset_models import DatasetBucket
from dataall.modules.shares_base.db.share_object_state_machines import ShareItemSM
from dataall.modules.shares_base.services.sharing_service import ShareData
from dataall.modules.shares_base.services.share_processor_manager import SharesProcessorInterface
from dataall.modules.shares_base.services.share_object_service import ShareObjectService
from dataall.modules.shares_base.services.share_manager_utils import execute_and_suppress_exception


log = logging.getLogger(__name__)


class ProcessS3BucketShare(SharesProcessorInterface):
    def __init__(self, session, share_data, shareable_items, reapply=False):
        self.session = session
        self.share_data: ShareData = share_data
        self.buckets: List[DatasetBucket] = shareable_items
        self.reapply: bool = reapply

    def _initialize_share_manager(self, bucket):
        return S3BucketShareManager(session=self.session, share_data=self.share_data, target_bucket=bucket)

    def process_approved_shares(self) -> bool:
        """
        1) update_share_item_status with Start action
        2) manage_bucket_policy - grants permission in the bucket policy
        3) grant_target_role_access_policy == done
        4) update_dataset_bucket_key_policy == done
        5) update_share_item_status with Finish action == done

        Returns
        -------
        True if share is granted successfully
        """
        log.info('##### Starting S3 bucket share #######')
        success = True
        if not self.buckets:
            log.info('No Buckets to share. Skipping...')
            return success
        if not S3ShareService.verify_principal_role(self.session, self.share_data.share):
            raise PrincipalRoleNotFound(
                'process approved shares',
                f'Principal role {self.share_data.share.principalRoleName} is not found. Failed to update KMS key/bucket policy',
            )
        for bucket in self.buckets:
            log.info(f'Sharing bucket {bucket.bucketUri}/{bucket.S3BucketName} ')
            manager = self._initialize_share_manager(bucket)
            sharing_item = ShareObjectRepository.find_sharable_item(
                self.session,
                self.share_data.share.shareUri,
                bucket.bucketUri,
            )
            if not self.reapply:
                shared_item_SM = ShareItemSM(ShareItemStatus.Share_Approved.value)
                new_state = shared_item_SM.run_transition(ShareObjectActions.Start.value)
                shared_item_SM.update_state_single_item(self.session, sharing_item, new_state)

            try:
                manager.grant_role_bucket_policy()
                manager.grant_s3_iam_access()
                if not self.share_data.dataset.imported or self.share_data.dataset.importedKmsKey:
                    manager.grant_dataset_bucket_key_policy()
                if not self.reapply:
                    new_state = shared_item_SM.run_transition(ShareItemActions.Success.value)
                    shared_item_SM.update_state_single_item(self.session, sharing_item, new_state)
                ShareStatusRepository.update_share_item_health_status(
                    self.session, sharing_item, ShareItemHealthStatus.Healthy.value, None, datetime.now()
                )

            except Exception as e:
                # must run first to ensure state transitions to failed
                if not self.reapply:
                    new_state = shared_item_SM.run_transition(ShareItemActions.Failure.value)
                    shared_item_SM.update_state_single_item(self.session, sharing_item, new_state)
                else:
                    ShareStatusRepository.update_share_item_health_status(
                        self.session, sharing_item, ShareItemHealthStatus.Unhealthy.value, str(e), datetime.now()
                    )
                success = False
                manager.handle_share_failure(e)
        return success

    def process_revoked_shares(self) -> bool:
        """
        1) update_share_item_status with Start action
        2) remove access from bucket policy
        3) remove access from key policy
        4) remove access from IAM role policy
        5) update_share_item_status with Finish action

        Returns
        -------
        True if share is revoked successfully
        False if revoke fails
        """

        log.info('##### Starting Revoking S3 bucket share #######')
        success = True
        if not self.buckets:
            log.info('No Buckets to revoke. Skipping...')
        for bucket in self.buckets:
            log.info(f'Revoking access to bucket {bucket.bucketUri}/{bucket.S3BucketName} ')
            manager = self._initialize_share_manager(bucket)
            removing_item = ShareObjectRepository.find_sharable_item(
                self.session,
                self.share_data.share.shareUri,
                bucket.bucketUri,
            )

            revoked_item_SM = ShareItemSM(ShareItemStatus.Revoke_Approved.value)
            new_state = revoked_item_SM.run_transition(ShareObjectActions.Start.value)
            revoked_item_SM.update_state_single_item(self.session, removing_item, new_state)
            try:
                if not S3ShareService.verify_principal_role(self.session, self.share_data.share):
                    raise PrincipalRoleNotFound(
                        'process revoked shares',
                        f'Principal role {self.share_data.share.principalRoleName} is not found. Failed to update KMS key/bucket policy',
                    )
                manager.delete_target_role_bucket_policy()
                manager.delete_target_role_access_policy(
                    share=self.share_data.share,
                    target_bucket=bucket,
                    target_environment=self.share_data.target_environment,
                )
                if not self.share_data.dataset.imported or self.share_data.dataset.importedKmsKey:
                    manager.delete_target_role_bucket_key_policy(
                        target_bucket=bucket,
                    )
                new_state = revoked_item_SM.run_transition(ShareItemActions.Success.value)
                revoked_item_SM.update_state_single_item(self.session, removing_item, new_state)
                ShareStatusRepository.update_share_item_health_status(
                    self.session, removing_item, None, None, removing_item.lastVerificationTime
                )

            except Exception as e:
                # must run first to ensure state transitions to failed
                new_state = revoked_item_SM.run_transition(ShareItemActions.Failure.value)
                revoked_item_SM.update_state_single_item(self.session, removing_item, new_state)
                success = False

                # statements which can throw exceptions but are not critical
                manager.handle_revoke_failure(e)

        return success

    def verify_shares_health_status(self) -> bool:
        share_object_item_health_status = True
        log.info('##### Verifying S3 bucket share #######')
        if not self.buckets:
            log.info('No Buckets to verify. Skipping...')
        for bucket in self.buckets:
            log.info(f'Verifying access to bucket {bucket.bucketUri}/{bucket.S3BucketName} ')
            manager = self._initialize_share_manager(bucket)
            sharing_item = ShareObjectRepository.find_sharable_item(
                self.session,
                self.share_data.share.shareUri,
                bucket.bucketUri,
            )
            try:
                if not S3ShareService.verify_principal_role(self.session, self.share_data.share):
                    raise PrincipalRoleNotFound(
                        'process verify shares',
                        f'Share principal Role {self.share_data.share.principalRoleName} not found. Check the team or consumption IAM role used.',
                    )
                manager.check_role_bucket_policy()
                manager.check_s3_iam_access()

                if not self.share_data.dataset.imported or self.share_data.dataset.importedKmsKey:
                    manager.check_dataset_bucket_key_policy()
            except Exception as e:
                manager.bucket_errors = [str(e)]

            if len(manager.bucket_errors):
                ShareStatusRepository.update_share_item_health_status(
                    self.session,
                    sharing_item,
                    ShareItemHealthStatus.Unhealthy.value,
                    ' | '.join(manager.bucket_errors),
                    datetime.now(),
                )
                share_object_item_health_status = False
            else:
                ShareStatusRepository.update_share_item_health_status(
                    self.session, sharing_item, ShareItemHealthStatus.Healthy.value, None, datetime.now()
                )
        return share_object_item_health_status

    def cleanup_shares(self) -> bool:
        """
        1) try to remove access from bucket policy
        2) try to remove access from key policy
        3) try to remove access from IAM role policy
        4) delete all share items and delete share object

        Returns
        -------
        True
        """

        log.info('##### Starting Cleaning-up S3 bucket share #######')
        if not self.buckets:
            log.info('No Buckets to revoke. Skipping...')
        for bucket in self.buckets:
            log.info(f'Revoking access to bucket {bucket.bucketUri}/{bucket.S3BucketName} ')
            manager = self._initialize_share_manager(bucket)
            if not S3ShareService.verify_principal_role(self.session, self.share_data.share):
                log.info(f'Principal role {self.share_data.share.principalRoleName} is not found.')
            execute_and_suppress_exception(func=manager.delete_target_role_bucket_policy)
            execute_and_suppress_exception(
                func=manager.delete_target_role_access_policy,
                share=self.share_data.share,
                target_bucket=bucket,
                target_environment=self.share_data.target_environment,
            )
            if not self.share_data.dataset.imported or self.share_data.dataset.importedKmsKey:
                execute_and_suppress_exception(func=manager.delete_target_role_bucket_key_policy, target_bucket=bucket)

            # Delete share item
            sharing_item = ShareObjectRepository.find_sharable_item(
                self.session,
                self.share_data.share.shareUri,
                bucket.bucketUri,
            )
            self.session.delete(sharing_item)
            self.session.commit()

        # Check share items in share and delete share
        remaining_share_items = ShareObjectRepository.get_all_share_items_in_share(
            session=self.session, share_uri=self.share_data.share.shareUri
        )
        if not remaining_share_items:
            ShareObjectService.deleting_share_permissions(
                session=self.session, share=self.share_data.share, dataset=self.share_data.dataset
            )
            self.session.delete(self.share_data.share)
        return True

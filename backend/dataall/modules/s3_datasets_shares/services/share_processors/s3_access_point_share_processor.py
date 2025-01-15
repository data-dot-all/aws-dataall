import logging
from datetime import datetime
from typing import List

from dataall.modules.notifications.services.admin_notifications import AdminNotificationService
from dataall.modules.shares_base.services.share_exceptions import PrincipalRoleNotFound
from dataall.modules.s3_datasets_shares.services.share_managers import S3AccessPointShareManager
from dataall.modules.s3_datasets_shares.services.s3_share_service import S3ShareService
from dataall.modules.shares_base.services.share_object_service import ShareObjectService
from dataall.modules.shares_base.services.shares_enums import (
    ShareItemHealthStatus,
    ShareItemStatus,
    ShareObjectActions,
    ShareItemActions,
)
from dataall.modules.s3_datasets.db.dataset_models import DatasetStorageLocation
from dataall.modules.shares_base.db.share_object_repositories import ShareObjectRepository
from dataall.modules.shares_base.db.share_state_machines_repositories import ShareStatusRepository
from dataall.modules.shares_base.db.share_object_state_machines import ShareItemSM
from dataall.modules.shares_base.services.sharing_service import ShareData
from dataall.modules.shares_base.services.share_processor_manager import SharesProcessorInterface
from dataall.modules.shares_base.services.share_manager_utils import execute_and_suppress_exception


log = logging.getLogger(__name__)


class ProcessS3AccessPointShare(SharesProcessorInterface):
    def __init__(self, session, share_data, shareable_items, reapply=False):
        self.session = session
        self.share_data: ShareData = share_data
        self.folders: List[DatasetStorageLocation] = shareable_items
        self.reapply: bool = reapply

    def _initialize_share_manager(self, folder):
        return S3AccessPointShareManager(session=self.session, share_data=self.share_data, target_folder=folder)

    def process_approved_shares(self) -> bool:
        """
        1) update_share_item_status with Start action
        2) (one time only) manage_bucket_policy - grants permission in the bucket policy
        3) grant_target_role_access_policy
        4) manage_access_point_and_policy
        5) update_dataset_bucket_key_policy
        6) update_share_item_status with Finish action

        Returns
        -------
        True if share is granted successfully
        """
        log.info('##### Starting Sharing folders #######')
        success = True
        if not self.folders:
            log.info('No Folders to share. Skipping...')
        for folder in self.folders:
            log.info(f'Sharing folder {folder.locationUri}/{folder.name}')
            manager = self._initialize_share_manager(folder)
            sharing_item = ShareObjectRepository.find_sharable_item(
                self.session,
                self.share_data.share.shareUri,
                folder.locationUri,
            )
            if not self.reapply:
                shared_item_SM = ShareItemSM(ShareItemStatus.Share_Approved.value)
                new_state = shared_item_SM.run_transition(ShareObjectActions.Start.value)
                shared_item_SM.update_state_single_item(self.session, sharing_item, new_state)
            try:
                if not S3ShareService.verify_principal_role(self.session, self.share_data.share):
                    raise PrincipalRoleNotFound(
                        'process approved shares',
                        f'Principal role {self.share_data.share.principalRoleName} is not found. Failed to update bucket policy',
                    )

                manager.manage_bucket_policy()
                manager.grant_target_role_access_policy()
                manager.manage_access_point_and_policy()
                if not self.share_data.dataset.imported or self.share_data.dataset.importedKmsKey:
                    manager.update_dataset_bucket_key_policy()

                log.info('Attaching FOLDER READ permissions...')
                S3ShareService.attach_dataset_folder_read_permission(
                    self.session, self.share_data.share, folder.locationUri
                )

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
        2) delete_access_point_policy for folder
        3) update_share_item_status with Finish action

        Returns
        -------
        True if share is revoked successfully
        """

        log.info('##### Starting Revoking folders #######')
        success = True
        if not self.folders:
            log.info('No Folders to revoke. Skipping...')
        for folder in self.folders:
            log.info(f'Revoking access to folder {folder.locationUri}/{folder.name}')
            manager = self._initialize_share_manager(folder)
            removing_item = ShareObjectRepository.find_sharable_item(
                self.session,
                self.share_data.share.shareUri,
                folder.locationUri,
            )

            revoked_item_SM = ShareItemSM(ShareItemStatus.Revoke_Approved.value)
            new_state = revoked_item_SM.run_transition(ShareObjectActions.Start.value)
            revoked_item_SM.update_state_single_item(self.session, removing_item, new_state)

            try:
                if not S3ShareService.verify_principal_role(self.session, self.share_data.share):
                    raise PrincipalRoleNotFound(
                        'process approved shares',
                        f'Principal role {self.share_data.share.principalRoleName} is not found. Failed to update bucket policy',
                    )
                access_point_policy = manager.revoke_access_in_access_point_policy()

                if len(access_point_policy['Statement']) > 0:
                    manager.attach_new_access_point_policy(access_point_policy)
                else:
                    log.info('Cleaning up folder share resources...')
                    manager.delete_access_point()
                    manager.revoke_target_role_access_policy()
                    if not self.share_data.dataset.imported or self.share_data.dataset.importedKmsKey:
                        manager.delete_dataset_bucket_key_policy(dataset=self.share_data.dataset)

                if (
                    self.share_data.share.groupUri != self.share_data.dataset.SamlAdminGroupName
                    and self.share_data.share.groupUri != self.share_data.dataset.stewards
                ):
                    log.info(f'Deleting FOLDER READ permissions from {folder.locationUri}...')
                    S3ShareService.delete_dataset_folder_read_permission(
                        self.session, manager.share, folder.locationUri
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
        log.info('##### Verifying folders shares #######')
        if not self.folders:
            log.info('No Folders to verify. Skipping...')
        for folder in self.folders:
            log.info(f'Verifying access to folder {folder.locationUri}/{folder.name}')
            manager = self._initialize_share_manager(folder)
            sharing_item = ShareObjectRepository.find_sharable_item(
                self.session,
                self.share_data.share.shareUri,
                folder.locationUri,
            )

            try:
                if not S3ShareService.verify_principal_role(self.session, self.share_data.share):
                    raise PrincipalRoleNotFound(
                        'process verify shares',
                        f'Share principal Role {self.share_data.share.principalRoleName} not found. Check the team or consumption IAM role used.',
                    )
                manager.check_bucket_policy()
                manager.check_target_role_access_policy()
                manager.check_access_point_and_policy()

                if not self.share_data.dataset.imported or self.share_data.dataset.importedKmsKey:
                    manager.check_dataset_bucket_key_policy()
            except Exception as e:
                manager.folder_errors = [str(e)]

            if len(manager.folder_errors):
                ShareStatusRepository.update_share_item_health_status(
                    self.session,
                    sharing_item,
                    ShareItemHealthStatus.Unhealthy.value,
                    ' | '.join(manager.folder_errors),
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
        1) try to delete_access_point_policy for folder
        2) delete all share items and delete share object

        Returns
        -------
        True
        """

        log.info('##### Starting Cleaning-up folders #######')
        if not self.folders:
            log.info('No Folders to revoke. Skipping...')
        for folder in self.folders:
            log.info(f'Revoking access to folder {folder.locationUri}/{folder.name}')
            manager = self._initialize_share_manager(folder)
            if not S3ShareService.verify_principal_role(self.session, self.share_data.share):
                log.info(f'Principal role {self.share_data.share.principalRoleName} is not found.')
            try:
                access_point_policy = manager.revoke_access_in_access_point_policy()
                if len(access_point_policy['Statement']) > 0:
                    manager.attach_new_access_point_policy(access_point_policy)
                else:
                    log.info('Cleaning up folder share resources...')
                    execute_and_suppress_exception(func=manager.delete_access_point)
                    execute_and_suppress_exception(func=manager.revoke_target_role_access_policy)
                    if not self.share_data.dataset.imported or self.share_data.dataset.importedKmsKey:
                        manager.delete_dataset_bucket_key_policy(dataset=self.share_data.dataset)
            except Exception:
                log.exception('')
            if (
                self.share_data.share.groupUri != self.share_data.dataset.SamlAdminGroupName
                and self.share_data.share.groupUri != self.share_data.dataset.stewards
            ):
                log.info(f'Deleting FOLDER READ permissions from {folder.locationUri}...')
                execute_and_suppress_exception(
                    func=S3ShareService.delete_dataset_folder_read_permission,
                    session=self.session,
                    share=manager.share,
                    locationUri=folder.locationUri,
                )
            # Delete share item
            sharing_item = ShareObjectRepository.find_sharable_item(
                self.session,
                self.share_data.share.shareUri,
                folder.locationUri,
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

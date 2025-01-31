import logging
from typing import List
from warnings import warn
from datetime import datetime

from dataall.base.db.exceptions import ResourceLockTimeout
from dataall.core.environment.services.environment_service import EnvironmentService
from dataall.core.resource_lock.db.resource_lock_repositories import ResourceLockRepository
from dataall.modules.s3_datasets.db.dataset_repositories import DatasetRepository
from dataall.modules.shares_base.services.shares_enums import (
    ShareItemHealthStatus,
    ShareItemStatus,
    ShareObjectActions,
    ShareItemActions,
    ShareableType,
)
from dataall.modules.s3_datasets.db.dataset_models import DatasetTable, S3Dataset
from dataall.modules.shares_base.db.share_object_models import ShareObjectItemDataFilter
from dataall.modules.shares_base.services.share_exceptions import PrincipalRoleNotFound
from dataall.modules.s3_datasets_shares.services.share_managers import LFShareManager
from dataall.modules.s3_datasets_shares.aws.ram_client import RamClient
from dataall.modules.s3_datasets_shares.services.s3_share_service import S3ShareService
from dataall.modules.shares_base.db.share_object_repositories import ShareObjectRepository
from dataall.modules.shares_base.db.share_object_item_repositories import ShareObjectItemRepository
from dataall.modules.shares_base.db.share_state_machines_repositories import ShareStatusRepository
from dataall.modules.s3_datasets_shares.db.s3_share_object_repositories import S3ShareObjectRepository
from dataall.modules.shares_base.db.share_object_state_machines import ShareItemSM
from dataall.modules.shares_base.services.share_manager_utils import ShareErrorFormatter, execute_and_suppress_exception

from dataall.modules.shares_base.services.sharing_service import ShareData
from dataall.modules.shares_base.services.share_processor_manager import SharesProcessorInterface
from dataall.modules.shares_base.services.share_object_service import ShareObjectService

log = logging.getLogger(__name__)


class ProcessLakeFormationShare(SharesProcessorInterface):
    def __init__(self, session, share_data, shareable_items, reapply=False):
        self.session = session
        self.share_data: ShareData = share_data
        self.tables: List[DatasetTable] = shareable_items
        self.reapply: bool = reapply

    def _initialize_share_manager(self, tables):
        return LFShareManager(session=self.session, share_data=self.share_data, tables=tables)

    def _build_resource_link_name(self, table_name: str, share_item_filter: ShareObjectItemDataFilter):
        if share_item_filter:
            return f'{table_name}_{share_item_filter.label}'
        return table_name

    def process_approved_shares(self) -> bool:
        """
        0) Check if source account details are properly initialized and initialize the Glue and LF clients
        1) Grant ALL permissions to pivotRole for source database in source account
        2) Create the shared database in target account if it doesn't exist
        3) Grant permissions to pivotRole and principals to "shared" database
        4) For each shared table:
            a) Update its status to SHARE_IN_PROGRESS with Action Start
            b) Check if table exists on glue catalog raise error if not and flag share item status to failed
            c) If it is a cross-account share:
                c.1) Revoke iamallowedgroups permissions from table
                c.2) Upgrade LF Data Catalog Settings to Version 3 (if not already >=3)
            d) Grant Permissions  to target principals -> create RAM invitation
                d.1) (If cross-account) And Accept pending RAM invitation
            e) Create resource link for table in target account
            f) grant permission to principals to resource link table
            g) update share item status to SHARE_SUCCESSFUL with Action Success

        Returns
        -------
        True if share is granted successfully
        False if share fails
        """
        log.info('##### Starting Sharing tables #######')
        success = True
        if not self.tables:
            log.info('No tables to share. Skipping...')
        else:
            manager = self._initialize_share_manager(self.tables)
            try:
                if not S3ShareService.verify_principal_role(self.session, self.share_data.share):
                    raise PrincipalRoleNotFound(
                        'process approved shares',
                        f'Principal role {self.share_data.share.principalRoleName} is not found. Failed to update LF policy',
                    )

                if None in [
                    manager.source_account_id,
                    manager.source_account_region,
                    manager.source_database_name,
                ]:
                    raise Exception(
                        'Source account details not initialized properly. Please check if the catalog account is properly onboarded on data.all'
                    )
                env = EnvironmentService.get_environment_by_uri(self.session, self.share_data.share.environmentUri)
                manager.initialize_clients()
                manager.grant_pivot_role_all_database_permissions_to_source_database()
                manager.check_if_exists_and_create_shared_database_in_target()
                manager.grant_pivot_role_all_database_permissions_to_shared_database()
                manager.grant_principals_database_permissions_to_shared_database()
            except Exception as e:
                log.error(f'Failed to process approved tables due to {e}')
                manager.handle_share_failure_for_all_tables(
                    tables=self.tables,
                    error=e,
                    share_item_status=ShareItemStatus.Share_Approved.value,
                    reapply=self.reapply,
                )
                return False

            for table in self.tables:
                log.info(f'Sharing table {table.tableUri}/{table.GlueTableName}...')

                share_item = ShareObjectRepository.find_sharable_item(
                    self.session, self.share_data.share.shareUri, table.tableUri
                )

                if not share_item:
                    log.info(
                        f'Share Item not found for {self.share_data.share.shareUri} '
                        f'and Dataset Table {table.GlueTableName} continuing loop...'
                    )
                    continue
                if not self.reapply:
                    shared_item_SM = ShareItemSM(ShareItemStatus.Share_Approved.value)
                    new_state = shared_item_SM.run_transition(ShareObjectActions.Start.value)
                    shared_item_SM.update_state_single_item(self.session, share_item, new_state)

                try:
                    if self.reapply:
                        # CHECK IF SHARING WITH ACCOUNT AND CLEAN UP
                        warn(
                            'Clean up of non-direct IAM Principal shares will be deprecated in version >= v2.9.0',
                            DeprecationWarning,
                            stacklevel=2,
                        )
                        # Revoke Target Account Permissions To Table
                        try:
                            log.info('Check & clean up of delegated LF Permission to Target Account...')
                            manager._clean_up_lf_permissions_account_delegation_pattern(table)
                        except Exception as e:
                            log.info(f'Clean Up ran into error {e}, continuing re-apply without clean up...')

                    share_item_filter = None
                    if share_item.attachedDataFilterUri:
                        share_item_filter = ShareObjectItemRepository.get_share_item_filter_by_uri(
                            self.session, share_item.attachedDataFilterUri
                        )

                    manager.check_table_exists_in_source_database(share_item, table)

                    if manager.cross_account:
                        log.info(f'Processing cross-account permissions for table {table.GlueTableName}...')
                        manager.revoke_iam_allowed_principals_from_table(table)
                        manager.upgrade_lakeformation_settings_in_source()

                    manager.grant_principals_permissions_to_source_table(table, share_item, share_item_filter)
                    if manager.cross_account:
                        retries = 0
                        retry_share_table = True
                        while retry_share_table and retries < 1:
                            (
                                retry_share_table,
                                failed_invitations,
                            ) = RamClient.accept_ram_invitation(
                                source_account_id=manager.source_account_id,
                                source_region=manager.source_account_region,
                                source_database=manager.source_database_name,
                                source_table_name=table.GlueTableName,
                                target_account_id=self.share_data.target_environment.AwsAccountId,
                                target_region=self.share_data.target_environment.region,
                            )

                    resource_link_name = self._build_resource_link_name(table.GlueTableName, share_item_filter)
                    manager.check_if_exists_and_create_resource_link_table_in_shared_database(table, resource_link_name)
                    manager.grant_principals_permissions_to_resource_link_table(resource_link_name)

                    log.info('Attaching TABLE READ permissions...')
                    S3ShareService.attach_dataset_table_read_permission(
                        self.session, self.share_data.share, table.tableUri
                    )

                    if not self.reapply:
                        new_state = shared_item_SM.run_transition(ShareItemActions.Success.value)
                        shared_item_SM.update_state_single_item(self.session, share_item, new_state)
                    ShareStatusRepository.update_share_item_health_status(
                        self.session, share_item, ShareItemHealthStatus.Healthy.value, None, datetime.now()
                    )
                except Exception as e:
                    if not self.reapply:
                        new_state = shared_item_SM.run_transition(ShareItemActions.Failure.value)
                        shared_item_SM.update_state_single_item(self.session, share_item, new_state)
                    else:
                        ShareStatusRepository.update_share_item_health_status(
                            self.session,
                            share_item,
                            ShareItemHealthStatus.Unhealthy.value,
                            str(e),
                            datetime.now(),
                        )
                    success = False
                    manager.handle_share_failure(table=table, error=e)
        return success

    def process_revoked_shares(self) -> bool:
        """
        0) Check if source account details are properly initialized and initialize the Glue and LF clients
        1) Grant Pivot Role all database permissions to the shared database
        2) For each revoked table:
            a) Update its status to REVOKE_IN_PROGRESS with Action Start
            b) Check if table exists on glue catalog raise error if not and flag share item status to failed
            c) Check if resource link table exists in target account
            d) Check if the table is shared in other share requests to this target account
            e) If c is True (resource link table exists), revoke permission to principals to resource link table
            f) If c is True (resource link table exists), revoke permission to principals to table (and for QS Group if no other shares present for table)
            g) If c is True and (old-share or (new-share and d is True, no other shares of this table)) then delete resource link table
            g) If d is True (no other shares of this table with target), revoke permissions to target account to the original table
            h) update share item status to REVOKE_SUCCESSFUL with Action Success
        3) Check if there are existing_shared_tables for this dataset with target environment
        4) If no existing_shared_tables, delete shared database

        Returns
        -------
        True if share is revoked successfully
        False if revoke fails
        """
        # Find out all the datasets where the same db is used and lock all those datasets
        # With this any possible override from other share will be avoided. See the https://github.com/data-dot-all/dataall/issues/1633 for more details on this.
        s3_dataset: S3Dataset = DatasetRepository.get_dataset_by_uri(
            session=self.session, dataset_uri=self.share_data.dataset.datasetUri
        )

        s3_datasets_with_common_db: List[S3Dataset] = DatasetRepository.list_all_active_datasets_with_glue_db(
            session=self.session, glue_db_name=s3_dataset.GlueDatabaseName
        )

        log.info(f'Found {len(s3_datasets_with_common_db)} datasets where same glue database is used')
        additional_resources_to_lock = [
            (s3_dataset.datasetUri, S3Dataset.__tablename__)
            for s3_dataset in s3_datasets_with_common_db
            if s3_dataset.datasetUri != self.share_data.dataset.datasetUri
        ]
        log.info(f'Additional Resources to be locked while revoking glue tables: {additional_resources_to_lock}')

        try:
            with ResourceLockRepository.acquire_lock_with_retry(
                resources=additional_resources_to_lock,
                session=self.session,
                acquired_by_uri=self.share_data.share.shareUri,
                acquired_by_type=self.share_data.share.__tablename__,
            ):
                log.info('##### Starting Revoking tables #######')
                success = True
                manager = self._initialize_share_manager(self.tables)
                if not self.tables:
                    log.info('No tables to revoke. Skipping...')
                else:
                    try:
                        if not S3ShareService.verify_principal_role(self.session, self.share_data.share):
                            raise PrincipalRoleNotFound(
                                'process revoked shares',
                                f'Principal role {self.share_data.share.principalRoleName} is not found. Failed to update LF policy',
                            )
                        if None in [
                            manager.source_account_id,
                            manager.source_account_region,
                            manager.source_database_name,
                        ]:
                            raise Exception(
                                'Source account details not initialized properly. Please check if the catalog account is properly onboarded on data.all'
                            )
                        manager.initialize_clients()
                        manager.grant_pivot_role_all_database_permissions_to_shared_database()
                    except Exception as e:
                        log.error(f'Failed to process revoked tables due to {e}')
                        manager.handle_share_failure_for_all_tables(
                            tables=self.tables, error=e, share_item_status=ShareItemStatus.Revoke_Approved.value
                        )
                        return False

                    for table in self.tables:
                        log.info(f'Revoking access to table {table.tableUri}/{table.GlueTableName}...')
                        share_item = ShareObjectRepository.find_sharable_item(
                            self.session, self.share_data.share.shareUri, table.tableUri
                        )
                        share_item_filter = None
                        if share_item.attachedDataFilterUri:
                            share_item_filter = ShareObjectItemRepository.get_share_item_filter_by_uri(
                                self.session, share_item.attachedDataFilterUri
                            )

                        revoked_item_SM = ShareItemSM(ShareItemStatus.Revoke_Approved.value)
                        new_state = revoked_item_SM.run_transition(ShareObjectActions.Start.value)
                        revoked_item_SM.update_state_single_item(self.session, share_item, new_state)

                        try:
                            log.info(f'Revoking access to table: {table.GlueTableName} ')
                            manager.check_table_exists_in_source_database(share_item, table)

                            log.info('Check resource link table exists')
                            resource_link_name = self._build_resource_link_name(table.GlueTableName, share_item_filter)

                            resource_link_table_exists = manager.check_resource_link_table_exists_in_target_database(
                                resource_link_name
                            )

                            if resource_link_table_exists:
                                log.info('Revoking principal permissions from resource link table')
                                manager.revoke_principals_permissions_to_resource_link_table(resource_link_name)
                                log.info('Revoking principal permissions from table in source')
                                manager.revoke_principals_permissions_to_table_in_source(
                                    table, share_item, share_item_filter
                                )
                                if share_item_filter:
                                    can_delete_resource_link = True
                                else:
                                    can_delete_resource_link = (
                                        False
                                        if S3ShareObjectRepository.check_other_approved_share_item_table_exists(
                                            self.session,
                                            self.share_data.target_environment.environmentUri,
                                            share_item.itemUri,
                                            share_item.shareItemUri,
                                        )
                                        else True
                                    )

                                if can_delete_resource_link:
                                    manager.grant_pivot_role_drop_permissions_to_resource_link_table(resource_link_name)
                                    manager.delete_resource_link_table_in_shared_database(resource_link_name)

                            if (
                                self.share_data.share.groupUri != self.share_data.dataset.SamlAdminGroupName
                                and self.share_data.share.groupUri != self.share_data.dataset.stewards
                            ):
                                log.info('Deleting TABLE READ permissions...')
                                S3ShareService.delete_dataset_table_read_permission(
                                    self.session, self.share_data.share, table.tableUri
                                )

                            new_state = revoked_item_SM.run_transition(ShareItemActions.Success.value)
                            revoked_item_SM.update_state_single_item(self.session, share_item, new_state)

                            ShareStatusRepository.update_share_item_health_status(
                                self.session, share_item, None, None, share_item.lastVerificationTime
                            )

                        except Exception as e:
                            new_state = revoked_item_SM.run_transition(ShareItemActions.Failure.value)
                            revoked_item_SM.update_state_single_item(self.session, share_item, new_state)
                            success = False

                            manager.handle_revoke_failure(table=table, error=e)

                    try:
                        if self.tables:
                            s3_dataset = DatasetRepository.get_dataset_by_uri(
                                session=self.session, dataset_uri=self.share_data.dataset.datasetUri
                            )

                            # Find any share items which exist between the principal and the dataset db.
                            # Please note - a single db can be used across various dataset. This not only finds share items related to the current share under process but also any other share where the gluedb and the principal is used.
                            existing_shared_tables_in_shares = (
                                S3ShareObjectRepository.check_existing_shares_on_items_for_principal(
                                    session=self.session,
                                    item_type=ShareableType.Table.value,
                                    principal=self.share_data.share.principalRoleName,
                                    database=s3_dataset.GlueDatabaseName,
                                )
                            )
                            log.info(
                                f'Remaining tables shared on the database: {s3_dataset.GlueDatabaseName} and principal: {self.share_data.share.principalRoleName} = {existing_shared_tables_in_shares}'
                            )

                            if not existing_shared_tables_in_shares:
                                log.info('Revoking permissions to target shared database...')
                                manager.revoke_principals_database_permissions_to_shared_database()

                            share_item_shared_states = ShareStatusRepository.get_share_item_shared_states()

                            # Find all the shares where the database name is used
                            # Please note - a single db can be used across various dataset ( and also the same db can be used in different environment ). This will fetch all the dataset shares where the glueDB name is used.
                            existing_shares_with_shared_tables_for_database = (
                                S3ShareObjectRepository.list_dataset_shares_on_database(
                                    session=self.session,
                                    dataset_uri=self.share_data.dataset.datasetUri,
                                    share_item_shared_states=share_item_shared_states,
                                    item_type=ShareableType.Table.value,
                                    database=s3_dataset.GlueDatabaseName,
                                )
                            )

                            log.info(
                                f'Existing shares with database: {s3_dataset.GlueDatabaseName} = {existing_shares_with_shared_tables_for_database}. Skipping deleting shared database'
                            )

                            if not len(existing_shares_with_shared_tables_for_database):
                                log.info('Deleting target shared database...')
                                manager.delete_shared_database_in_target()
                    except Exception as e:
                        log.error(
                            f'Failed to clean-up database permissions or delete shared database {manager.shared_db_name} '
                            f'due to: {e}'
                        )
                        success = False
                    return success

        except ResourceLockTimeout as timeout:
            log.error(
                f'Resource locking timed out while locking additional resources: {additional_resources_to_lock} for revoking glue tables: {self.tables} due to: {timeout}'
            )
            raise timeout

    def verify_shares(self) -> bool:
        log.info('##### Verifying tables #######')
        if not self.tables:
            log.info('No tables to verify. Skipping...')
        else:
            manager = self._initialize_share_manager(self.tables)
            try:
                if not S3ShareService.verify_principal_role(self.session, self.share_data.share):
                    raise PrincipalRoleNotFound(
                        'process verify shares',
                        f'Share principal Role {self.share_data.share.principalRoleName} not found. Check the team or consumption IAM role used.',
                    )
                if None in [
                    manager.source_account_id,
                    manager.source_account_region,
                    manager.source_database_name,
                ]:
                    raise Exception(
                        'Source account details not initialized properly. Please check if the catalog account is properly onboarded on data.all'
                    )
                manager.initialize_clients()
                if not manager.check_pivot_role_permissions_to_source_database():
                    manager.grant_pivot_role_all_database_permissions_to_source_database()
                shared_database_exists = manager.check_shared_database_in_target()
                if shared_database_exists and not manager.check_pivot_role_permissions_to_shared_database():
                    manager.grant_pivot_role_all_database_permissions_to_shared_database()
                manager.check_principals_permissions_to_shared_database()
            except Exception as e:
                manager.db_level_errors = [str(e)]

            for table in self.tables:
                manager.tbl_level_errors = []
                log.info(f'Verifying access to table {table.tableUri}/{table.GlueTableName}...')
                try:
                    share_item = ShareObjectRepository.find_sharable_item(
                        self.session, self.share_data.share.shareUri, table.tableUri
                    )
                    share_item_filter = None
                    if share_item.attachedDataFilterUri:
                        share_item_filter = ShareObjectItemRepository.get_share_item_filter_by_uri(
                            self.session, share_item.attachedDataFilterUri
                        )
                    manager.verify_table_exists_in_source_database(share_item, table)
                    manager.check_target_principals_permissions_to_source_table(table, share_item, share_item_filter)

                    if manager.cross_account:
                        if not RamClient.check_ram_invitation_status(
                            source_account_id=manager.source_account_id,
                            source_region=manager.source_account_region,
                            target_account_id=self.share_data.target_environment.AwsAccountId,
                            source_database=manager.source_database_name,
                            source_table_name=table.GlueTableName,
                        ):
                            manager.tbl_level_errors.append(
                                ShareErrorFormatter.missing_permission_error_msg(
                                    self.share_data.target_environment.AwsAccountId,
                                    'RAM Invitation',
                                    'ASSOCIATED',
                                    'Glue Table',
                                    f'{manager.source_database_name}.{table.GlueTableName}',
                                )
                            )
                    resource_link_name = self._build_resource_link_name(table.GlueTableName, share_item_filter)
                    manager.verify_resource_link_table_exists_in_target_database(resource_link_name)
                    manager.check_principals_permissions_to_resource_link_table(resource_link_name)

                except Exception as e:
                    manager.tbl_level_errors = [str(e)]

                if len(manager.db_level_errors) or len(manager.tbl_level_errors):
                    ShareStatusRepository.update_share_item_health_status(
                        self.session,
                        share_item,
                        ShareItemHealthStatus.Unhealthy.value,
                        ' | '.join(manager.db_level_errors) + ' | ' + ' | '.join(manager.tbl_level_errors),
                        datetime.now(),
                    )
                else:
                    ShareStatusRepository.update_share_item_health_status(
                        self.session, share_item, ShareItemHealthStatus.Healthy.value, None, datetime.now()
                    )
        return True

    def cleanup_shares(self) -> bool:
        """
        0) Check if source account details are properly initialized and initialize the Glue and LF clients
        1) Try to Grant Pivot Role all database permissions to the shared database
        2) For each revoked table:
            b) Check if table exists on glue catalog
            c) Check if resource link table exists in target account
            d) Check if the table is shared in other share requests to this target account
            e) If c is True (resource link table exists), try to revoke permission to principals to resource link table
            f) If c is True (resource link table exists), try to revoke permission to principals to table (and for QS Group if no other shares present for table)
            g) If c is True and (old-share or (new-share and d is True, no other shares of this table)) then try to delete resource link table
            g) If d is True (no other shares of this table with target), try to revoke permissions to target account to the original table
            h) delete share item
        3) Check if there are existing_shared_tables for this dataset with target environment
        4) If no existing_shared_tables, try delete shared database
        5) delete share

        Returns
        -------
        True
        """
        log.info('##### Starting Cleaning-up tables #######')
        manager = self._initialize_share_manager(self.tables)
        if not self.tables:
            log.info('No tables to revoke. Skipping...')
        else:
            if not S3ShareService.verify_principal_role(self.session, self.share_data.share):
                log.info(f'Principal role {self.share_data.share.principalRoleName} is not found.')
            if None in [
                manager.source_account_id,
                manager.source_account_region,
                manager.source_database_name,
            ]:
                raise Exception(
                    'Source account details not initialized properly. Please check if the catalog account is properly onboarded on data.all'
                )
            manager.initialize_clients()
            execute_and_suppress_exception(func=manager.grant_pivot_role_all_database_permissions_to_shared_database)

            for table in self.tables:
                log.info(f'Revoking access to table {table.tableUri}/{table.GlueTableName}...')
                share_item = ShareObjectRepository.find_sharable_item(
                    self.session, self.share_data.share.shareUri, table.tableUri
                )
                share_item_filter = None
                if share_item.attachedDataFilterUri:
                    share_item_filter = ShareObjectItemRepository.get_share_item_filter_by_uri(
                        self.session, share_item.attachedDataFilterUri
                    )
                log.info(f'Revoking access to table: {table.GlueTableName} ')
                execute_and_suppress_exception(
                    func=manager.check_table_exists_in_source_database, share_item=share_item, table=table
                )
                try:
                    log.info('Check resource link table exists')
                    resource_link_name = self._build_resource_link_name(table.GlueTableName, share_item_filter)

                    resource_link_table_exists = manager.check_resource_link_table_exists_in_target_database(
                        resource_link_name
                    )

                    if resource_link_table_exists:
                        log.info('Revoking principal permissions from resource link table')
                        execute_and_suppress_exception(
                            func=manager.revoke_principals_permissions_to_resource_link_table,
                            resource_link_name=resource_link_name,
                        )
                        log.info('Revoking principal permissions from table in source')
                        execute_and_suppress_exception(
                            func=manager.revoke_principals_permissions_to_table_in_source,
                            table=table,
                            share_item=share_item,
                            share_item_filter=share_item_filter,
                        )
                        if share_item_filter:
                            can_delete_resource_link = True
                        else:
                            can_delete_resource_link = (
                                False
                                if S3ShareObjectRepository.check_other_approved_share_item_table_exists(
                                    self.session,
                                    self.share_data.target_environment.environmentUri,
                                    share_item.itemUri,
                                    share_item.shareItemUri,
                                )
                                else True
                            )

                        if can_delete_resource_link:
                            execute_and_suppress_exception(
                                func=manager.grant_pivot_role_drop_permissions_to_resource_link_table,
                                resource_link_name=resource_link_name,
                            )
                            execute_and_suppress_exception(
                                func=manager.delete_resource_link_table_in_shared_database,
                                resource_link_name=resource_link_name,
                            )

                    if (
                        self.share_data.share.groupUri != self.share_data.dataset.SamlAdminGroupName
                        and self.share_data.share.groupUri != self.share_data.dataset.stewards
                    ):
                        log.info('Deleting TABLE READ permissions...')
                        S3ShareService.delete_dataset_table_read_permission(
                            self.session, self.share_data.share, table.tableUri
                        )
                except Exception:
                    log.exception('')

                # Delete share item
                self.session.delete(share_item)
                self.session.commit()

            if self.tables:
                log.info('Revoking permissions to target shared database...')
                execute_and_suppress_exception(func=manager.revoke_principals_database_permissions_to_shared_database)
                share_item_shared_states = ShareStatusRepository.get_share_item_shared_states()
                s3_dataset = DatasetRepository.get_dataset_by_uri(
                    session=self.session, dataset_uri=self.share_data.dataset.datasetUri
                )

                existing_shares_with_shared_tables_in_environment = (
                    S3ShareObjectRepository.list_dataset_shares_on_database(
                        session=self.session,
                        dataset_uri=self.share_data.dataset.datasetUri,
                        share_item_shared_states=share_item_shared_states,
                        item_type=ShareableType.Table.value,
                        database=s3_dataset.GlueDatabaseName,
                    )
                )
                if not len(existing_shares_with_shared_tables_in_environment):
                    log.info('Deleting target shared database...')
                    execute_and_suppress_exception(func=manager.delete_shared_database_in_target)
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

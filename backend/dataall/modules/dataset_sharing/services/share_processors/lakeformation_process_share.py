import logging

from dataall.core.environment.db.environment_models import Environment, EnvironmentGroup
from dataall.modules.dataset_sharing.services.dataset_sharing_enums import ShareItemStatus, ShareObjectActions, ShareItemActions, ShareableType
from dataall.modules.dataset_sharing.services.share_managers import LFShareManager
from dataall.modules.dataset_sharing.aws.ram_client import RamClient
from dataall.modules.datasets_base.db.dataset_models import DatasetTable, Dataset
from dataall.modules.dataset_sharing.db.share_object_models import ShareObject
from dataall.modules.dataset_sharing.db.share_object_repositories import ShareObjectRepository, ShareItemSM

log = logging.getLogger(__name__)


class ProcessLakeFormationShare(LFShareManager):
    def __init__(
        self,
        session,
        dataset: Dataset,
        share: ShareObject,
        shared_tables: [DatasetTable],
        revoked_tables: [DatasetTable],
        source_environment: Environment,
        target_environment: Environment,
        env_group: EnvironmentGroup,
    ):
        super().__init__(
            session,
            dataset,
            share,
            shared_tables,
            revoked_tables,
            source_environment,
            target_environment,
            env_group,
        )

    def process_approved_shares(self) -> bool:
        """
        1) Grant ALL permissions to pivotRole for source database in source account
        2) Create the shared database in target account if it doesn't exist
        3) Grant permissions to pivotRole and principals to "shared" database
        4) For each shared table:
            a) Update its status to SHARE_IN_PROGRESS with Action Start
            b) Check if table exists on glue catalog raise error if not and flag share item status to failed
            c) If it is a cross-account share:
                c.1) Revoke iamallowedgroups permissions from table
                c.2) Grant target account permissions to original table -> create RAM invitation
                c.3) Accept pending RAM invitation
            d) Create resource link for table in target account
            e) grant permission to principals to shared-table in target account
            f) grant permission to principals to resource link table
            g) update share item status to SHARE_SUCCESSFUL with Action Success

        Returns
        -------
        True if share is granted successfully
        False if share fails
        """

        log.info(
            '##### Starting Sharing tables #######'
        )
        success = True
        if not self.shared_tables:
            log.info("No tables to share. Skipping...")
        else:
            self.grant_pivot_role_all_database_permissions_to_source_database()
            self.check_if_exists_and_create_shared_database_in_target()
            self.grant_pivot_role_all_database_permissions_to_shared_database()
            self.grant_principals_database_permissions_to_shared_database()

            for table in self.shared_tables:
                log.info(f"Sharing table {table.GlueTableName}...")

                share_item = ShareObjectRepository.find_sharable_item(
                    self.session, self.share.shareUri, table.tableUri
                )

                if not share_item:
                    log.info(
                        f'Share Item not found for {self.share.shareUri} '
                        f'and Dataset Table {table.GlueTableName} continuing loop...'
                    )
                    continue

                shared_item_SM = ShareItemSM(ShareItemStatus.Share_Approved.value)
                new_state = shared_item_SM.run_transition(ShareObjectActions.Start.value)
                shared_item_SM.update_state_single_item(self.session, share_item, new_state)

                try:
                    self.check_table_exists_in_source_database(share_item, table)

                    if self.cross_account:
                        log.info(f'Processing cross-account permissions for table {table.GlueTableName}...')
                        # TODO: old shares, add if exists, use LFV3
                        self.revoke_iam_allowed_principals_from_table(table)
                        self.grant_target_account_permissions_to_source_table(table)
                        (
                            retry_share_table,
                            failed_invitations,
                        ) = RamClient.accept_ram_invitation(
                            source_account_id=self.source_environment.AwsAccountId,
                            source_region=self.source_environment.region,
                            target_account_id=self.target_environment.AwsAccountId,
                            target_region=self.target_environment.region,
                            source_database=self.dataset.GlueDatabaseName,
                            source_table=table
                        )
                        if retry_share_table:
                            self.grant_target_account_permissions_to_source_table(table)
                            RamClient.accept_ram_invitation(
                                source_account_id=self.source_environment.AwsAccountId,
                                source_region=self.source_environment.region,
                                target_account_id=self.target_environment.AwsAccountId,
                                target_region=self.target_environment.region,
                                source_database=self.dataset.GlueDatabaseName,
                                source_table=table
                            )
                    self.check_if_exists_and_create_resource_link_table_in_shared_database(table)
                    self.grant_principals_permissions_to_table_in_target(table)  # TODO WITH LFV3 we might be able to remove this
                    self.grant_principals_permissions_to_resource_link_table(table)

                    new_state = shared_item_SM.run_transition(ShareItemActions.Success.value)
                    shared_item_SM.update_state_single_item(self.session, share_item, new_state)

                except Exception as e:
                    new_state = shared_item_SM.run_transition(ShareItemActions.Failure.value)
                    shared_item_SM.update_state_single_item(self.session, share_item, new_state)
                    success = False

                    self.handle_share_failure(table=table, error=e)

        return success

    def process_revoked_shares(self) -> bool:
        """
        1) For each revoked table:
            a) Update its status to REVOKE_IN_PROGRESS with Action Start
            b) Check if table exists on glue catalog raise error if not and flag share item status to failed
            c) Check if resource link table exists in target account
            d) Check if the table is shared in other share requests to this target account
            e) If c is True (resource link table exists), revoke permission to principals to resource link table
            f) If c is True (resource link table exists), revoke permission to principals to table (and for QS Group if no other shares present for table)
            g) If c is True and (old-share or (new-share and d is True, no other shares of this table)) then delete resource link table
            g) If d is True (no other shares of this table with target), revoke permissions to target account to the original table
            h) update share item status to REVOKE_SUCCESSFUL with Action Success
        2) Check if there are existing_shared_tables for this dataset with target environment
        3) If no existing_shared_tables, delete shared database

        Returns
        -------
        True if share is revoked successfully
        False if revoke fails
        """
        log.info(
            '##### Starting Revoking tables #######'
        )
        success = True
        for table in self.revoked_tables:
            share_item = ShareObjectRepository.find_sharable_item(
                self.session, self.share.shareUri, table.tableUri
            )

            revoked_item_SM = ShareItemSM(ShareItemStatus.Revoke_Approved.value)
            new_state = revoked_item_SM.run_transition(ShareObjectActions.Start.value)
            revoked_item_SM.update_state_single_item(self.session, share_item, new_state)

            try:
                log.info(f'Revoking access to table: {table.GlueTableName} ')

                self.check_table_exists_in_source_database(share_item, table)

                resource_link_table_exists = self.check_resource_link_table_exists_in_target_database(table)
                other_table_shares_in_env = True if ShareObjectRepository.other_approved_share_item_table_exists(
                    self.session,
                    self.target_environment.environmentUri,
                    share_item.itemUri,
                    share_item.shareItemUri
                ) else False

                if resource_link_table_exists:
                    log.info(f'Revoking access to resource link table for: {table.GlueTableName} ')
                    self.revoke_principals_permissions_to_resource_link_table(table)
                    self.revoke_principals_permissions_to_table_in_target(table)

                    if (self.is_new_share and not other_table_shares_in_env) or not self.is_new_share:
                        log.info(f'Deleting resource link table for: {table.GlueTableName} ')
                        self.delete_resource_link_table_in_shared_database(table)

                if not other_table_shares_in_env:
                    log.info(f'Revoking access from target account to table: {table.GlueTableName} ')
                    self.revoke_external_account_access_on_source_account(table)

                new_state = revoked_item_SM.run_transition(ShareItemActions.Success.value)
                revoked_item_SM.update_state_single_item(self.session, share_item, new_state)

            except Exception as e:
                new_state = revoked_item_SM.run_transition(ShareItemActions.Failure.value)
                revoked_item_SM.update_state_single_item(self.session, share_item, new_state)
                success = False

                self.handle_revoke_failure(table=table, error=e)

        try:
            existing_shared_tables = ShareObjectRepository.check_existing_shared_items_of_type(
                session=self.session,
                uri=self.share.shareUri,
                item_type=ShareableType.Table.value
            )
            log.info(
                f'Still remaining tables shared in this share object = {existing_shared_tables}')

            if not existing_shared_tables and self.revoked_tables:
                log.info("Revoking permissions to target shared database...")
                self.revoke_principals_database_permissions_to_shared_database()
                # TODO Add test for this new method

            existing_shared_tables_environment = ShareObjectRepository.list_dataset_shares_with_existing_shared_items(
                session=self.session,
                dataset_uri=self.dataset.datasetUri,
                environment_uri=self.target_environment.environmentUri,
                item_type=ShareableType.Table.value
            )

            log.info(f'Still remaining tables shared from this dataset to this environment = {existing_shared_tables_environment}')
            if not existing_shared_tables_environment and self.revoked_tables:
                log.info("Deleting target shared database...")
                self.delete_shared_database_in_target()
        except Exception as e:
            log.error(
                f'Failed to clean-up database permission or delete shared database {self.shared_db_name} '
                f'due to: {e}'
            )
            success = False
        return success

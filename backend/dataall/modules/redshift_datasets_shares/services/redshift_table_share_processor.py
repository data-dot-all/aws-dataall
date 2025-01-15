import logging
from datetime import datetime
from typing import List
from dataall.base.utils.naming_convention import NamingConventionService, NamingConventionPattern
from dataall.modules.notifications.services.admin_notifications import AdminNotificationService
from dataall.modules.shares_base.services.sharing_service import ShareData
from dataall.modules.shares_base.services.share_processor_manager import SharesProcessorInterface
from dataall.modules.shares_base.db.share_object_repositories import ShareObjectRepository
from dataall.modules.shares_base.db.share_object_state_machines import ShareItemSM
from dataall.modules.shares_base.db.share_state_machines_repositories import ShareStatusRepository
from dataall.modules.shares_base.services.shares_enums import (
    ShareItemHealthStatus,
    ShareItemStatus,
    ShareObjectActions,
    ShareItemActions,
)
from dataall.modules.shares_base.services.share_object_service import ShareObjectService
from dataall.modules.shares_base.services.share_manager_utils import ShareErrorFormatter, execute_and_suppress_exception
from dataall.modules.redshift_datasets.db.redshift_models import RedshiftTable
from dataall.modules.redshift_datasets.db.redshift_connection_repositories import RedshiftConnectionRepository
from dataall.modules.redshift_datasets.services.redshift_enums import RedshiftType
from dataall.modules.redshift_datasets_shares.aws.redshift_data import redshift_share_data_client
from dataall.modules.redshift_datasets_shares.aws.redshift import redshift_share_client
from dataall.modules.redshift_datasets_shares.db.redshift_share_object_repositories import RedshiftShareRepository
from dataall.modules.redshift_datasets_shares.services.redshift_shares_enums import RedshiftDatashareStatus

log = logging.getLogger(__name__)

DATAALL_PREFIX = 'dataall'


class ProcessRedshiftShare(SharesProcessorInterface):
    def __init__(self, session, share_data, shareable_items, reapply=False):
        self.session = session
        self.share_data: ShareData = share_data
        self.dataset = share_data.dataset
        self.share = share_data.share
        self.tables: List[RedshiftTable] = shareable_items
        self.reapply: bool = reapply

        dataset_connection = RedshiftConnectionRepository.get_redshift_connection(
            self.session, self.dataset.connectionUri
        )

        self.source_connection = RedshiftConnectionRepository.get_namespace_admin_connection(
            session,
            environment_uri=self.share_data.source_environment.environmentUri,
            namespace_id=dataset_connection.nameSpaceId,
        )

        self.target_connection = RedshiftConnectionRepository.get_redshift_connection(
            session, share_data.share.principalId
        )
        self.cross_account = (
            self.share_data.target_environment.AwsAccountId != self.share_data.source_environment.AwsAccountId
        )
        self.redshift_role = share_data.share.principalRoleName

        # There is a unique datashare per dataset per target namespace
        # To restrict pivot role permissions on the datashares both in source and target we prefix them with dataall prefix
        self.datashare_name = NamingConventionService(
            target_label=self.target_connection.nameSpaceId,
            pattern=NamingConventionPattern.REDSHIFT_DATASHARE,
            target_uri=self.dataset.datasetUri,
            resource_prefix=DATAALL_PREFIX,
        ).build_compliant_name()
        self.datashare_arn = f'arn:aws:redshift:{self.share_data.source_environment.region}:{self.share_data.source_environment.AwsAccountId}:datashare:{self.source_connection.nameSpaceId}/{self.datashare_name}'
        self.local_db = self._build_local_db_name()
        self.external_schema = self._build_external_schema_name()

    def _build_local_db_name(self) -> str:
        return f'{self.target_connection.name}_{self.source_connection.database}_{self.dataset.name}'

    def _build_external_schema_name(self) -> str:
        return f'{self.source_connection.database}_{self.dataset.schema}_{self.dataset.name}'

    def _initialize_clients(self):
        self.redshift_data_client_in_source = redshift_share_data_client(
            account_id=self.share_data.source_environment.AwsAccountId,
            region=self.share_data.source_environment.region,
            connection=self.source_connection,
        )
        self.redshift_data_client_in_target = redshift_share_data_client(
            account_id=self.share_data.target_environment.AwsAccountId,
            region=self.share_data.target_environment.region,
            connection=self.target_connection,
        )

    def process_approved_shares(self) -> bool:
        """
        1) (in source namespace) Create datashare for this dataset for this target namespace. If it does not exist yet. One time operation.
        2) (in source namespace) Add schema to the datashare, if not already added. One time operation.
        3) Grant access to the consumer cluster to the datashare
            3.a) SAME ACCOUNT: (in source namespace) Grant access to the consumer cluster to the datashare, if not already granted. One time operation.
            3.b) CROSS ACCOUNT:
               - (in source namespace) Grant access to the consumer ACCOUNT, if not already granted. One time operation.
               - (in source account) Authorize datashare, if not already authorized. One time operation
               - (in target account) Associate datashare with target namespace, if not already authorized. One time operation
        4) (in target namespace) Create local database WITH PERMISSIONS from datashare, if it does not exist yet. One time operation.
        5) (in target namespace) Grant usage access to the redshift role to the local database, if not already granted. One time operation.
        6) (in target namespace) Create external schema in local database, if it does not exist yet. One time operation.
        7) (in target namespace) Grant usage access to the redshift role to the schema.
        For each table:
            8) (in source namespace) Add table to the datashare, if not already added.
            9) (in target namespace) Grant select access to the requested table to the redshift role in the local db.
            10) (in target namespace) Grant select access to the requested table to the redshift role in the external schema.
        Returns
        -------
        True if share is granted successfully
        """

        log.info('##### Starting Sharing Redshift tables #######')
        success = True
        if not self.tables:
            log.info('No Redshift tables to share. Skipping...')
        else:
            if not self.reapply:
                shared_item_SM = ShareItemSM(ShareItemStatus.Share_Approved.value)
                new_state = shared_item_SM.run_transition(ShareObjectActions.Start.value)
                shared_item_SM.update_state(self.session, self.share.shareUri, new_state)
            try:
                self._initialize_clients()
                # 1) Create datashare for this dataset for this target namespace. If it does not exist yet
                newly_created = self.redshift_data_client_in_source.create_datashare(datashare=self.datashare_name)

                # 2) Add schema to the datashare, if not already added
                self.redshift_data_client_in_source.add_schema_to_datashare(
                    datashare=self.datashare_name, schema=self.dataset.schema
                )
                # 3) Grant access to the consumer namespace to the datashare, if not already granted
                if self.cross_account:
                    log.info('Processing cross-account datashare grants')
                    # (in source namespace) Grant access to the consumer ACCOUNT, if not already granted
                    self.redshift_data_client_in_source.grant_datashare_usage_to_account(
                        datashare=self.datashare_name, account=self.share_data.target_environment.AwsAccountId
                    )
                    # (in source account) Authorize datashare, if not already authorized
                    redshift_client_in_source = redshift_share_client(
                        account_id=self.share_data.source_environment.AwsAccountId,
                        region=self.share_data.source_environment.region,
                    )
                    redshift_client_in_source.authorize_datashare(
                        datashare_arn=self.datashare_arn, account=self.share_data.target_environment.AwsAccountId
                    )
                    # (in target account) Associate datashare with target namespace, if not already authorized
                    redshift_client_in_target = redshift_share_client(
                        account_id=self.share_data.target_environment.AwsAccountId,
                        region=self.share_data.target_environment.region,
                    )
                    consumer_arn = (
                        f'arn:aws:redshift-serverless:{self.share_data.target_environment.region}:{self.share_data.target_environment.AwsAccountId}:namespace/{self.target_connection.nameSpaceId}'
                        if self.target_connection.redshiftType == RedshiftType.Serverless.value
                        else f'arn:aws:redshift:{self.share_data.target_environment.region}:{self.share_data.target_environment.AwsAccountId}:namespace:{self.target_connection.nameSpaceId}'
                    )
                    redshift_client_in_target.associate_datashare(
                        datashare_arn=self.datashare_arn,
                        consumer_arn=consumer_arn,
                    )
                else:
                    log.info('Processing same-account datashare grants')
                    self.redshift_data_client_in_source.grant_datashare_usage_to_namespace(
                        datashare=self.datashare_name, namespace=self.target_connection.nameSpaceId
                    )

                # 4) Create local database from datashare, if it does not exist yet
                if newly_created:
                    # For reapply/unsuccessful share we need to ensure that the database created has been created for the newly_created database
                    self.redshift_data_client_in_target.drop_database(database=self.local_db)
                self.redshift_data_client_in_target.create_database_from_datashare(
                    database=self.local_db,
                    datashare=self.datashare_name,
                    namespace=self.source_connection.nameSpaceId,
                    account=self.share_data.source_environment.AwsAccountId if self.cross_account else None,
                )
                # 5) Grant usage access to the redshift role to the new local database
                self.redshift_data_client_in_target.grant_database_usage_access_to_redshift_role(
                    database=self.local_db, rs_role=self.redshift_role
                )

                # 6) Create external schema in local database, if it does not exist yet
                self.redshift_data_client_in_target.create_external_schema(
                    database=self.local_db, schema=self.dataset.schema, external_schema=self.external_schema
                )
                # 7) Grant usage access to the redshift role to the external schema
                self.redshift_data_client_in_target.grant_schema_usage_access_to_redshift_role(
                    schema=self.external_schema, rs_role=self.redshift_role
                )
                # 7) Grant usage access to the redshift role to the schema of the self.local_db
                self.redshift_data_client_in_target.grant_schema_usage_access_to_redshift_role(
                    database=self.local_db, schema=self.dataset.schema, rs_role=self.redshift_role
                )

                for table in self.tables:
                    try:
                        # 8) Add tables to the datashare, if not already added
                        self.redshift_data_client_in_source.add_table_to_datashare(
                            datashare=self.datashare_name, schema=self.dataset.schema, table_name=table.name
                        )
                        # 9) Grant select access to the requested tables to the redshift role to the self.local_db
                        self.redshift_data_client_in_target.grant_select_table_access_to_redshift_role(
                            database=self.local_db,
                            schema=self.dataset.schema,
                            table=table.name,
                            rs_role=self.redshift_role,
                        )
                        # 10) Grant select access to the requested tables to the redshift role to the external_schema
                        self.redshift_data_client_in_target.grant_select_table_access_to_redshift_role(
                            schema=self.external_schema,
                            table=table.name,
                            rs_role=self.redshift_role,
                        )

                        share_item = ShareObjectRepository.find_sharable_item(
                            self.session, self.share.shareUri, table.rsTableUri
                        )
                        if not self.reapply:
                            table_SM = ShareItemSM(new_state)
                            final_state = table_SM.run_transition(ShareItemActions.Success.value)
                            table_SM.update_state_single_item(self.session, share_item, final_state)

                        ShareStatusRepository.update_share_item_health_status(
                            self.session, share_item, ShareItemHealthStatus.Healthy.value, None, datetime.now()
                        )
                    except Exception as e:
                        success = False
                        log.error(
                            f'Failed to process approved redshift dataset {self.dataset.name} '
                            f'table {table.name} '
                            f'from source {self.source_connection=}'
                            f'with target {self.target_connection=}'
                            f'due to: {e}'
                        )
                        share_item = ShareObjectRepository.find_sharable_item(
                            self.session, self.share.shareUri, table.rsTableUri
                        )
                        if not self.reapply:
                            table_SM = ShareItemSM(new_state)
                            new_state = table_SM.run_transition(ShareItemActions.Failure.value)
                            table_SM.update_state_single_item(self.session, share_item, new_state)
                        else:
                            ShareStatusRepository.update_share_item_health_status(
                                self.session, share_item, ShareItemHealthStatus.Unhealthy.value, str(e), datetime.now()
                            )

            except Exception as e:
                log.error(
                    f'Failed to process approved redshift dataset {self.dataset.name} '
                    f'tables {[t.name for t in self.tables]} '
                    f'from source {self.source_connection.name} in namespace {self.source_connection.nameSpaceId} '
                    f'with target {self.target_connection.name} in namespace {self.target_connection.nameSpaceId} '
                    f'due to: {e}'
                )
                if not self.reapply:
                    new_state = shared_item_SM.run_transition(ShareItemActions.Failure.value)
                    shared_item_SM.update_state(self.session, self.share.shareUri, new_state)
                else:
                    for table in self.tables:
                        share_item = ShareObjectRepository.find_sharable_item(
                            self.session, self.share.shareUri, table.rsTableUri
                        )
                        ShareStatusRepository.update_share_item_health_status(
                            self.session, share_item, ShareItemHealthStatus.Unhealthy.value, str(e), datetime.now()
                        )
                AdminNotificationService().notify_admins_with_error_log(
                    process_error='Error occurred while processing redshift table share request',
                    process_name='redshift table share processor',
                    error_logs=[str(e)],
                )
                return False
        return success

    def process_revoked_shares(self) -> bool:
        """
        For each table:
            Update table status with Start Action (Revoke_Approved ---> Revoke_In_Progress)
            try:
                1) (in target namespace) Revoke access to the revoked tables to the redshift role in external schema (if schema exists)
                2) (in target namespace) Revoke access to the revoked tables to the redshift role in self.local_db (if database exists)
                3) (in source namespace) If that table is not shared in this namespace, remove table from datashare (if datashare exists)
            except:
                Update table status with Failure Action (Revoke_In_Progress ---> Revoke_Failed)
        If the previous is successful, we proceed to clean-up shared resources across datashares:
        try:
            4) (in target namespace) If no more tables are shared with the redshift role, revoke usage access to the external schema to the redshift role
            5) (in target namespace) If no more tables are shared with the redshift role, revoke usage access to the self.local_db to the redshift role
            6) (in target namespace) If no more tables are shared with any role in this namespace, drop external schema
            7) (in target namespace) If no more tables are shared with any role in this namespace, drop local database
            8) (in source namespace) If no more tables are shared with any role in this namespace, drop datashare
            # Drop datashare deletes it from source and target, alongside its permissions (for both same and cross account)
            Update NON-FAILED tables with Success Action (Revoke_In_Progress ---> Revoke_Succeeded)
        except:
            Update tables with Failure Action (Revoke_In_Progress ---> Revoke_Failed)
        Returns
        -------
        True if share is revoked successfully
        """
        log.info('##### Starting Revoke Redshift tables #######')
        success = True
        if not self.tables:
            log.info('No Redshift tables to revoke. Skipping...')
        else:
            self._initialize_clients()

            for table in self.tables:
                log.info(f'Revoking access to table {table}...')
                try:
                    share_item = ShareObjectRepository.find_sharable_item(
                        self.session, self.share.shareUri, table.rsTableUri
                    )

                    revoked_item_SM = ShareItemSM(ShareItemStatus.Revoke_Approved.value)
                    started_state = revoked_item_SM.run_transition(ShareObjectActions.Start.value)
                    revoked_item_SM.update_state_single_item(self.session, share_item, started_state)

                    local_db_exists = self.redshift_data_client_in_target.check_database_exists(database=self.local_db)
                    # 1) (in target namespace) Revoke access to the revoked tables to the redshift role in external schema (if schema exists)
                    if local_db_exists and self.redshift_data_client_in_target.check_schema_exists(
                        schema=self.external_schema, database=self.target_connection.database
                    ):
                        self.redshift_data_client_in_target.revoke_select_table_access_to_redshift_role(
                            schema=self.external_schema, table=table.name, rs_role=self.redshift_role
                        )
                    else:
                        log.info(
                            'External schema does not exist or local database does not exist, permissions cannot be revoked'
                        )
                    # 2) (in target namespace) Revoke access to the revoked tables to the redshift role in local_db (if database exists)
                    if local_db_exists:
                        self.redshift_data_client_in_target.revoke_select_table_access_to_redshift_role(
                            database=self.local_db,
                            schema=self.dataset.schema,
                            table=table.name,
                            rs_role=self.redshift_role,
                        )
                    else:
                        log.info('Database does not exist, no permissions need to be revoked')
                    # 3) (in source namespace) If that table is not shared in this namespace, remove table from datashare (if datashare exists)
                    if (
                        RedshiftShareRepository.count_other_shared_items_redshift_table_with_connection(
                            session=self.session,
                            share_uri=self.share.shareUri,
                            table_uri=table.rsTableUri,
                            connection_uri=self.share.principalId,
                        )
                        == 0
                    ):
                        log.info(
                            f'No other share items are sharing this table {table.name} with this namespace {self.target_connection.nameSpaceId}'
                        )
                        if self.redshift_data_client_in_source.check_datashare_exists(self.datashare_name):
                            self.redshift_data_client_in_source.remove_table_from_datashare(
                                datashare=self.datashare_name, schema=self.dataset.schema, table_name=table.name
                            )

                except Exception as e:
                    success = False
                    log.error(
                        f'Failed to process revoked redshift dataset {self.dataset.name} '
                        f'table {table.name} '
                        f'from source {self.source_connection.name} in namespace {self.source_connection.nameSpaceId} '
                        f'with target {self.target_connection.name} in namespace {self.target_connection.nameSpaceId} '
                        f'due to: {e}'
                    )
                    share_item = ShareObjectRepository.find_sharable_item(
                        self.session, self.share.shareUri, table.rsTableUri
                    )
                    failed_table_SM = ShareItemSM(started_state)
                    failed_state = failed_table_SM.run_transition(ShareItemActions.Failure.value)
                    failed_table_SM.update_state_single_item(self.session, share_item, failed_state)
                    ShareStatusRepository.update_share_item_health_status(
                        self.session, share_item, ShareItemHealthStatus.Unhealthy.value, str(e), datetime.now()
                    )
                    AdminNotificationService().notify_admins_with_error_log(
                        process_error='Error occurred while revoking redshift table share request',
                        process_name='redshift tables share processor',
                        error_logs=[str(e)],
                    )
            self.session.commit()
            try:
                if success:
                    log.info('Cleaning up shared resources in redshift datashares...')
                    # 4) (in target namespace) If no more tables are shared with the redshift role, revoke usage access to the external schema to the redshift role
                    # 5) (in target namespace) If no more tables are shared with the redshift role, revoke usage access to the local_db to the redshift role
                    if (
                        RedshiftShareRepository.count_dataset_shared_items_with_redshift_role(
                            session=self.session,
                            dataset_uri=self.dataset.datasetUri,
                            rs_role=self.redshift_role,
                            connection_uri=self.share.principalId,
                        )
                        == 0
                    ):  # In this check, if a table is in Revoke_In_Progress it does not count as shared state
                        log.info(
                            f'No other tables of this dataset are shared with this redshift role {self.redshift_role}'
                        )
                        self.redshift_data_client_in_target.revoke_schema_usage_access_to_redshift_role(
                            schema=self.external_schema, rs_role=self.redshift_role
                        )
                        if local_db_exists:
                            self.redshift_data_client_in_target.revoke_database_usage_access_to_redshift_role(
                                database=self.local_db, rs_role=self.redshift_role
                            )
                        else:
                            log.info('Database does not exist, no permissions need to be revoked')
                    # 6) (in target namespace) If no more tables are shared with any role in this namespace, drop external schema
                    # 7) (in target namespace) If no more tables are shared with any role in this namespace, drop local database
                    # 8) (in source namespace) If no more tables are shared with any role in this namespace, drop datashare
                    if (
                        RedshiftShareRepository.count_dataset_shared_items_with_namespace(
                            session=self.session,
                            dataset_uri=self.dataset.datasetUri,
                            connection_uri=self.share.principalId,
                        )
                        == 0
                    ):
                        log.info(
                            f'No other tables of this dataset are shared with this namespace {self.target_connection.nameSpaceId}'
                        )
                        self.redshift_data_client_in_target.drop_schema(schema=self.external_schema)
                        self.redshift_data_client_in_target.drop_database(database=self.local_db)
                        self.redshift_data_client_in_source.drop_datashare(datashare=self.datashare_name)

                    # Update NON-FAILED tables with Success Action (Revoke_In_Progress ---> Revoke_Succeeded)
                    non_failed_item_SM = ShareItemSM(started_state)
                    final_state = non_failed_item_SM.run_transition(ShareItemActions.Success.value)
                    non_failed_item_SM.update_state(self.session, self.share.shareUri, final_state)
                    for table in self.tables:
                        share_item = ShareObjectRepository.find_sharable_item(
                            self.session, self.share.shareUri, table.rsTableUri
                        )
                        ShareStatusRepository.update_share_item_health_status(
                            self.session, share_item, None, None, share_item.lastVerificationTime
                        )

            except Exception as e:
                log.error(
                    f'Failed to clean up shared resources in redshift datashares for redshift dataset {self.dataset.name} '
                    f'tables {[t.name for t in self.tables]} '
                    f'from source {self.source_connection.name} in namespace {self.source_connection.nameSpaceId} '
                    f'with target {self.target_connection.name} in namespace {self.target_connection.nameSpaceId} '
                    f'due to: {e}'
                )
                all_failed_state = revoked_item_SM.run_transition(ShareItemActions.Failure.value)
                revoked_item_SM.update_state(self.session, self.share.shareUri, all_failed_state)
                for table in self.tables:
                    share_item = ShareObjectRepository.find_sharable_item(
                        self.session, self.share.shareUri, table.rsTableUri
                    )
                    ShareStatusRepository.update_share_item_health_status(
                        self.session, share_item, ShareItemHealthStatus.Unhealthy.value, str(e), datetime.now()
                    )
                AdminNotificationService().notify_admins_with_error_log(
                    process_error='Error occurred while revoking redshift table share request',
                    process_name='redshift tables share processor',
                    error_logs=[str(e)],
                )
                return False
            return success

    def verify_shares_health_status(self) -> bool:
        """
        1) (in source namespace) Check the datashare exists
        2) (in source namespace) Check that schema is added to datashare
        3) (in source namespace) Check the access is granted to the consumer namespace to the datashare
            3.a) SAME ACCOUNT: (in source namespace) Check describe datashare from namespace
            3.b) CROSS ACCOUNT:
               - (in source account) Check status of datashare in source
               - (in target account) Check status of datashare in target
        4) (in target namespace) Check that local db exists
        5) (in target namespace) Check that the redshift role has access to the local db
        6) (in target namespace) Check that external schema exists
        7) (in target namespace) Check that the redshift role has access to the extenal schema
        For each table:
            8) (in source namespace) Check that table is added to datashare
            9) (in target namespace) Check that the redshift role has select access to the requested table in the local db.
            10) (in target namespace) Check that the redshift role has select access to the requested table in the external schema.
        """
        share_object_item_health_status = True
        log.info('##### Verifying Redshift tables #######')
        if not self.tables:
            log.info('No tables to verify. Skipping...')
        else:
            tbl_level_errors = []
            ds_level_errors = []
            self._initialize_clients()
            try:
                # 1) (in source namespace) Check that datashare exists
                if not self.redshift_data_client_in_source.check_datashare_exists(self.datashare_name):
                    ds_level_errors.append(ShareErrorFormatter.dne_error_msg('Redshift datashare', self.datashare_name))
                # 2) (in source namespace) Check that schema is added to datashare
                if not self.redshift_data_client_in_source.check_schema_in_datashare(
                    datashare=self.datashare_name, schema=self.dataset.schema
                ):
                    ds_level_errors.append(
                        ShareErrorFormatter.dne_error_msg(
                            'Redshift schema added to datashare',
                            f'datashare_name={self.datashare_name}, schema={self.dataset.schema}',
                        )
                    )
                # 3) (in target namespace) Check the access is granted to the consumer cluster to the datashare
                if self.cross_account:
                    # 3.b) Check that datashare in source is authorized
                    redshift_client_in_source = redshift_share_client(
                        account_id=self.share_data.source_environment.AwsAccountId,
                        region=self.share_data.source_environment.region,
                    )
                    if (
                        status_in_source := redshift_client_in_source.get_datashare_status(
                            datashare_arn=self.datashare_arn,
                            consumer_id=self.share_data.target_environment.AwsAccountId,
                        )
                    ) not in [RedshiftDatashareStatus.Active.value, RedshiftDatashareStatus.Authorized.value]:
                        ds_level_errors.append(
                            ShareErrorFormatter.wrong_status_error_msg(
                                resource_type='Redshift datashare in source account',
                                target_resource=self.datashare_name,
                                status=status_in_source,
                            )
                        )

                    # 3.b) Check that datashare in target is available
                    redshift_client_in_target = redshift_share_client(
                        account_id=self.share_data.target_environment.AwsAccountId,
                        region=self.share_data.target_environment.region,
                    )
                    consumer_arn = (
                        f'arn:aws:redshift-serverless:{self.share_data.target_environment.region}:{self.share_data.target_environment.AwsAccountId}:namespace/{self.target_connection.nameSpaceId}'
                        if self.target_connection.redshiftType == RedshiftType.Serverless.value
                        else f'arn:aws:redshift:{self.share_data.target_environment.region}:{self.share_data.target_environment.AwsAccountId}:namespace:{self.target_connection.nameSpaceId}'
                    )
                    if (
                        status_in_target := redshift_client_in_target.get_datashare_status(
                            datashare_arn=self.datashare_arn, consumer_id=consumer_arn
                        )
                    ) not in [RedshiftDatashareStatus.Active.value]:
                        ds_level_errors.append(
                            ShareErrorFormatter.wrong_status_error_msg(
                                resource_type='Redshift datashare in target account',
                                target_resource=self.datashare_name,
                                status=status_in_target,
                            )
                        )
                # 3.a)b) (in target namespace) Check the access is granted to the consumer cluster to the datashare
                if not self.redshift_data_client_in_target.check_consumer_permissions_to_datashare(
                    datashare=self.datashare_name
                ):
                    ds_level_errors.append(
                        ShareErrorFormatter.missing_permission_error_msg(
                            self.target_connection.nameSpaceId,
                            'SHARE',
                            ['SHARE'],
                            'Redshift datashare',
                            self.datashare_name,
                        )
                    )
                # 4) (in target namespace) Check that local db exists
                if not self.redshift_data_client_in_target.check_database_exists(self.local_db):
                    ds_level_errors.append(
                        ShareErrorFormatter.dne_error_msg('Redshift local database in consumer', self.local_db)
                    )
                # 5) (in target namespace) Check that the redshift role has access to the local db
                if not self.redshift_data_client_in_target.check_role_permissions_in_database(
                    database=self.local_db, rs_role=self.redshift_role
                ):
                    ds_level_errors.append(
                        ShareErrorFormatter.missing_permission_error_msg(
                            self.redshift_role, 'USAGE', ['USAGE'], 'Redshift local database in consumer', self.local_db
                        )
                    )
                # 6) (in target namespace) Check that external schema exists
                if not self.redshift_data_client_in_target.check_schema_exists(
                    schema=self.external_schema, database=self.target_connection.database
                ):
                    ds_level_errors.append(
                        ShareErrorFormatter.dne_error_msg('Redshift external schema', self.external_schema)
                    )
                # 7) (in target namespace) Check that the redshift role has access to the external schema
                if not self.redshift_data_client_in_target.check_role_permissions_in_schema(
                    schema=self.external_schema, rs_role=self.redshift_role
                ):
                    ds_level_errors.append(
                        ShareErrorFormatter.missing_permission_error_msg(
                            self.redshift_role, 'USAGE', ['USAGE'], 'Redshift external schema', self.external_schema
                        )
                    )
            except Exception as e:
                ds_level_errors = [str(e)]

            for table in self.tables:
                try:
                    # 8) (in source namespace) Check that table is added to datashare
                    if not self.redshift_data_client_in_source.check_table_in_datashare(
                        datashare=self.datashare_name, table_name=table.name
                    ):
                        tbl_level_errors.append(
                            ShareErrorFormatter.dne_error_msg(
                                'Redshift table added to datashare',
                                f'datashare_name={self.datashare_name}, table={table.name}',
                            )
                        )
                    # 9) (in target namespace) Check that the redshift role has select access to the requested table in the local db.
                    # 10) (in target namespace) Check that the redshift role has select access to the requested table in the external schema.
                    # Not possible to check role permissions through system functions or tables. Not implemented at the moment
                except Exception as e:
                    tbl_level_errors.append(str(e))

                share_item = ShareObjectRepository.find_sharable_item(
                    self.session, self.share.shareUri, table.rsTableUri
                )
                if len(ds_level_errors) or len(tbl_level_errors):
                    ShareStatusRepository.update_share_item_health_status(
                        self.session,
                        share_item,
                        ShareItemHealthStatus.Unhealthy.value,
                        ' | '.join(ds_level_errors) + ' | ' + ' | '.join(tbl_level_errors),
                        datetime.now(),
                    )
                    share_object_item_health_status = False
                else:
                    ShareStatusRepository.update_share_item_health_status(
                        self.session, share_item, ShareItemHealthStatus.Healthy.value, None, datetime.now()
                    )
        return share_object_item_health_status

    def cleanup_shares(self) -> bool:
        """
        For each table:
            Update table status with Start Action (Revoke_Approved ---> Revoke_In_Progress)
            try:
                1) (in target namespace) Revoke access to the revoked tables to the redshift role in external schema (if schema exists)
                2) (in target namespace) Revoke access to the revoked tables to the redshift role in self.local_db (if database exists)
                3) (in source namespace) If that table is not shared in this namespace, remove table from datashare (if datashare exists)
            except:
                Update table status with Failure Action (Revoke_In_Progress ---> Revoke_Failed)
        If the previous is successful, we proceed to clean-up shared resources across datashares:
        try:
            4) (in target namespace) If no more tables are shared with the redshift role, revoke usage access to the external schema to the redshift role
            5) (in target namespace) If no more tables are shared with the redshift role, revoke usage access to the self.local_db to the redshift role
            6) (in target namespace) If no more tables are shared with any role in this namespace, drop external schema
            7) (in target namespace) If no more tables are shared with any role in this namespace, drop local database
            8) (in source namespace) If no more tables are shared with any role in this namespace, drop datashare
            # Drop datashare deletes it from source and target, alongside its permissions (for both same and cross account)
            Update NON-FAILED tables with Success Action (Revoke_In_Progress ---> Revoke_Succeeded)
        except:
            Update tables with Failure Action (Revoke_In_Progress ---> Revoke_Failed)
        Returns
        -------
        True if share is revoked successfully
        """
        log.info('##### Starting Cleaning up Redshift tables #######')
        if not self.tables:
            log.info('No Redshift tables to revoke. Skipping...')
        else:
            self._initialize_clients()
            for table in self.tables:
                log.info(f'Revoking access to table {table}...')
                local_db_exists = self.redshift_data_client_in_target.check_database_exists(database=self.local_db)
                # 1) (in target namespace) Revoke access to the revoked tables to the redshift role in external schema (if schema exists)
                if local_db_exists and self.redshift_data_client_in_target.check_schema_exists(
                    schema=self.external_schema, database=self.target_connection.database
                ):
                    execute_and_suppress_exception(
                        func=self.redshift_data_client_in_target.revoke_select_table_access_to_redshift_role,
                        schema=self.external_schema,
                        table=table.name,
                        rs_role=self.redshift_role,
                    )
                else:
                    log.info(
                        'External schema does not exist or local database does not exist, permissions cannot be revoked'
                    )
                # 2) (in target namespace) Revoke access to the revoked tables to the redshift role in local_db (if database exists)
                if local_db_exists:
                    execute_and_suppress_exception(
                        func=self.redshift_data_client_in_target.revoke_select_table_access_to_redshift_role,
                        database=self.local_db,
                        schema=self.dataset.schema,
                        table=table.name,
                        rs_role=self.redshift_role,
                    )
                else:
                    log.info('Database does not exist, no permissions need to be revoked')
                # 3) (in source namespace) If that table is not shared in this namespace, remove table from datashare (if datashare exists)
                if (
                    RedshiftShareRepository.count_other_shared_items_redshift_table_with_connection(
                        session=self.session,
                        share_uri=self.share.shareUri,
                        table_uri=table.rsTableUri,
                        connection_uri=self.share.principalId,
                    )
                    == 0
                ):
                    log.info(
                        f'No other share items are sharing this table {table.name} with this namespace {self.target_connection.nameSpaceId}'
                    )
                    if self.redshift_data_client_in_source.check_datashare_exists(self.datashare_name):
                        execute_and_suppress_exception(
                            func=self.redshift_data_client_in_source.remove_table_from_datashare,
                            datashare=self.datashare_name,
                            schema=self.dataset.schema,
                            table_name=table.name,
                        )
                # Delete share item
                share_item = ShareObjectRepository.find_sharable_item(
                    self.session, self.share.shareUri, table.rsTableUri
                )
                self.session.delete(share_item)
            self.session.commit()

            log.info('Cleaning up shared resources in redshift datashares...')
            # 4) (in target namespace) If no more tables are shared with the redshift role, revoke usage access to the external schema to the redshift role
            # 5) (in target namespace) If no more tables are shared with the redshift role, revoke usage access to the local_db to the redshift role
            if (
                RedshiftShareRepository.count_dataset_shared_items_with_redshift_role(
                    session=self.session,
                    dataset_uri=self.dataset.datasetUri,
                    rs_role=self.redshift_role,
                    connection_uri=self.share.principalId,
                )
                == 0
            ):  # In this check, if a table is in Revoke_In_Progress it does not count as shared state
                log.info(f'No other tables of this dataset are shared with this redshift role {self.redshift_role}')
                execute_and_suppress_exception(
                    func=self.redshift_data_client_in_target.revoke_schema_usage_access_to_redshift_role,
                    schema=self.external_schema,
                    rs_role=self.redshift_role,
                )
                if local_db_exists:
                    execute_and_suppress_exception(
                        func=self.redshift_data_client_in_target.revoke_database_usage_access_to_redshift_role,
                        database=self.local_db,
                        rs_role=self.redshift_role,
                    )
                else:
                    log.info('Database does not exist, no permissions need to be revoked')
            # 6) (in target namespace) If no more tables are shared with any role in this namespace, drop external schema
            # 7) (in target namespace) If no more tables are shared with any role in this namespace, drop local database
            # 8) (in source namespace) If no more tables are shared with any role in this namespace, drop datashare
            if (
                RedshiftShareRepository.count_dataset_shared_items_with_namespace(
                    session=self.session,
                    dataset_uri=self.dataset.datasetUri,
                    connection_uri=self.share.principalId,
                )
                == 0
            ):
                log.info(
                    f'No other tables of this dataset are shared with this namespace {self.target_connection.nameSpaceId}'
                )
                execute_and_suppress_exception(
                    func=self.redshift_data_client_in_target.drop_schema, schema=self.external_schema
                )
                execute_and_suppress_exception(
                    func=self.redshift_data_client_in_target.drop_database, database=self.local_db
                )
                execute_and_suppress_exception(
                    func=self.redshift_data_client_in_source.drop_datashare, datashare=self.datashare_name
                )
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

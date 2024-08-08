import logging
from datetime import datetime
from typing import List
from dataall.base.utils.naming_convention import NamingConventionService, NamingConventionPattern
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
from dataall.modules.redshift_datasets_shares.aws.redshift_data import redshift_share_data_client
from dataall.modules.redshift_datasets.db.redshift_models import RedshiftTable
from dataall.modules.redshift_datasets.db.redshift_connection_repositories import RedshiftConnectionRepository
from dataall.modules.redshift_datasets_shares.db.redshift_share_object_repositories import RedshiftShareRepository

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
        self.source_connection = dataset_connection
        self.target_connection = RedshiftConnectionRepository.get_redshift_connection(
            session, share_data.share.principalId
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

    def _build_local_db_name(self) -> str:
        return f'{self.target_connection.name}_{self.source_connection.database}'

    def _build_external_schema_name(self) -> str:
        return f'{self.source_connection.database}_{self.dataset.schema}'

    def process_approved_shares(self) -> bool:
        """
        1) (in source namespace) Create datashare for this dataset for this target namespace. If it does not exist yet. One time operation.
        2) (in source namespace) Add schema to the datashare, if not already added. One time operation.
        3) (in source namespace) Grant access to the consumer cluster to the datashare, if not already granted. One time operation.
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
                redshift_client_in_source = redshift_share_data_client(
                    account_id=self.share_data.source_environment.AwsAccountId,
                    region=self.share_data.source_environment.region,
                    connection=self.source_connection,
                )
                redshift_client_in_target = redshift_share_data_client(
                    account_id=self.share_data.target_environment.AwsAccountId,
                    region=self.share_data.target_environment.region,
                    connection=self.target_connection,
                )
                local_db = self._build_local_db_name()
                external_schema = self._build_external_schema_name()

                # 1) Create datashare for this dataset for this target namespace. If it does not exist yet
                redshift_client_in_source.create_datashare(datashare=self.datashare_name)

                # 2) Add schema to the datashare, if not already added
                redshift_client_in_source.add_schema_to_datashare(
                    datashare=self.datashare_name, schema=self.dataset.schema
                )
                # 3) Grant access to the consumer cluster to the datashare, if not already granted
                redshift_client_in_source.grant_usage_to_datashare(
                    datashare=self.datashare_name, namespace=self.target_connection.nameSpaceId
                )

                # 4) Create local database from datashare, if it does not exist yet
                redshift_client_in_target.create_database_from_datashare(
                    database=local_db,
                    datashare=self.datashare_name,
                    namespace=self.source_connection.nameSpaceId,
                )
                # 5) Grant usage access to the redshift role to the new local database
                redshift_client_in_target.grant_database_usage_access_to_redshift_role(
                    database=local_db, rs_role=self.redshift_role
                )

                # 6) Create external schema in local database, if it does not exist yet
                redshift_client_in_target.create_external_schema(
                    database=local_db, schema=self.dataset.schema, external_schema=external_schema
                )
                # 7) Grant usage access to the redshift role to the external schema
                redshift_client_in_target.grant_schema_usage_access_to_redshift_role(
                    schema=external_schema, rs_role=self.redshift_role
                )

                for table in self.tables:
                    try:
                        # 8) Add tables to the datashare, if not already added
                        redshift_client_in_source.add_table_to_datashare(
                            datashare=self.datashare_name, schema=self.dataset.schema, table_name=table.name
                        )
                        # 9) Grant select access to the requested tables to the redshift role to the local_db
                        redshift_client_in_target.grant_select_table_access_to_redshift_role(
                            database=local_db, schema=self.dataset.schema, table=table.name, rs_role=self.redshift_role
                        )
                        # 10) Grant select access to the requested tables to the redshift role to the external_schema
                        redshift_client_in_target.grant_select_table_access_to_redshift_role(
                            schema=external_schema,
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
                    f'from source {self.source_connection.name} in namespace {self.source_connection.nameSpaceId}'
                    f'with target {self.target_connection.name} in namespace {self.target_connection.nameSpaceId}'
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
                return False
        return success

    def process_revoked_shares(self) -> bool:
        """
        For each table
            1) (in target namespace) Revoke access to the revoked tables to the redshift role in external schema
            2) (in target namespace) Revoke access to the revoked tables to the redshift role in local_db
            3) (in source namespace) If that table is not shared in this namespace, remove table from datashare
        4) (in target namespace) If no more tables are shared with the redshift role, revoke usage access to the external schema to the redshift role
        5) (in target namespace) If no more tables are shared with the redshift role, revoke usage access to the local_db to the redshift role
        6) (in target namespace) If no more tables are shared with any role in this namespace, drop local database
        7) (in source namespace) If no more tables are shared with any role in this namespace, drop datashare
        # Drop datashare deletes it from source and target, alongside its permissions.
        Returns
        -------
        True if share is revoked successfully
        """
        log.info('##### Starting Revoke Redshift tables #######')
        success = True
        if not self.tables:
            log.info('No Redshift tables to revoke. Skipping...')
        else:
            try:
                redshift_client_in_source = redshift_share_data_client(
                    account_id=self.share_data.source_environment.AwsAccountId,
                    region=self.share_data.source_environment.region,
                    connection=self.source_connection,
                )
                redshift_client_in_target = redshift_share_data_client(
                    account_id=self.share_data.target_environment.AwsAccountId,
                    region=self.share_data.target_environment.region,
                    connection=self.target_connection,
                )
                local_db = self._build_local_db_name()
                external_schema = self._build_external_schema_name()

                for table in self.tables:
                    log.info(f'Revoking access to table {table}...')
                    share_item = ShareObjectRepository.find_sharable_item(
                        self.session, self.share.shareUri, table.rsTableUri
                    )

                    revoked_item_SM = ShareItemSM(ShareItemStatus.Revoke_Approved.value)
                    new_state = revoked_item_SM.run_transition(ShareObjectActions.Start.value)
                    revoked_item_SM.update_state_single_item(self.session, share_item, new_state)

                    try:
                        # 1) (in target namespace) Revoke access to the revoked tables to the redshift role in external schema
                        redshift_client_in_target.revoke_select_table_access_to_redshift_role(
                            schema=external_schema, table=table.name, rs_role=self.redshift_role
                        )
                        # 2) (in target namespace) Revoke access to the revoked tables to the redshift role in local_db
                        redshift_client_in_target.revoke_select_table_access_to_redshift_role(
                            database=local_db, schema=self.dataset.schema, table=table.name, rs_role=self.redshift_role
                        )
                        # 3) (in source namespace) If that table is not shared in this namespace, remove table from datashare
                        if (
                            RedshiftShareRepository.count_other_shares_redshift_table_with_connection(
                                session=self.session,
                                share_uri=self.share.shareUri,
                                table_uri=table.rsTableUri,
                                namespace_id=self.target_connection.nameSpaceId,
                            )
                            > 0
                        ):
                            log.info(
                                f'No other share items are sharing this table {table.name} with this namespace {self.target_connection.nameSpaceId}'
                            )
                            redshift_client_in_source.remove_table_from_datashare(
                                datashare=self.datashare_name, schema=self.dataset.schema, table_name=table.name
                            )
                        # 4) Update table status with ShareItemActions.Success
                        new_state = revoked_item_SM.run_transition(ShareItemActions.Success.value)
                        revoked_item_SM.update_state_single_item(self.session, share_item, new_state)

                        ShareStatusRepository.update_share_item_health_status(
                            self.session, share_item, None, None, share_item.lastVerificationTime
                        )
                    except Exception as e:
                        success = False
                        log.error(
                            f'Failed to process revoked redshift dataset {self.dataset.name} '
                            f'table {table.name} '
                            f'from source {self.source_connection.name} in namespace {self.source_connection.nameSpaceId}'
                            f'with target {self.target_connection.name} in namespace {self.target_connection.nameSpaceId}'
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

                    # 4) (in target namespace) If no more tables are shared with the redshift role, revoke usage access to the external schema to the redshift role
                    # 5) (in target namespace) If no more tables are shared with the redshift role, revoke usage access to the local_db to the redshift role
                    if (
                        RedshiftShareRepository.count_shares_with_redshift_role(
                            session=self.session,
                            dataset_uri=self.dataset.datasetUri,
                            rs_role=self.redshift_role,
                            namespace_id=self.target_connection.nameSpaceId,
                        )
                        > 0
                    ):
                        log.info(
                            f'No other tables of this dataset are shared with this redshift role {self.redshift_role}'
                        )
                        redshift_client_in_target.revoke_schema_usage_access_to_redshift_role(
                            schema=external_schema, rs_role=self.redshift_role
                        )
                        redshift_client_in_target.revoke_database_usage_access_to_redshift_role(
                            database=local_db, rs_role=self.redshift_role
                        )

                    # 6) (in target namespace) If no more tables are shared with any role in this namespace, drop local database
                    # 7) (in source namespace) If no more tables are shared with any role in this namespace, drop datashare
                    if (
                        RedshiftShareRepository.count_shares_with_namespace(
                            session=self.session,
                            dataset_uri=self.dataset.datasetUri,
                            namespace_id=self.target_connection.nameSpaceId,
                        )
                        > 1
                    ):
                        log.info(
                            f'No other tables of this dataset are shared with this namespace {self.target_connection.nameSpaceId}'
                        )
                        redshift_client_in_target.drop_database(database=local_db)
                        redshift_client_in_source.drop_datashare(datashare=self.datashare_name)

            except Exception as e:
                log.error(
                    f'Failed to process revoked redshift dataset {self.dataset.name} '
                    f'tables {[t.name for t in self.tables]} '
                    f'from source {self.source_connection.name} in namespace {self.source_connection.nameSpaceId}'
                    f'with target {self.target_connection.name} in namespace {self.target_connection.nameSpaceId}'
                    f'due to: {e}'
                )
                if not self.reapply:
                    new_state = revoked_item_SM.run_transition(ShareItemActions.Failure.value)
                    revoked_item_SM.update_state(self.session, self.share.shareUri, new_state)
                else:
                    for table in self.tables:
                        share_item = ShareObjectRepository.find_sharable_item(
                            self.session, self.share.shareUri, table.rsTableUri
                        )
                        ShareStatusRepository.update_share_item_health_status(
                            self.session, share_item, ShareItemHealthStatus.Unhealthy.value, str(e), datetime.now()
                        )
                return False
            return success

    def verify_shares(self) -> bool:
        pass

import logging
from dataall.base.context import get_context
from dataall.core.permissions.services.resource_policy_service import ResourcePolicyService
from dataall.core.permissions.services.tenant_policy_service import TenantPolicyService
from dataall.modules.catalog.db.glossary_repositories import GlossaryRepository
from dataall.core.environment.services.environment_service import EnvironmentService
from dataall.modules.s3_datasets.aws.athena_table_client import AthenaTableClient
from dataall.modules.s3_datasets.aws.glue_dataset_client import DatasetCrawler
from dataall.modules.s3_datasets.db.dataset_table_repositories import DatasetTableRepository
from dataall.modules.s3_datasets.db.dataset_table_data_filter_repositories import DatasetTableDataFilterRepository
from dataall.modules.s3_datasets.indexers.table_indexer import DatasetTableIndexer
from dataall.modules.s3_datasets.indexers.dataset_indexer import DatasetIndexer
from dataall.modules.s3_datasets.services.dataset_permissions import (
    UPDATE_DATASET_TABLE,
    MANAGE_DATASETS,
    DELETE_DATASET_TABLE,
    SYNC_DATASET,
)
from dataall.modules.s3_datasets.aws.lf_data_filter_client import LakeFormationDataFilterClient
from dataall.modules.s3_datasets.db.dataset_repositories import DatasetRepository
from dataall.modules.datasets_base.services.datasets_enums import ConfidentialityClassification
from dataall.modules.s3_datasets.db.dataset_models import DatasetTable, S3Dataset
from dataall.modules.s3_datasets.services.dataset_permissions import (
    PREVIEW_DATASET_TABLE,
    DATASET_TABLE_ALL,
    GET_DATASET_TABLE,
)
from dataall.modules.s3_datasets.services.dataset_service import DatasetService
from dataall.base.utils import json_utils
from dataall.base.db import exceptions

log = logging.getLogger(__name__)


class DatasetTableService:
    @staticmethod
    def _get_dataset_uri(session, table_uri):
        table = DatasetTableRepository.get_dataset_table_by_uri(session, table_uri)
        return table.datasetUri

    @staticmethod
    def get_table(uri: str):
        with get_context().db_engine.scoped_session() as session:
            return DatasetTableRepository.get_dataset_table_by_uri(session, uri)

    @staticmethod
    @ResourcePolicyService.has_resource_permission(GET_DATASET_TABLE)
    def get_table_restricted_information(uri: str, table: DatasetTable):
        return table

    @staticmethod
    @TenantPolicyService.has_tenant_permission(MANAGE_DATASETS)
    @ResourcePolicyService.has_resource_permission(UPDATE_DATASET_TABLE, parent_resource=_get_dataset_uri)
    def update_table(uri: str, table_data: dict = None):
        with get_context().db_engine.scoped_session() as session:
            table = DatasetTableRepository.get_dataset_table_by_uri(session, uri)

            for k in [attr for attr in table_data.keys() if attr != 'terms']:
                setattr(table, k, table_data.get(k))

            DatasetTableRepository.save(session, table)
            if 'terms' in table_data:
                GlossaryRepository.set_glossary_terms_links(
                    session, get_context().username, table.tableUri, 'DatasetTable', table_data['terms']
                )

        DatasetTableIndexer.upsert(session, table_uri=table.tableUri)
        DatasetIndexer.upsert(session=session, dataset_uri=table.datasetUri)
        return table

    @staticmethod
    @TenantPolicyService.has_tenant_permission(MANAGE_DATASETS)
    @ResourcePolicyService.has_resource_permission(DELETE_DATASET_TABLE, parent_resource=_get_dataset_uri)
    def delete_table(uri: str):
        with get_context().db_engine.scoped_session() as session:
            table = DatasetTableRepository.get_dataset_table_by_uri(session, uri)
            DatasetService.check_before_delete(session, table.tableUri, action=DELETE_DATASET_TABLE)
            DatasetService.execute_on_delete(session, table.tableUri, action=DELETE_DATASET_TABLE)

            table_data_filters = DatasetTableDataFilterRepository.list_data_filters(session, table.tableUri)
            dataset = DatasetRepository.get_dataset_by_uri(session, table.datasetUri)
            lf_client = LakeFormationDataFilterClient(table=table, dataset=dataset)
            # Delete LF Filters
            for data_filter in table_data_filters:
                lf_client.delete_table_data_filter(data_filter)
            DatasetTableRepository.delete_all_table_filters(session, table)

            DatasetTableRepository.delete(session, table)
            DatasetTableService._delete_dataset_table_read_permission(session, uri)

            GlossaryRepository.delete_glossary_terms_links(
                session, target_uri=table.tableUri, target_type='DatasetTable'
            )
        DatasetTableIndexer.delete_doc(doc_id=uri)
        return True

    @staticmethod
    def preview(uri: str):
        context = get_context()
        with context.db_engine.scoped_session() as session:
            table: DatasetTable = DatasetTableRepository.get_dataset_table_by_uri(session, uri)
            dataset = DatasetRepository.get_dataset_by_uri(session, table.datasetUri)
            if (
                ConfidentialityClassification.get_confidentiality_level(dataset.confidentiality)
                != ConfidentialityClassification.Unclassified.value
            ) and (dataset.SamlAdminGroupName not in context.groups and dataset.stewards not in context.groups):
                raise exceptions.UnauthorizedOperation(
                    action=PREVIEW_DATASET_TABLE,
                    message='User is not authorized to Preview Table for Confidential datasets',
                )
            env = EnvironmentService.get_environment_by_uri(session, dataset.environmentUri)
            return AthenaTableClient(env, table).get_table()

    @staticmethod
    @ResourcePolicyService.has_resource_permission(GET_DATASET_TABLE)
    def get_glue_table_properties(uri: str):
        with get_context().db_engine.scoped_session() as session:
            table: DatasetTable = DatasetTableRepository.get_dataset_table_by_uri(session, uri)
            return json_utils.to_string(table.GlueTableProperties).replace('\\', ' ')

    @classmethod
    @TenantPolicyService.has_tenant_permission(MANAGE_DATASETS)
    @ResourcePolicyService.has_resource_permission(SYNC_DATASET)
    def sync_tables_for_dataset(cls, uri):
        context = get_context()
        with context.db_engine.scoped_session() as session:
            dataset = DatasetRepository.get_dataset_by_uri(session, uri)
            S3Prefix = dataset.S3BucketName
            tables = DatasetCrawler(dataset).list_glue_database_tables(S3Prefix)
            cls.sync_existing_tables(session, uri=dataset.datasetUri, glue_tables=tables)
            DatasetTableIndexer.upsert_all(session=session, dataset_uri=dataset.datasetUri)
            DatasetTableIndexer.remove_all_deleted(session=session, dataset_uri=dataset.datasetUri)
            DatasetIndexer.upsert(session=session, dataset_uri=dataset.datasetUri)
            return DatasetRepository.count_dataset_tables(session, dataset.datasetUri)

    @staticmethod
    def sync_existing_tables(session, uri, glue_tables=None):
        dataset: S3Dataset = DatasetRepository.get_dataset_by_uri(session, uri)
        if dataset:
            existing_tables = DatasetTableRepository.find_dataset_tables(session, uri)
            existing_table_names = [e.GlueTableName for e in existing_tables]
            existing_dataset_tables_map = {t.GlueTableName: t for t in existing_tables}
            DatasetTableRepository.update_existing_tables_status(existing_tables, glue_tables, session)
            log.info(f'existing_tables={glue_tables}')
            for table in glue_tables:
                if table['Name'] not in existing_table_names:
                    log.info(f'Storing new table: {table} for dataset db {dataset.GlueDatabaseName}')
                    updated_table = DatasetTableRepository.create_synced_table(session, dataset, table)
                    DatasetTableService._attach_dataset_table_permission(session, dataset, updated_table.tableUri)
                else:
                    log.info(f'Updating table: {table} for dataset db {dataset.GlueDatabaseName}')
                    updated_table: DatasetTable = existing_dataset_tables_map.get(table['Name'])
                    updated_table.GlueTableProperties = json_utils.to_json(table.get('Parameters', {}))

                DatasetTableRepository.sync_table_columns(session, updated_table, table)

        return True

    @staticmethod
    def _attach_dataset_table_permission(session, dataset: S3Dataset, table_uri):
        """
        Attach Table permissions to dataset groups
        """
        permission_group = {
            dataset.SamlAdminGroupName,
            dataset.stewards if dataset.stewards is not None else dataset.SamlAdminGroupName,
        }
        for group in permission_group:
            ResourcePolicyService.attach_resource_policy(
                session=session,
                group=group,
                permissions=DATASET_TABLE_ALL,
                resource_uri=table_uri,
                resource_type=DatasetTable.__name__,
            )

    @staticmethod
    def _delete_dataset_table_read_permission(session, table_uri):
        """
        Delete Table  permissions to dataset groups
        """
        ResourcePolicyService.delete_resource_policy(
            session=session, group=None, resource_uri=table_uri, resource_type=DatasetTable.__name__
        )

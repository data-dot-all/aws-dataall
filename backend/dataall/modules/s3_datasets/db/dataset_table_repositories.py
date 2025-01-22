import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List

from sqlalchemy.sql import and_

from dataall.base.db import exceptions
from dataall.modules.s3_datasets.db.dataset_models import (
    DatasetTableColumn,
    DatasetTable,
    S3Dataset,
    DatasetTableDataFilter,
)
from dataall.base.utils import json_utils
from dataall.modules.shares_base.db.share_object_models import ShareObject
from dataall.modules.shares_base.db.share_object_repositories import ShareObjectRepository
from dataall.modules.shares_base.services.shares_enums import ShareItemStatus

logger = logging.getLogger(__name__)


"""
Dataclass containing status of the dataset table and the share objects where the dataset table is present 
"""
@dataclass
class DatasetTableShareDetails:
    tableUri: str
    status: str
    share_objects: List[ShareObject] = field(default_factory=list)


class DatasetTableRepository:
    @staticmethod
    def save(session, table: DatasetTable):
        session.add(table)

    @staticmethod
    def create_synced_table(session, dataset: S3Dataset, table: dict):
        updated_table = DatasetTable(
            datasetUri=dataset.datasetUri,
            label=table['Name'],
            name=table['Name'],
            region=dataset.region,
            owner=dataset.owner,
            GlueDatabaseName=dataset.GlueDatabaseName,
            AWSAccountId=dataset.AwsAccountId,
            S3BucketName=dataset.S3BucketName,
            S3Prefix=table.get('StorageDescriptor', {}).get('Location'),
            GlueTableName=table['Name'],
            LastGlueTableStatus='InSync',
            GlueTableProperties=json_utils.to_json(table.get('Parameters', {})),
        )
        session.add(updated_table)
        session.commit()
        return updated_table

    @staticmethod
    def delete(session, table: DatasetTable):
        session.delete(table)

    @staticmethod
    def delete_all_table_filters(session, table: DatasetTable):
        session.query(DatasetTableDataFilter).filter(
            and_(
                DatasetTableDataFilter.tableUri == table.tableUri,
            )
        ).delete()
        session.commit()

    @staticmethod
    def get_dataset_table_by_uri(session, table_uri):
        table: DatasetTable = session.query(DatasetTable).get(table_uri)
        if not table:
            raise exceptions.ObjectNotFound('DatasetTable', table_uri)
        return table

    @staticmethod
    def update_existing_tables_status(session, existing_tables, glue_tables):
        # Map between tables and the details about the table ( i.e. status, share object on that table )
        updated_tables_status_map: Dict[DatasetTable, DatasetTableShareDetails] = dict()
        for existing_table in existing_tables:
            if existing_table.GlueTableName not in [t['Name'] for t in glue_tables]:
                if existing_table.LastGlueTableStatus != 'Deleted':
                    existing_table.LastGlueTableStatus = 'Deleted'
                    # Get all the share objects where the table is used
                    dataset_shares: List[ShareObject] = ShareObjectRepository.list_dataset_shares_for_item_uris(session=session, dataset_uri=existing_table.datasetUri, share_item_shared_states=[ShareItemStatus.Share_Succeeded.value], item_uris=[existing_table.tableUri])
                    updated_tables_status_map[existing_table] = DatasetTableShareDetails(status='Deleted', share_objects=dataset_shares, tableUri=existing_table.tableUri)
                    logger.info(f'Existing Table {existing_table.GlueTableName} status set to Deleted from Glue')
                else:
                    logger.info(f'Existing Table {existing_table.GlueTableName} status already set Deleted')
            elif (
                    existing_table.GlueTableName in [t['Name'] for t in glue_tables]
                    and existing_table.LastGlueTableStatus == 'Deleted'
            ):
                existing_table.LastGlueTableStatus = 'InSync'
                updated_tables_status_map[existing_table] = DatasetTableShareDetails(status='InSync: Updated to InSync from Deleted', share_objects=[], tableUri=existing_table.tableUri) # Keeping share object empty as no user needs to be informed when a table gets in sync
                logger.info(
                    f'Updating Existing Table {existing_table.GlueTableName} status set to InSync from Deleted after found in Glue'
                )
        return updated_tables_status_map

    @staticmethod
    def find_all_active_tables(session, dataset_uri):
        return (
            session.query(DatasetTable)
            .filter(
                and_(
                    DatasetTable.datasetUri == dataset_uri,
                    DatasetTable.LastGlueTableStatus != 'Deleted',
                )
            )
            .all()
        )

    @staticmethod
    def find_all_deleted_tables(session, dataset_uri):
        return (
            session.query(DatasetTable)
            .filter(
                and_(
                    DatasetTable.datasetUri == dataset_uri,
                    DatasetTable.LastGlueTableStatus == 'Deleted',
                )
            )
            .all()
        )

    @staticmethod
    def sync_table_columns(session, dataset_table, glue_table):
        DatasetTableRepository.delete_all_table_columns(session, dataset_table)

        columns = [
            {**item, **{'columnType': 'column'}} for item in glue_table.get('StorageDescriptor', {}).get('Columns', [])
        ]
        partitions = [
            {**item, **{'columnType': f'partition_{index}'}}
            for index, item in enumerate(glue_table.get('PartitionKeys', []))
        ]

        logger.debug(f'Found columns {columns} for table {dataset_table}')
        logger.debug(f'Found partitions {partitions} for table {dataset_table}')

        for col in columns + partitions:
            table_col = DatasetTableColumn(
                name=col['Name'],
                description=col.get('Comment', 'No description provided'),
                label=col['Name'],
                owner=dataset_table.owner,
                datasetUri=dataset_table.datasetUri,
                tableUri=dataset_table.tableUri,
                AWSAccountId=dataset_table.AWSAccountId,
                GlueDatabaseName=dataset_table.GlueDatabaseName,
                GlueTableName=dataset_table.GlueTableName,
                region=dataset_table.region,
                typeName=col['Type'],
                columnType=col['columnType'],
            )
            session.add(table_col)

    @staticmethod
    def delete_all_table_columns(session, dataset_table):
        session.query(DatasetTableColumn).filter(
            and_(
                DatasetTableColumn.GlueDatabaseName == dataset_table.GlueDatabaseName,
                DatasetTableColumn.GlueTableName == dataset_table.GlueTableName,
            )
        ).delete()
        session.commit()

    @staticmethod
    def get_table_by_s3_prefix(session, s3_prefix, accountid, region):
        table: DatasetTable = (
            session.query(DatasetTable)
            .filter(
                and_(
                    DatasetTable.S3Prefix.startswith(s3_prefix),
                    DatasetTable.AWSAccountId == accountid,
                    DatasetTable.region == region,
                )
            )
            .first()
        )
        if not table:
            logging.info(f'No table found for  {s3_prefix}|{accountid}|{region}')
        else:
            logging.info(f'Found table {table.tableUri}|{table.GlueTableName}|{table.S3Prefix}')
            return table

    @staticmethod
    def find_dataset_tables(session, dataset_uri):
        return session.query(DatasetTable).filter(DatasetTable.datasetUri == dataset_uri).all()

    @staticmethod
    def delete_dataset_tables(session, dataset_uri) -> bool:
        tables = (
            session.query(DatasetTable)
            .filter(
                and_(
                    DatasetTable.datasetUri == dataset_uri,
                )
            )
            .all()
        )
        for table in tables:
            table.deleted = datetime.now()
        return tables

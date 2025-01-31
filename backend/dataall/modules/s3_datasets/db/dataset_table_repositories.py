import logging
from datetime import datetime
from typing import List

from sqlalchemy.sql import and_

from dataall.base.db import exceptions
from dataall.core.activity.db.activity_models import Activity
from dataall.modules.s3_datasets.db.dataset_models import (
    DatasetTableColumn,
    DatasetTable,
    S3Dataset,
    DatasetTableDataFilter,
)
from dataall.base.utils import json_utils
from dataall.modules.shares_base.db.share_object_repositories import ShareObjectRepository
from dataall.modules.shares_base.db.share_object_models import ShareObjectItem
from dataall.modules.shares_base.services.shares_enums import ShareItemStatus

logger = logging.getLogger(__name__)


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
    def update_existing_tables_status(existing_tables, glue_tables, session):
        for existing_table in existing_tables:
            if existing_table.GlueTableName not in [t['Name'] for t in glue_tables]:
                existing_table.LastGlueTableStatus = 'Deleted'
                logger.info(f'Existing Table {existing_table.GlueTableName} status set to Deleted from Glue')
                # Once the table item is deleted from glue and no longer part of the dataset
                # Find out where this item is used in shares and delete all the share items.
                share_item_status_filter = [ShareItemStatus.Share_Succeeded.value]
                share_object_items: List[ShareObjectItem] = (
                    ShareObjectRepository.list_share_object_items_for_item_with_status(
                        session=session, item_uri=existing_table.tableUri, status=share_item_status_filter
                    )
                )
                logger.info(
                    f'Found {len(share_object_items)} share objects where the table {existing_table.tableUri} is present as a share item in state: {share_item_status_filter}. Deleting those share items'
                )
                for share_object_item in share_object_items:
                    activity = Activity(
                        action='SHARE_OBJECT_ITEM:DELETE',
                        label='SHARE_OBJECT_ITEM:DELETE',
                        owner='dataall-automation',
                        summary=f'dataall-automation deleted share object: {share_object_item.itemName} with uri: {share_object_item.itemUri} since the glue table associated was deleted from source glue db',
                        targetUri=share_object_item.itemUri,
                        targetType='share_object_item',
                    )
                    session.add(activity)
                    session.delete(share_object_item)
            elif (
                existing_table.GlueTableName in [t['Name'] for t in glue_tables]
                and existing_table.LastGlueTableStatus == 'Deleted'
            ):
                existing_table.LastGlueTableStatus = 'InSync'
                logger.info(
                    f'Updating Existing Table {existing_table.GlueTableName} status set to InSync from Deleted after found in Glue'
                )

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

import logging
from os import name

from botocore.exceptions import ClientError

from dataall.base.aws.sts import SessionHelper

log = logging.getLogger(__name__)


class GlueClient:
    def __init__(self, account_id, region, role=None):
        pivot_role_session = SessionHelper.remote_session(accountid=account_id, region=region)
        aws_session = (
            SessionHelper.get_session(base_session=pivot_role_session, role_arn=role) if role else pivot_role_session
        )
        self._client = aws_session.client('glue', region_name=region)
        self._account_id = account_id
        self._region = region

    def get_table_metadata(self, database, table_name):
        try:
            table_metadata = self._client.get_table(DatabaseName=database, Name=table_name)
            table_name = table_metadata['Table']['Name']
            column_metadata = table_metadata['Table']['StorageDescriptor']['Columns']
            partition_metadata = table_metadata['Table']['PartitionKeys']
            meta_data = f"""
            Database Name: {database}
            Table Name: {table_name} 
            Column Metadata: {column_metadata}
            Partition Metadata: {partition_metadata}
            """
        except ClientError as e:
            log.error(f'Error fetching metadata for {table_name=}: {e}')
            raise e
        return meta_data

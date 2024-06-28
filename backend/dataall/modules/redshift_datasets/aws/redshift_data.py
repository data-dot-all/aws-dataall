import logging
import time
from botocore.exceptions import ClientError
from dataall.base.aws.sts import SessionHelper
from dataall.modules.redshift_datasets.db.redshift_models import RedshiftConnection


log = logging.getLogger(__name__)


class RedshiftData:
    def __init__(self, account_id: str, region: str, connection: RedshiftConnection) -> None:
        session = SessionHelper.remote_session(accountid=account_id, region=region)
        self.client = session.client(service_name='redshift-data', region_name=region)
        self.database = connection.database
        self.execute_connection_params = {
            'Database': connection.database,
        }
        if connection.workgroup:
            self.execute_connection_params['WorkgroupName'] = connection.workgroup
        if connection.clusterId:
            self.execute_connection_params['ClusterIdentifier'] = connection.clusterId
        if connection.secretArn:
            self.execute_connection_params['SecretArn'] = connection.secretArn
        if connection.redshiftUser:
            self.execute_connection_params['DbUser'] = connection.redshiftUser

    def _execute_statement(self, sql: str):
        log.info(f'Executing {sql=} with connection {self.execute_connection_params}...')
        execute_dict = self.execute_connection_params
        execute_dict['Sql'] = sql
        execute_statement_response = self.client.execute_statement(**execute_dict)

        execution_finished = False
        describe_statement_response = None
        while not execution_finished:
            describe_statement_response = self.client.describe_statement(Id=execute_statement_response['Id'])
            time.sleep(1)
            execution_finished = describe_statement_response['Status'] not in ['PICKED', 'STARTED', 'SUBMITTED']

        if describe_statement_response['Status'] == 'FAILED':
            raise Exception(describe_statement_response['Error'])

        log.info(f'Received response {describe_statement_response=}')
        return describe_statement_response['Id']

    @staticmethod
    def identifier(name: str) -> str:
        return f'"{name}"'

    def fully_qualified_table_name(self, schema: str, table_name: str) -> str:
        return f'{RedshiftData.identifier(self.database)}.{RedshiftData.identifier(schema)}.{RedshiftData.identifier(table_name)}'

    def list_redshift_databases(self):
        databases = []
        try:
            log.info(f"Looking for {self.database} in databases...")

            list_databases_response = self.client.list_databases(**self.execute_connection_params)
            if "Databases" in list_databases_response.keys():
                databases = list_databases_response["Databases"]
            log.info(f'Returning {databases=}...')
            return databases
        except ClientError as e:
            log.error(e)
            raise e

    def list_redshift_schemas(self):
        schemas = []
        try:
            log.debug(f"Fetching {self.database} schemas")
            list_schemas_response = self.client.list_schemas(**self.execute_connection_params)
            if "Schemas" in list_schemas_response.keys():
                schemas = list_schemas_response["Schemas"]

            # Remove "internal" schemas
            if "information_schema" in schemas:
                schemas.remove("information_schema")
            if "pg_catalog" in schemas:
                schemas.remove("pg_catalog")
            log.info(f'Returning {schemas=}...')
            return schemas
        except ClientError as e:
            log.error(e)
            raise e

    def list_redshift_tables(self, schema: str):
        tables_list = []
        try:
            log.debug(f"Fetching {self.database} tables")
            list_tables_response = self.client.list_tables(**self.execute_connection_params, SchemaPattern=schema, MaxResults=1000)
            next_token = list_tables_response.get("NextToken", None)
            if "Tables" in list_tables_response.keys():
                tables_list = list_tables_response["Tables"]
                while next_token:
                    list_tables_response = self.client.list_tables(
                        **self.execute_connection_params, NextToken=next_token, MaxResults=1000, SchemaPattern=schema
                    )
                    if "Tables" in list_tables_response.keys():
                        tables_list.extend(list_tables_response["Tables"])
                    next_token = list_tables_response.get("NextToken", None)

            tables = [{"name": table["name"], "type": table["type"]} for table in tables_list if
                      table["type"] in ["TABLE", "VIEW"]]
            log.info(f'Returning {tables=}...')
            return tables
        except ClientError as e:
            log.error(e)
            raise e

    def create_datashare(self, schema: str, datashare: str):
        try:
            log.info(f'Creating {datashare=}...')
            sql_statement = f'CREATE DATASHARE {RedshiftData.identifier(datashare)};'
            self._execute_statement(sql=sql_statement)

            sql_statement = f'ALTER DATASHARE {RedshiftData.identifier(datashare)} ADD SCHEMA {RedshiftData.identifier(schema)};'
            self._execute_statement(sql=sql_statement)

        except Exception as e:
            allowed_error_messages = [f'ERROR: share "{datashare}" already exists']
            error_message = e.args[0]
            if error_message in allowed_error_messages:
                log.info('Datashare {0} already exists'.format(datashare))
            else:
                raise e

    def add_table_to_datashare(self, datashare: str, schema: str, table_name: str):
        fq_table_name = self.fully_qualified_table_name(schema, table_name)
        sql_statement = f"ALTER DATASHARE {RedshiftData.identifier(datashare)} ADD TABLE {fq_table_name};"
        try:
            self._execute_statement(sql_statement)
        except Exception as e:
            allowed_error_message = f"ERROR: Relation {table_name} is already added to the datashare {datashare}"
            error_message = e.args[0]
            if error_message == allowed_error_message:
                log.info("Table {0} is already present in the datashare {1}".format(fq_table_name, datashare))
            else:
                raise e

    def grant_usage_to_datashare_via_catalog(self, datashare: str, account: str):
        log.info(f'Grant usage on {datashare=} via catalog...')
        sql_statement = (
            f"GRANT USAGE ON DATASHARE {RedshiftData.identifier(datashare)} TO ACCOUNT '{account}' VIA DATA CATALOG;"
        )
        self._execute_statement(sql=sql_statement)

    # def remove_table_from_datashare(self, schema: str, database: str, workgroup: str, datashare: str, table_name: str):
    #     fq_table_name = self.fully_qualified_table_name(database, schema, table_name)
    #     sql_statement = f"ALTER DATASHARE {RedshiftData.identifier(datashare)} REMOVE TABLE {fq_table_name};"
    #     try:
    #         self._execute_statement(database, workgroup, sql_statement)
    #     except Exception as e:
    #         allowed_error_message = f"ERROR: Datashare {datashare} does not contain the Relation {table_name}"
    #         error_message = e.args[0]
    #         if error_message == allowed_error_message:
    #             log.info(f"Table {fq_table_name} does not exist on datashare {datashare}. No need to remove it any more.")
    #         else:
    #             raise e
    #
    # def drop_datashare(self, database: str, workgroup: str, datashare: str):
    #     sql_statement = f"DROP DATASHARE {RedshiftData.identifier(datashare)};"
    #     try:
    #         self._execute_statement(database, workgroup, sql_statement)
    #     except Exception as e:
    #         allowed_error_message = f"ERROR: Datashare {datashare} does not exist"
    #         error_message = e.args[0]
    #         if error_message == allowed_error_message:
    #             log.info(f"Datashare {datashare} does not exist. No need to drop it any more.")
    #         else:
    #             raise e

    # def get_desc_datashare_result(self, desc_datashare_sql_id: str) -> List[str]:
    #     get_statement_result_response = self.client.get_statement_result(Id=desc_datashare_sql_id)
    #     next_token = get_statement_result_response.get("NextToken", None)
    #     try:
    #         if "Records" in get_statement_result_response.keys():
    #             records = get_statement_result_response["Records"]
    #             while next_token:
    #                 get_statement_result_response = self.client.redshiftDataClient.get_statement_result(Id=desc_datashare_sql_id, NextToken=next_token)
    #                 if "Records" in get_statement_result_response.keys():
    #                     records.extend(get_statement_result_response["Records"])
    #                 next_token = get_statement_result_response.get("NextToken", None)
    #             filtered_records = [[d for d in record if "stringValue" in d.keys()] for record in records]
    #             # the 6th element has the table name and the 5th element has the object type i.e. table, view or schema
    #             table_list = [
    #                 [d for d in record][5]["stringValue"].split(".")[-1]
    #                 for record in filtered_records
    #                 if [d for d in record][4]["stringValue"] in ["table", "view"]
    #             ]
    #             return table_list
    #     except Exception as e:
    #         log.error(
    #             f"Failed to retrieve tables for sql_id {desc_datashare_sql_id}: {e}",
    #             exc_info=True,
    #         )
    #         raise e
    #

# TODO: This file will be replaced by using the SDK directly


def get_redshift_dataset(client, dataset_uri):
    query = {
        'operationName': 'getRedshiftDataset',
        'variables': {'datasetUri': dataset_uri},
        'query': """
            query getRedshiftDataset($datasetUri: String!) {
              getRedshiftDataset(datasetUri: $datasetUri) {
                datasetUri
                owner
                description
                label
                name
                region
                created
                imported
                userRoleForDataset
                SamlAdminGroupName
                AwsAccountId
                tags
                stewards
                topics
                confidentiality
                autoApprovalEnabled
                organization {
                  organizationUri
                  label
                }
                terms {
                  count
                  nodes {
                    __typename
                    ... on Term {
                      nodeUri
                      path
                      label
                    }
                  }
                }
                environment {
                  environmentUri
                  label
                  region
                  organization {
                    organizationUri
                    label
                  }
                }
                upvotes
                connection {
                  connectionUri
                  label
                  redshiftType
                  clusterId
                  nameSpaceId
                  workgroup
                  redshiftUser
                  secretArn
                  database
                }
                schema
              }
            }
        """,
    }
    response = client.query(query=query)
    return response.data.getRedshiftDataset


def list_redshift_dataset_tables(client, dataset_uri, term=''):
    query = {
        'operationName': 'listRedshiftDatasetTables',
        'variables': {
            'datasetUri': dataset_uri,
            'filter': {'term': term},
        },
        'query': """
            query listRedshiftDatasetTables(
              $datasetUri: String!
              $filter: RedshiftDatasetTableFilter
            ) {
              listRedshiftDatasetTables(datasetUri: $datasetUri, filter: $filter) {
                count
                page
                pages
                hasNext
                hasPrevious
                nodes {
                  rsTableUri
                  datasetUri
                  name
                  label
                  created
                  description
                }
              }
            }
        """,
    }
    response = client.query(query=query)
    return response.data.listRedshiftDatasetTables


def get_redshift_dataset_table(client, rs_table_uri):
    query = {
        'operationName': 'getRedshiftDatasetTable',
        'variables': {'rsTableUri': rs_table_uri},
        'query': """
            query getRedshiftDatasetTable($rsTableUri: String!) {
              getRedshiftDatasetTable(rsTableUri: $rsTableUri) {
                rsTableUri
                name
                label
                created
                description
                tags
                terms {
                  count
                  nodes {
                    __typename
                    ... on Term {
                      nodeUri
                      path
                      label
                    }
                  }
                }
                dataset {
                  owner
                  SamlAdminGroupName
                  datasetUri
                  name
                  label
                  userRoleForDataset
                  organization {
                    label
                  }
                  environment {
                    label
                  }
                  region
                }
              }
            }
        """,
    }
    response = client.query(query=query)
    return response.data.getRedshiftDatasetTable


def get_redshift_dataset_table_columns(client, rs_table_uri, term=''):
    query = {
        'operationName': 'getRedshiftDatasetTableColumns',
        'variables': {
            'rsTableUri': rs_table_uri,
            'filter': {'term': term},
        },
        'query': """
            query getRedshiftDatasetTableColumns(
              $rsTableUri: String!
              $filter: RedshiftDatasetTableFilter
            ) {
              getRedshiftDatasetTableColumns(rsTableUri: $rsTableUri, filter: $filter) {
                count
                page
                pages
                hasNext
                hasPrevious
                nodes {
                  columnDefault
                  label
                  length
                  name
                  nullable
                  typeName
                }
              }
            }
        """,
    }
    response = client.query(query=query)
    return response.data.getRedshiftDatasetTableColumns


def list_redshift_schema_dataset_tables(client, dataset_uri):
    query = {
        'operationName': 'listRedshiftSchemaDatasetTables',
        'variables': {'datasetUri': dataset_uri},
        'query': """
            query listRedshiftSchemaDatasetTables($datasetUri: String!) {
              listRedshiftSchemaDatasetTables(datasetUri: $datasetUri) {
                name
                type
                alreadyAdded
              }
            }
        """,
    }
    response = client.query(query=query)
    return response.data.listRedshiftSchemaDatasetTables


def import_redshift_dataset(
    client,
    label,
    org_uri,
    env_uri,
    description,
    tags,
    owner,
    topics,
    group_uri,
    confidentiality,
    auto_approval_enabled,
    connection_uri,
    schema,
    tables,
):
    mutation = {
        'operationName': 'importRedshiftDataset',
        'variables': {
            'input': {
                'label': label,
                'organizationUri': org_uri,
                'environmentUri': env_uri,
                'description': description,
                'tags': tags,
                'owner': owner,
                'topics': topics,
                'SamlAdminGroupName': group_uri,
                'confidentiality': confidentiality,
                'autoApprovalEnabled': auto_approval_enabled,
                'connectionUri': connection_uri,
                'schema': schema,
                'tables': tables,
            }
        },
        'query': """
            mutation importRedshiftDataset($input: ImportRedshiftDatasetInput) {
              importRedshiftDataset(input: $input) {
                datasetUri
                label
                userRoleForDataset
              }
            }
        """,
    }
    response = client.query(mutation=mutation)
    return response.data.importRedshiftDataset


def update_redshift_dataset(client, dataset_uri, description):
    mutation = {
        'operationName': 'updateRedshiftDataset',
        'variables': {
            'datasetUri': dataset_uri,
            'input': {'description': description},
        },
        'query': """
            mutation updateRedshiftDataset(
              $datasetUri: String!
              $input: ModifyRedshiftDatasetInput
            ) {
              updateRedshiftDataset(datasetUri: $datasetUri, input: $input) {
                datasetUri
                label
                userRoleForDataset
              }
            }
        """,
    }
    response = client.query(mutation=mutation)
    return response.data.updateRedshiftDataset


def delete_redshift_dataset(client, dataset_uri):
    mutation = {
        'operationName': 'deleteRedshiftDataset',
        'variables': {'datasetUri': dataset_uri},
        'query': """
            mutation deleteRedshiftDataset($datasetUri: String!) {
              deleteRedshiftDataset(datasetUri: $datasetUri)
            }
        """,
    }
    response = client.query(mutation=mutation)
    return response.data.deleteRedshiftDataset


def add_redshift_dataset_tables(client, dataset_uri, tables):
    mutation = {
        'operationName': 'addRedshiftDatasetTables',
        'variables': {
            'datasetUri': dataset_uri,
            'tables': tables,
        },
        'query': """
            mutation addRedshiftDatasetTables(
              $datasetUri: String!
              $tables: [String]!
            ) {
              addRedshiftDatasetTables(datasetUri: $datasetUri, tables: $tables)
            }
        """,
    }
    response = client.query(mutation=mutation)
    return response.data.addRedshiftDatasetTables


def delete_redshift_dataset_table(client, rs_table_uri):
    mutation = {
        'operationName': 'deleteRedshiftDatasetTable',
        'variables': {'rsTableUri': rs_table_uri},
        'query': """
            mutation deleteRedshiftDatasetTable($rsTableUri: String!) {
              deleteRedshiftDatasetTable(rsTableUri: $rsTableUri)
            }
        """,
    }
    response = client.query(mutation=mutation)
    return response.data.deleteRedshiftDatasetTable


def update_redshift_dataset_table(client, rs_table_uri, description):
    mutation = {
        'operationName': 'updateRedshiftDatasetTable',
        'variables': {
            'rsTableUri': rs_table_uri,
            'input': {'description': description},
        },
        'query': """
            mutation updateRedshiftDatasetTable(
              $rsTableUri: String!
              $input: ModifyRedshiftDatasetInput
            ) {
              updateRedshiftDatasetTable(rsTableUri: $rsTableUri, input: $input) {
                rsTableUri
                label
              }
            }
        """,
    }
    response = client.query(mutation=mutation)
    return response.data.updateRedshiftDatasetTable

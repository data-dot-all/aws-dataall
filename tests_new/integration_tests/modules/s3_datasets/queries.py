# TODO: This file will be replaced by using the SDK directly

S3_DATASET_TYPE = """
datasetUri
label
name
description
tags
owner
created
updated
admins
AwsAccountId
region
S3BucketName
GlueDatabaseName
GlueCrawlerName
GlueCrawlerSchedule
GlueProfilingJobName
GlueProfilingTriggerSchedule
IAMDatasetAdminRoleArn
KmsAlias
SamlAdminGroupName
businessOwnerEmail
businessOwnerDelegationEmails
importedS3Bucket
importedGlueDatabase
importedKmsKey
importedAdminRole
imported
environment { 
  environmentUri
  label
  AwsAccountId
  region
}
organization { 
  organizationUri
  label
}
owners
stewards
userRoleForDataset
userRoleInEnvironment
statistics { 
  tables
  locations
  upvotes
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
topics
confidentiality
language
stack { 
  stack
  status
  stackUri
  targetUri
  accountid
  region
  stackid
  link
  outputs
  resources
}
autoApprovalEnabled
"""

S3_DATASET_TABLE_FILTER_TYPE = """
filterUri
tableUri
label
description
filterType
includedCols
rowExpression
"""


## Dataset Queries/Mutations
def create_dataset(
    client,
    name,
    owner,
    group,
    organizationUri,
    environmentUri,
    tags,
    autoApprovalEnabled=False,
    confidentiality=None,
):
    query = {
        'operationName': 'CreateDataset',
        'variables': {
            'input': {
                'owner': owner,
                'label': name,
                'description': 'Created for integration testing',
                'tags': tags,
                'topics': ['Sites'],
                'environmentUri': environmentUri,
                'SamlAdminGroupName': group,
                'organizationUri': organizationUri,
                'confidentiality': confidentiality or 'Unclassified',
                'autoApprovalEnabled': autoApprovalEnabled,
            }
        },
        'query': f"""
                    mutation CreateDataset($input: NewDatasetInput!) {{
                      createDataset(input: $input) {{
                        {S3_DATASET_TYPE}
                      }}
                    }}
                """,
    }
    response = client.query(query=query)
    return response.data.createDataset


def import_dataset(
    client,
    name,
    owner,
    group,
    organizationUri,
    environmentUri,
    tags,
    bucketName,
    KmsKeyAlias='',
    glueDatabaseName='',
    autoApprovalEnabled=False,
    confidentiality=None,
):
    query = {
        'operationName': 'ImportDataset',
        'variables': {
            'input': {
                'owner': owner,
                'label': name,
                'description': 'Created for integration testing',
                'tags': tags,
                'environmentUri': environmentUri,
                'SamlAdminGroupName': group,
                'organizationUri': organizationUri,
                'confidentiality': confidentiality or 'Unclassified',
                'autoApprovalEnabled': autoApprovalEnabled,
                'bucketName': bucketName,
                'KmsKeyAlias': KmsKeyAlias,
                'glueDatabaseName': glueDatabaseName,
            }
        },
        'query': f"""
                    mutation ImportDataset($input: ImportDatasetInput) {{
                      importDataset(input: $input) {{
                        {S3_DATASET_TYPE}
                      }}
                    }}
                """,
    }
    response = client.query(query=query)
    return response.data.importDataset


def delete_dataset(client, datasetUri, deleteFromAws=True):
    query = {
        'operationName': 'deleteDataset',
        'variables': {'datasetUri': datasetUri, 'deleteFromAWS': deleteFromAws},
        'query': f"""
                mutation deleteDataset($datasetUri: String!, $deleteFromAWS: Boolean) {{
                  deleteDataset(datasetUri: $datasetUri, deleteFromAWS: $deleteFromAWS)
                }}
                """,
    }
    response = client.query(query=query)
    return response.data.deleteDataset


def update_dataset(client, datasetUri, input: dict):
    query = {
        'operationName': 'UpdateDataset',
        'variables': {'datasetUri': datasetUri, 'input': input},
        'query': f"""
                    mutation UpdateDataset($datasetUri: String, $input: ModifyDatasetInput) {{
                      updateDataset(datasetUri: $datasetUri, input: $input) {{
                        {S3_DATASET_TYPE}
                      }}
                    }}
                """,
    }
    response = client.query(query=query)
    return response.data.updateDataset


def get_dataset(client, datasetUri):
    query = {
        'operationName': 'GetDataset',
        'variables': {'datasetUri': datasetUri},
        'query': f"""
                    query GetDataset($datasetUri: String!) {{
                      getDataset(datasetUri: $datasetUri) {{
                        {S3_DATASET_TYPE}
                      }}
                    }}
                """,
    }
    response = client.query(query=query)
    return response.data.getDataset


def get_dataset_assume_role_url(client, datasetUri):
    query = {
        'operationName': 'GetDatasetAssumeRoleUrl',
        'variables': {'datasetUri': datasetUri},
        'query': f"""
                    query GetDatasetAssumeRoleUrl($datasetUri: String!) {{
                      getDatasetAssumeRoleUrl(datasetUri: $datasetUri)
                    }}
                """,
    }
    response = client.query(query=query)
    return response.data.getDatasetAssumeRoleUrl


def generate_dataset_access_token(client, datasetUri):
    query = {
        'operationName': 'GenerateDatasetAccessToken',
        'variables': {'datasetUri': datasetUri},
        'query': f"""
                    mutation GenerateDatasetAccessToken($datasetUri: String!) {{
                      generateDatasetAccessToken(datasetUri: $datasetUri)
                    }}
                """,
    }
    response = client.query(query=query)
    return response.data.generateDatasetAccessToken


def get_dataset_presigned_role_url(client, datasetUri, input):
    query = {
        'operationName': 'GetDatasetPresignedUrl',
        'variables': {'datasetUri': datasetUri, 'input': input},
        'query': f"""
                    query GetDatasetPresignedUrl(
                      $datasetUri: String!
                      $input: DatasetPresignedUrlInput
                    ) {{
                      getDatasetPresignedUrl(datasetUri: $datasetUri, input: $input)
                    }}
                """,
    }
    response = client.query(query=query)
    return response.data.getDatasetPresignedUrl


def start_glue_crawler(client, datasetUri, input):
    query = {
        'operationName': 'StartGlueCrawler',
        'variables': {'datasetUri': datasetUri, 'input': input},
        'query': f"""
                    mutation StartGlueCrawler($datasetUri: String, $input: CrawlerInput) {{
                      startGlueCrawler(datasetUri: $datasetUri, input: $input) {{
                        Name
                        AwsAccountId
                        region
                        status
                      }}
                    }}
                """,
    }
    response = client.query(query=query)
    return response.data.startGlueCrawler


def list_s3_datasets_owned_by_env_group(client, environment_uri, group_uri, term):
    query = {
        'operationName': 'listS3DatasetsOwnedByEnvGroup',
        'variables': {'environmentUri': environment_uri, 'groupUri': group_uri, 'filter': {'term': term}},
        'query': f"""
                query listS3DatasetsOwnedByEnvGroup(
                  $filter: DatasetFilter
                  $environmentUri: String!
                  $groupUri: String!
                ) {{
                  listS3DatasetsOwnedByEnvGroup(
                    environmentUri: $environmentUri
                    groupUri: $groupUri
                    filter: $filter
                  ) {{
                    count
                    page
                    pages
                    hasNext
                    hasPrevious
                    nodes {{
                      datasetUri
                      label
                      AwsAccountId
                      region
                      GlueDatabaseName
                      SamlAdminGroupName
                      name
                      S3BucketName
                      created
                      owner
                      stack {{
                        status
                      }}
                    }}
                  }}
                }}
                """,
    }
    response = client.query(query=query)
    return response.data.listS3DatasetsOwnedByEnvGroup


## Folders Queries/Mutations
def create_folder(client, datasetUri, input):
    query = {
        'operationName': 'CreateDatasetStorageLocation',
        'variables': {'datasetUri': datasetUri, 'input': input},
        'query': f"""
                    mutation CreateDatasetStorageLocation($datasetUri: String!, $input: NewDatasetStorageLocationInput) {{
                      createDatasetStorageLocation(datasetUri: $datasetUri, input: $input) {{
                        locationUri
                        S3Prefix
                        label
                      }}
                    }}
                """,
    }
    response = client.query(query=query)
    return response.data.createDatasetStorageLocation


def delete_folder(client, locationUri):
    query = {
        'operationName': 'DeleteDatasetStorageLocation',
        'variables': {'locationUri': locationUri},
        'query': f"""
                    mutation DeleteDatasetStorageLocation($locationUri: String!) {{
                      deleteDatasetStorageLocation(locationUri: $locationUri)
                    }}
                """,
    }
    response = client.query(query=query)
    return response.data.deleteDatasetStorageLocation


def update_folder(client, locationUri, input):
    query = {
        'operationName': 'updateDatasetStorageLocation',
        'variables': {'locationUri': locationUri, 'input': input},
        'query': f"""
                    mutation updateDatasetStorageLocation($locationUri: String!, $input: ModifyDatasetStorageLocationInput!) {{
                      updateDatasetStorageLocation(locationUri: $locationUri, input: $input) {{
                        locationUri
                        S3Prefix
                        label
                      }}
                    }}
                """,
    }
    response = client.query(query=query)
    return response.data.updateDatasetStorageLocation


def get_folder(client, locationUri):
    query = {
        'operationName': 'getDatasetStorageLocation',
        'variables': {'locationUri': locationUri},
        'query': f"""
                    query getDatasetStorageLocation($locationUri: String!) {{
                      getDatasetStorageLocation(locationUri: $locationUri) {{
                        locationUri
                        label
                        S3Prefix 
                      }}
                    }}
                """,
    }
    response = client.query(query=query)
    return response.data.getDatasetStorageLocation


## Tables Queries/Mutations


def update_dataset_table(client, tableUri, input):
    query = {
        'operationName': 'UpdateDatasetTable',
        'variables': {'tableUri': tableUri, 'input': input},
        'query': f"""
                mutation UpdateDatasetTable(
                  $tableUri: String!
                  $input: ModifyDatasetTableInput!
                ) {{
                  updateDatasetTable(tableUri: $tableUri, input: $input) {{
                    tableUri
                    label
                  }}
                }}
                """,
    }
    response = client.query(query=query)
    return response.data.updateDatasetTable


def delete_table(client, tableUri):
    query = {
        'operationName': 'deleteDatasetTable',
        'variables': {'tableUri': tableUri},
        'query': f"""
                    mutation deleteDatasetTable($tableUri: String!) {{
                      deleteDatasetTable(tableUri: $tableUri)
                    }}
                """,
    }
    response = client.query(query=query)
    return response.data.deleteDatasetTable


def sync_tables(client, datasetUri):
    query = {
        'operationName': 'SyncTables',
        'variables': {'datasetUri': datasetUri},
        'query': f"""
                    mutation SyncTables($datasetUri: String!) {{
                      syncTables(datasetUri: $datasetUri) {{
                        count
                        nodes {{
                          tableUri
                          GlueTableName
                          GlueDatabaseName
                          description
                          name
                          label
                          created
                          S3Prefix
                          dataset {{
                            datasetUri
                            name
                            GlueDatabaseName
                            userRoleForDataset
                          }}
                        }}
                      }}
                    }}
                """,
    }
    response = client.query(query=query)
    return response.data.syncTables


def create_table_data_filter(client, tableUri, input):
    query = {
        'operationName': 'createTableDataFilter',
        'variables': {'tableUri': tableUri, 'input': input},
        'query': f"""
                mutation createTableDataFilter($tableUri: String!,$input: NewTableDataFilterInput!) {{
                  createTableDataFilter(tableUri: $tableUri, input: $input) {{
                      {S3_DATASET_TABLE_FILTER_TYPE}
                  }}
                }}
                """,
    }
    response = client.query(query=query)
    return response.data.createTableDataFilter


def delete_table_data_filter(client, filterUri):
    query = {
        'operationName': 'deleteTableDataFilter',
        'variables': {'filterUri': filterUri},
        'query': f"""
                mutation deleteTableDataFilter($filterUri: String!) {{
                  deleteTableDataFilter(filterUri: $filterUri)
                }}
            """,
    }
    response = client.query(query=query)
    return response.data.deleteTableDataFilter


def get_dataset_table(client, tableUri):
    query = {
        'operationName': 'GetDatasetTable',
        'variables': {'tableUri': tableUri},
        'query': f"""
            query GetDatasetTable($tableUri: String!) {{
                getDatasetTable(tableUri: $tableUri) {{
                    datasetUri
                    owner
                    description
                    created
                    tags
                    tableUri
                    AwsAccountId
                    GlueTableName
                    GlueDatabaseName
                    LastGlueTableStatus
                    label
                    name
                    S3Prefix
              }}
            }}
            """,
    }
    response = client.query(query=query)
    return response.data.getDatasetTable


def list_dataset_tables(client, datasetUri):
    query = {
        'operationName': 'GetDataset',
        'variables': {'datasetUri': datasetUri, 'filter': {}},
        'query': f"""
                        query GetDataset($datasetUri: String!) {{
                          getDataset(datasetUri: $datasetUri) {{
                            {S3_DATASET_TYPE}
                            tables {{
                              count
                              nodes {{
                                GlueTableName
                              }}
                            }}
                          }}
                        }}
                    """,
    }
    response = client.query(query=query)
    return response.data.getDataset


def preview_table(client, tableUri):
    query = {
        'operationName': 'PreviewTable',
        'variables': {'tableUri': tableUri},
        'query': f"""
                    query PreviewTable($tableUri: String!) {{
                      previewTable(tableUri: $tableUri) {{
                        rows
                        fields
                      }}
                    }}
                """,
    }
    response = client.query(query=query)
    return response.data.previewTable


def list_table_data_filters(client, tableUri):
    query = {
        'operationName': 'listTableDataFilters',
        'variables': {'tableUri': tableUri, 'filter': {}},
        'query': f"""
                query listTableDataFilters(
                  $tableUri: String!
                  $filter: DatasetTableFilter
                ) {{
                  listTableDataFilters(tableUri: $tableUri, filter: $filter) {{
                    count
                    page
                    pages
                    hasNext
                    hasPrevious
                    nodes {{
                      {S3_DATASET_TABLE_FILTER_TYPE}
                    }}
                  }}
                }}
            """,
    }
    response = client.query(query=query)
    return response.data.listTableDataFilters


## Table Column Queries/Mutations
def sync_dataset_table_columns(client, tableUri):
    query = {
        'operationName': 'SyncDatasetTableColumns',
        'variables': {'tableUri': tableUri},
        'query': f"""
            mutation SyncDatasetTableColumns($tableUri: String!) {{
              syncDatasetTableColumns(tableUri: $tableUri) {{
                count
                page
                pages
                hasNext
                hasPrevious
                nodes {{
                  columnUri
                  name
                  description
                  typeName
                }}
              }}
            }}
                """,
    }
    response = client.query(query=query)
    return response.data.syncDatasetTableColumns


def update_dataset_table_column(client, columnUri, input):
    query = {
        'operationName': 'updateDatasetTableColumn',
        'variables': {'columnUri': columnUri, 'input': input},
        'query': f"""
            mutation updateDatasetTableColumn(
              $columnUri: String!
              $input: DatasetTableColumnInput
            ) {{
              updateDatasetTableColumn(columnUri: $columnUri, input: $input) {{
                columnUri
                description
              }}
            }}
                """,
    }
    response = client.query(query=query)
    return response.data.updateDatasetTableColumn


def list_dataset_table_columns(client, tableUri, term=''):
    query = {
        'operationName': 'ListDatasetTableColumns',
        'variables': {'tableUri': tableUri, 'filter': {'term': term}},
        'query': f"""
            query ListDatasetTableColumns(
      $tableUri: String!
      $filter: DatasetTableColumnFilter
    ) {{
      listDatasetTableColumns(tableUri: $tableUri, filter: $filter) {{
        count
        page
        pages
        hasNext
        hasPrevious
        nodes {{
          columnUri
          name
          label
          description
          typeName
          columnType
          terms {{
            count
            page
            pages
            nodes {{
              linkUri
              term {{
                label
                created
                path
                nodeUri
              }}
            }}
          }}
        }}
      }}
    }}
                """,
    }
    response = client.query(query=query)
    return response.data.listDatasetTableColumns


## Profiling Queries/Mutations
def start_dataset_profiling_run(client, input):
    query = {
        'operationName': 'startDatasetProfilingRun',
        'variables': {'input': input},
        'query': f"""
                    mutation startDatasetProfilingRun($input: StartDatasetProfilingRunInput!) {{
                      startDatasetProfilingRun(input: $input) {{
                        profilingRunUri
                        datasetUri
                        status
                        GlueTableName
                      }}
                    }}
                """,
    }
    response = client.query(query=query)
    return response.data.startDatasetProfilingRun


def list_table_profiling_runs(client, tableUri):
    query = {
        'operationName': 'listDatasetTableProfilingRuns',
        'variables': {'tableUri': tableUri},
        'query': f"""
                        query listDatasetTableProfilingRuns($tableUri: String!) {{
      listDatasetTableProfilingRuns(tableUri: $tableUri) {{
        count
        page
        pages
        hasNext
        hasPrevious
        nodes {{
          profilingRunUri
          GlueJobRunId
          GlueTableName
          results
          created
          status
        }}
      }}
    }}
                """,
    }
    response = client.query(query=query)
    return response.data.listDatasetTableProfilingRuns


def get_table_profiling_run(client, tableUri):
    query = {
        'operationName': 'getDatasetTableProfilingRun',
        'variables': {'tableUri': tableUri},
        'query': f"""
                        query getDatasetTableProfilingRun($tableUri: String!) {{
      getDatasetTableProfilingRun(tableUri: $tableUri) {{
        profilingRunUri
        status
        GlueTableName
        datasetUri
        GlueJobName
        GlueJobRunId
        GlueTriggerSchedule
        GlueTriggerName
        GlueTableName
        AwsAccountId
        results
      }}
    }}
                """,
    }
    response = client.query(query=query)
    return response.data.getDatasetTableProfilingRun


def list_s3_object_keys(client, datasetUri):
    query = {
        'operationName': 'listS3ObjectKeys',
        'variables': {'datasetUri': datasetUri},
        'query': """
            query listS3ObjectKeys($datasetUri: String!) {
              listS3ObjectKeys(datasetUri: $datasetUri)
            }
                """,
    }
    response = client.query(query=query)
    return response.data.listS3ObjectKeys

# TODO: This file will be replaced by using the SDK directly


def create_worksheet(client, name, group, tags=[]):
    query = {
        'operationName': 'CreateWorksheet',
        'variables': {
            'input': {
                'label': name,
                'SamlAdminGroupName': group,
                'description': 'Created for integration testing',
                'tags': tags,
            }
        },
        'query': """
            mutation CreateWorksheet($input: NewWorksheetInput) {
              createWorksheet(input: $input) {
                worksheetUri
                label
                created
              }
            }
                """,
    }
    response = client.query(query=query)
    return response.data.createWorksheet


def delete_worksheet(client, worksheet_uri):
    query = {
        'operationName': 'deleteWorksheet',
        'variables': {'worksheetUri': worksheet_uri},
        'query': """
            mutation deleteWorksheet($worksheetUri: String!) {
              deleteWorksheet(worksheetUri: $worksheetUri)
            }
        """,
    }
    response = client.query(query=query)
    return response.data.deleteWorksheet


def get_worksheet(client, worksheet_uri):
    query = {
        'operationName': 'GetWorksheet',
        'variables': {'worksheetUri': worksheet_uri},
        'query': """
            query GetWorksheet($worksheetUri: String!) {
                  getWorksheet(worksheetUri: $worksheetUri) {
                    worksheetUri
                    label
                    description
                    SamlAdminGroupName
                    tags
                    sqlBody
                    chartConfig {
                      dimensions {
                        columnName
                      }
                      measures {
                        columnName
                        aggregationName
                      }
                    }
                    owner
                    created
                    updated
                    userRoleForWorksheet
                    lastSavedQueryResult {
                      AthenaQueryId
                      ElapsedTimeInMs
                      Error
                      DataScannedInBytes
                      Status
                      columns {
                        columnName
                        typeName
                      }
                      rows {
                        cells {
                          value
                          columnName
                        }
                      }
                    }
                  }
                }
            """,
    }
    response = client.query(query=query)
    return response.data.getWorksheet


def list_worksheets(client, term=''):
    query = {
        'operationName': 'ListWorksheets',
        'variables': {'filter': {'page': 1, 'pageSize': 10, 'term': term}},
        'query': """
            query ListWorksheets($filter: WorksheetFilter) {
              listWorksheets(filter: $filter) {
                count
                page
                pages
                hasNext
                hasPrevious
                nodes {
                  worksheetUri
                  label
                  description
                  tags
                  owner
                  created
                  userRoleForWorksheet
                  SamlAdminGroupName
                }
              }
            }
        """,
    }
    response = client.query(query=query)
    return response.data.listWorksheets


def run_athena_sql_query(client, query, environment_uri, worksheet_uri):
    query = {
        'operationName': 'runAthenaSqlQuery',
        'variables': {'sqlQuery': query, 'environmentUri': environment_uri, 'worksheetUri': worksheet_uri},
        'query': """
                query runAthenaSqlQuery(
                      $environmentUri: String!
                      $worksheetUri: String!
                      $sqlQuery: String!
                    ) {
                      runAthenaSqlQuery(
                        environmentUri: $environmentUri
                        worksheetUri: $worksheetUri
                        sqlQuery: $sqlQuery
                      ) {
                        rows {
                          cells {
                            columnName
                            typeName
                            value
                          }
                        }
                        columns {
                          columnName
                          typeName
                        }
                      }
                    }
                """,
    }
    response = client.query(query=query)
    return response.data.runAthenaSqlQuery


def update_worksheet(client, worksheet_uri, name='', description='', tags=[]):
    query = {
        'operationName': 'UpdateWorksheet',
        'variables': {
            'worksheetUri': worksheet_uri,
            'input': {
                'label': name,
                'description': description,
                'tags': tags,
            },
        },
        'query': """
            mutation UpdateWorksheet(
                  $worksheetUri: String!
                  $input: UpdateWorksheetInput
                ) {
                  updateWorksheet(worksheetUri: $worksheetUri, input: $input) {
                    worksheetUri
                    label
                    created
                    description
                  }
                }
            """,
    }
    response = client.query(query=query)
    return response.data.updateWorksheet


def text_to_sql(client, prompt, environment_uri, worksheet_uri, database_name, table_names=[]):
    query = {
        'operationName': 'textToSQL',
        'variables': {
            'prompt': prompt,
            'environmentUri': environment_uri,
            'worksheetUri': worksheet_uri,
            'databaseName': database_name,
            'tableNames': table_names,
        },
        'query': """
            query textToSQL(
                  $prompt: String!
                  $environmentUri: String!
                  $worksheetUri: String!
                  $databaseName: String!
                  $tableNames: [String]
                ) {
                  textToSQL(
                    prompt: $prompt
                    environmentUri: $environmentUri
                    worksheetUri: $worksheetUri
                    databaseName: $databaseName
                    tableNames: $tableNames
                  )
                }
            """,
    }
    response = client.query(query=query)
    return response.data.textToSQL


def analyze_text_document(client, prompt, environment_uri, worksheet_uri, dataset_uri, key):
    query = {
        'operationName': 'analyzeTextDocument',
        'variables': {
            'prompt': prompt,
            'environmentUri': environment_uri,
            'worksheetUri': worksheet_uri,
            'datasetUri': dataset_uri,
            'key': key,
        },
        'query': """
            query analyzeTextDocument(
                  $prompt: String!
                  $environmentUri: String!
                  $worksheetUri: String!
                  $datasetUri: String!
                  $key: String!
                ) {
                  analyzeTextDocument(
                    prompt: $prompt
                    environmentUri: $environmentUri
                    worksheetUri: $worksheetUri
                    datasetUri: $datasetUri
                    key: $key
                  )
                }
            """,
    }
    response = client.query(query=query)
    return response.data.analyzeTextDocument

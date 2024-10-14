from dataall.base.api import gql
from dataall.modules.worksheets.api.resolvers import (
    get_worksheet,
    list_worksheets,
    run_sql_query,
    text_to_sql,
    unstruct_query,
)


getWorksheet = gql.QueryField(
    name='getWorksheet',
    type=gql.Ref('Worksheet'),
    resolver=get_worksheet,
    args=[gql.Argument(name='worksheetUri', type=gql.NonNullableType(gql.String))],
)


listWorksheets = gql.QueryField(
    name='listWorksheets',
    resolver=list_worksheets,
    args=[gql.Argument(name='filter', type=gql.Ref('WorksheetFilter'))],
    type=gql.Ref('Worksheets'),
)


runAthenaSqlQuery = gql.QueryField(
    name='runAthenaSqlQuery',
    type=gql.Ref('AthenaQueryResult'),
    args=[
        gql.Argument(name='environmentUri', type=gql.NonNullableType(gql.String)),
        gql.Argument(name='worksheetUri', type=gql.NonNullableType(gql.String)),
        gql.Argument(name='sqlQuery', type=gql.NonNullableType(gql.String)),
    ],
    resolver=run_sql_query,
)

TextToSQL = gql.QueryField(
    name='textToSQL',
    type=gql.Ref('TextToSQLResult'),
    args=[
        gql.Argument(name='environmentUri', type=gql.NonNullableType(gql.String)),
        gql.Argument(name='worksheetUri', type=gql.NonNullableType(gql.String)),
        gql.Argument(name='prompt', type=gql.NonNullableType(gql.String)),
        gql.Argument(name='datasetUri', type=gql.NonNullableType(gql.String)),
        gql.Argument(name='tableNames', type=gql.String),
    ],
    resolver=text_to_sql,
)

unstructuredQuery = gql.QueryField(
    name='unstructuredQuery',
    type=gql.Ref('UnstructuredQueryResult'),
    args=[
        gql.Argument(name='environmentUri', type=gql.NonNullableType(gql.String)),
        gql.Argument(name='worksheetUri', type=gql.NonNullableType(gql.String)),
        gql.Argument(name='prompt', type=gql.NonNullableType(gql.String)),
        gql.Argument(name='datasetUri', type=gql.NonNullableType(gql.String)),
        gql.Argument(name='key', type=gql.NonNullableType(gql.String)),
    ],
    resolver=unstruct_query,
)

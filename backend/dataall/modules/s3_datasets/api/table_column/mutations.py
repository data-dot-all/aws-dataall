from dataall.base.api import gql
from dataall.modules.s3_datasets.api.table_column.resolvers import (
    sync_table_columns,
    update_table_column,
    batch_update_table_columns_description,
)

syncDatasetTableColumns = gql.MutationField(
    name='syncDatasetTableColumns',
    args=[gql.Argument(name='tableUri', type=gql.NonNullableType(gql.String))],
    type=gql.Ref('DatasetTableColumnSearchResult'),
    resolver=sync_table_columns,
)


updateDatasetTableColumn = gql.MutationField(
    name='updateDatasetTableColumn',
    args=[
        gql.Argument(name='columnUri', type=gql.String),
        gql.Argument(name='input', type=gql.Ref('DatasetTableColumnInput')),
    ],
    type=gql.Ref('DatasetTableColumn'),
    resolver=update_table_column,
)
batchUpdateDatasetTableColumn = gql.MutationField(
    name='batchUpdateDatasetTableColumn',
    args=[gql.Argument(name='columns', type=gql.ArrayType(gql.Ref('SubitemDescriptionInput')))],
    type=gql.String,
    resolver=batch_update_table_columns_description,
)

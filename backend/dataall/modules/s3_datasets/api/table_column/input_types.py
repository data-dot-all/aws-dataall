from dataall.base.api import gql

DatasetTableColumnFilter = gql.InputType(
    name='DatasetTableColumnFilter',
    arguments=[
        gql.Argument('term', gql.String),
        gql.Argument('page', gql.Integer),
        gql.Argument('pageSize', gql.Integer),
    ],
)

DatasetTableColumnInput = gql.InputType(
    name='DatasetTableColumnInput',
    arguments=[
        gql.Argument('description', gql.String),
        gql.Argument('classification', gql.Integer),
        gql.Argument('tags', gql.Integer),
        gql.Argument('topics', gql.Integer),
    ],
)
SubitemDescription = gql.InputType(
    name='SubitemDescriptionInput',
    arguments=[
        gql.Argument(name='label', type=gql.String),
        gql.Argument(name='description', type=gql.String),
        gql.Argument(name='subitem_id', type=gql.String),
    ],
)

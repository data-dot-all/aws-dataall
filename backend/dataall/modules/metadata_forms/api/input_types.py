from dataall.base.api import gql

NewMetadataFormInput = gql.InputType(
    name='NewMetadataFormInput',
    arguments=[
        gql.Field(name='name', type=gql.NonNullableType(gql.String)),
        gql.Field(name='description', type=gql.String),
        gql.Field(name='SamlGroupName', type=gql.NonNullableType(gql.String)),
        gql.Field(name='visibility', type=gql.NonNullableType(gql.String)),
        gql.Field(name='homeEntity', type=gql.String),
    ],
)

NewMetadataFormFieldInput = gql.InputType(
    name='NewMetadataFormFieldInput',
    arguments=[
        gql.Field(name='name', type=gql.NonNullableType(gql.String)),
        gql.Field(name='type', type=gql.NonNullableType(gql.String)),
        gql.Field(name='displayNumber', type=gql.NonNullableType(gql.Integer)),
        gql.Field(name='description', type=gql.String),
        gql.Field(name='required', type=gql.Boolean),
        gql.Field(name='glossaryNodeUri', type=gql.String),
        gql.Field(name='possibleValues', type=gql.ArrayType(gql.String)),
    ],
)

MetadataFormFieldUpdateInput = gql.InputType(
    name='MetadataFormFieldUpdateInput',
    arguments=[
        gql.Field(name='uri', type=gql.String),
        gql.Field(name='metadataFormUri', type=gql.String),
        gql.Field(name='displayNumber', type=gql.NonNullableType(gql.Integer)),
        gql.Field(name='deleted', type=gql.Boolean),
        gql.Field(name='name', type=gql.String),
        gql.Field(name='description', type=gql.String),
        gql.Field(name='type', type=gql.String),
        gql.Field(name='required', type=gql.Boolean),
        gql.Field(name='glossaryNodeUri', type=gql.String),
        gql.Field(name='possibleValues', type=gql.ArrayType(gql.String)),
    ],
)

MetadataFormFilter = gql.InputType(
    name='MetadataFormFilter',
    arguments=[
        gql.Argument('page', gql.Integer),
        gql.Argument('search_input', gql.String),
        gql.Argument('pageSize', gql.Integer),
        gql.Argument('entityType', gql.String),
        gql.Argument('entityUri', gql.String),
        gql.Argument('hideAttached', gql.Boolean),
    ],
)

AttachedMetadataFormFilter = gql.InputType(
    name='AttachedMetadataFormFilter',
    arguments=[
        gql.Argument('page', gql.Integer),
        gql.Argument('search_input', gql.String),
        gql.Argument('pageSize', gql.Integer),
        gql.Argument('entityType', gql.String),
        gql.Argument('entityUri', gql.String),
        gql.Argument('metadataFormUri', gql.String),
    ],
)

NewAttachedMetadataFormInput = gql.InputType(
    name='NewAttachedMetadataFormInput',
    arguments=[
        gql.Field(name='entityType', type=gql.NonNullableType(gql.String)),
        gql.Field(name='entityUri', type=gql.NonNullableType(gql.String)),
        gql.Field(name='attachedUri', type=gql.String),
        gql.Field(name='fields', type=gql.ArrayType(gql.Ref('NewAttachedMetadataFormFieldInput'))),
    ],
)

NewAttachedMetadataFormFieldInput = gql.InputType(
    name='NewAttachedMetadataFormFieldInput',
    arguments=[
        gql.Field(name='fieldUri', type=gql.NonNullableType(gql.String)),
        gql.Field(name='value', type=gql.String),
    ],
)

NewMetadataFormEnforcementInput = gql.InputType(
    name='NewMetadataFormEnforcementInput',
    arguments=[
        gql.Field(name='metadataFormUri', type=gql.NonNullableType(gql.String)),
        gql.Field(name='level', type=gql.NonNullableType(gql.String)),
        gql.Field(name='homeEntity', type=gql.String),
        gql.Field(name='severity', type=gql.String),
        gql.Field(name='entityTypes', type=gql.ArrayType(gql.String)),
    ],
)

AffectedEntityFilter = gql.InputType(
    name='AffectedEntityFilter',
    arguments=[
        gql.Argument('page', gql.Integer),
        gql.Argument('pageSize', gql.Integer),
    ],
)

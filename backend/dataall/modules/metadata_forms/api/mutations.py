from dataall.base.api import gql
from dataall.modules.metadata_forms.api.resolvers import (
    create_metadata_form,
    delete_metadata_form,
    create_metadata_form_field,
)

createMetadataForm = gql.MutationField(
    name='createMetadataForm',
    args=[gql.Argument(name='input', type=gql.NonNullableType(gql.Ref('NewMetadataFormInput')))],
    type=gql.Ref('MetadataForm'),
    resolver=create_metadata_form,
    test_scope='MetadataForm',
)

deleteMetadataForm = gql.MutationField(
    name='deleteMetadataForm',
    args=[
        gql.Argument(name='formUri', type=gql.NonNullableType(gql.String)),
    ],
    type=gql.Boolean,
    resolver=delete_metadata_form,
    test_scope='MetadataForm',
)

createMetadataFormField = gql.MutationField(
    name='createMetadataFormField',
    args=[
        gql.Argument(name='formUri', type=gql.NonNullableType(gql.String)),
        gql.Argument(name='input', type=gql.NonNullableType(gql.Ref('NewMetadataFormFieldInput'))),
    ],
    type=gql.Ref('MetadataFormField'),
    resolver=create_metadata_form_field,
    test_scope='MetadataForm',
)

from dataall.base.api import gql
from dataall.modules.metadata_forms.api.resolvers import (
    create_metadata_form,
    delete_metadata_form,
    create_metadata_form_fields,
    delete_metadata_form_field,
    batch_metadata_form_field_update,
    create_attached_metadata_form,
    delete_attached_metadata_form,
    create_metadata_form_version,
    delete_metadata_form_version,
    create_mf_enforcement_rule,
    delete_mf_enforcement_rule,
)

createMetadataForm = gql.MutationField(
    name='createMetadataForm',
    args=[gql.Argument(name='input', type=gql.NonNullableType(gql.Ref('NewMetadataFormInput')))],
    type=gql.Ref('MetadataForm'),
    resolver=create_metadata_form,
    test_scope='MetadataForm',
)

createMetadataFormVersion = gql.MutationField(
    name='createMetadataFormVersion',
    args=[
        gql.Argument(name='formUri', type=gql.NonNullableType(gql.String)),
        gql.Argument(name='copyVersion', type=gql.Integer),
    ],
    type=gql.Integer,
    resolver=create_metadata_form_version,
    test_scope='MetadataForm',
)

createAttachedMetadataForm = gql.MutationField(
    name='createAttachedMetadataForm',
    args=[
        gql.Argument(name='formUri', type=gql.NonNullableType(gql.String)),
        gql.Argument(name='input', type=gql.NonNullableType(gql.Ref('NewAttachedMetadataFormInput'))),
    ],
    type=gql.Ref('AttachedMetadataForm'),
    resolver=create_attached_metadata_form,
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

deleteMetadataFormVersion = gql.MutationField(
    name='deleteMetadataFormVersion',
    args=[
        gql.Argument(name='formUri', type=gql.NonNullableType(gql.String)),
        gql.Argument(name='version', type=gql.Integer),
    ],
    type=gql.Integer,
    resolver=delete_metadata_form_version,
    test_scope='MetadataForm',
)

deleteAttachedMetadataForm = gql.MutationField(
    name='deleteAttachedMetadataForm',
    args=[
        gql.Argument(name='attachedFormUri', type=gql.NonNullableType(gql.String)),
    ],
    type=gql.Boolean,
    resolver=delete_attached_metadata_form,
    test_scope='MetadataForm',
)


createMetadataFormFields = gql.MutationField(
    name='createMetadataFormFields',
    args=[
        gql.Argument(name='formUri', type=gql.NonNullableType(gql.String)),
        gql.Argument(name='input', type=gql.ArrayType(gql.Ref('NewMetadataFormFieldInput'))),
    ],
    type=gql.ArrayType(gql.Ref('MetadataFormField')),
    resolver=create_metadata_form_fields,
    test_scope='MetadataForm',
)

deleteMetadataFormField = gql.MutationField(
    name='deleteMetadataFormField',
    args=[
        gql.Argument(name='formUri', type=gql.NonNullableType(gql.String)),
        gql.Argument(name='fieldUri', type=gql.NonNullableType(gql.String)),
    ],
    type=gql.Boolean,
    resolver=delete_metadata_form_field,
    test_scope='MetadataForm',
)

batchMetadataFormFieldUpdates = gql.MutationField(
    name='batchMetadataFormFieldUpdates',
    args=[
        gql.Argument(name='formUri', type=gql.NonNullableType(gql.String)),
        gql.Argument(name='input', type=gql.ArrayType(gql.Ref('MetadataFormFieldUpdateInput'))),
    ],
    type=gql.ArrayType(gql.Ref('MetadataFormField')),
    resolver=batch_metadata_form_field_update,
    test_scope='MetadataForm',
)


createMetadataFormEnforcementRule = gql.MutationField(
    name='createMetadataFormEnforcementRule',
    args=[gql.Argument(name='input', type=gql.NonNullableType(gql.Ref('NewMetadataFormEnforcementInput')))],
    type=gql.Ref('MetadataFormEnforcementRule'),
    resolver=create_mf_enforcement_rule,
    test_scope='MetadataForm',
)

deleteMetadataFormEnforcementRule = gql.MutationField(
    name='deleteMetadataFormEnforcementRule',
    args=[
        gql.Argument(name='uri', type=gql.NonNullableType(gql.String)),
        gql.Argument(name='rule_uri', type=gql.NonNullableType(gql.String)),
    ],
    type=gql.Boolean,
    resolver=delete_mf_enforcement_rule,
    test_scope='MetadataForm',
)

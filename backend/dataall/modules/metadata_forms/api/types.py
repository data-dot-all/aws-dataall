from dataall.base.api import gql
from dataall.modules.metadata_forms.api.resolvers import (
    get_home_entity_name,
    get_form_fields,
    get_fields_glossary_node_name,
    get_user_role,
    get_attached_form_fields,
    has_tenant_permissions_for_metadata_forms,
    resolve_metadata_form,
    resolve_metadata_form_field,
)

MetadataForm = gql.ObjectType(
    name='MetadataForm',
    fields=[
        gql.Field(name='uri', type=gql.ID),
        gql.Field(name='name', type=gql.String),
        gql.Field(name='description', type=gql.String),
        gql.Field(name='SamlGroupName', type=gql.String),
        gql.Field(name='visibility', type=gql.String),
        gql.Field(name='homeEntity', type=gql.String),
        gql.Field(name='homeEntityName', type=gql.String, resolver=get_home_entity_name),
        gql.Field(name='userRole', type=gql.String, resolver=get_user_role),
        gql.Field(name='fields', type=gql.ArrayType(gql.Ref('MetadataFormField')), resolver=get_form_fields),
    ],
)

MetadataFormField = gql.ObjectType(
    name='MetadataFormField',
    fields=[
        gql.Field(name='uri', type=gql.ID),
        gql.Field(name='name', type=gql.String),
        gql.Field(name='displayNumber', type=gql.Integer),
        gql.Field(name='description', type=gql.String),
        gql.Field(name='type', type=gql.String),
        gql.Field(name='required', type=gql.Boolean),
        gql.Field(name='metadataFormUri', type=gql.String),
        gql.Field(name='glossaryNodeUri', type=gql.String),
        gql.Field(name='glossaryNodeName', type=gql.String, resolver=get_fields_glossary_node_name),
        gql.Field(name='possibleValues', type=gql.ArrayType(gql.String)),
    ],
)

MetadataFormSearchResult = gql.ObjectType(
    name='MetadataFormSearchResult',
    fields=[
        gql.Field(name='count', type=gql.Integer),
        gql.Field(name='nodes', type=gql.ArrayType(gql.Ref('MetadataForm'))),
        gql.Field(name='pageSize', type=gql.Integer),
        gql.Field(name='nextPage', type=gql.Integer),
        gql.Field(name='pages', type=gql.Integer),
        gql.Field(name='page', type=gql.Integer),
        gql.Field(name='previousPage', type=gql.Integer),
        gql.Field(name='hasNext', type=gql.Boolean),
        gql.Field(name='hasPrevious', type=gql.Boolean),
        gql.Field(name='hasTenantPermissions', type=gql.Boolean, resolver=has_tenant_permissions_for_metadata_forms),
    ],
)

AttachedMetadataFormSearchResult = gql.ObjectType(
    name='AttachedMetadataFormSearchResult',
    fields=[
        gql.Field(name='count', type=gql.Integer),
        gql.Field(name='nodes', type=gql.ArrayType(gql.Ref('AttachedMetadataForm'))),
        gql.Field(name='pageSize', type=gql.Integer),
        gql.Field(name='nextPage', type=gql.Integer),
        gql.Field(name='pages', type=gql.Integer),
        gql.Field(name='page', type=gql.Integer),
        gql.Field(name='previousPage', type=gql.Integer),
        gql.Field(name='hasNext', type=gql.Boolean),
        gql.Field(name='hasPrevious', type=gql.Boolean),
    ],
)

AttachedMetadataForm = gql.ObjectType(
    name='AttachedMetadataForm',
    fields=[
        gql.Field(name='uri', type=gql.ID),
        gql.Field(name='metadataForm', type=gql.Ref('MetadataForm'), resolver=resolve_metadata_form),
        gql.Field(name='entityUri', type=gql.String),
        gql.Field(name='entityType', type=gql.String),
        gql.Field(
            name='fields', type=gql.ArrayType(gql.Ref('AttachedMetadataFormField')), resolver=get_attached_form_fields
        ),
    ],
)

AttachedMetadataFormField = gql.ObjectType(
    name='AttachedMetadataFormField',
    fields=[
        gql.Field(name='uri', type=gql.ID),
        gql.Field(name='field', type=gql.Ref('MetadataFormField'), resolver=resolve_metadata_form_field),
        gql.Field(name='value', type=gql.String),
    ],
)

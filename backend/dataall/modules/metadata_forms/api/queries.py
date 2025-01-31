from dataall.base.api import gql
from dataall.modules.metadata_forms.api.resolvers import (
    list_user_metadata_forms,
    list_entity_metadata_forms,
    get_metadata_form,
    get_attached_metadata_form,
    list_attached_forms,
    get_entity_metadata_form_permissions,
    list_metadata_form_versions,
    list_mf_enforcement_rules,
    list_mf_affected_entities,
    list_entity_types_with_scope,
    list_affecting_rules,
)

listUserMetadataForms = gql.QueryField(
    name='listUserMetadataForms',
    args=[gql.Argument('filter', gql.Ref('MetadataFormFilter'))],
    type=gql.Ref('MetadataFormSearchResult'),
    resolver=list_user_metadata_forms,
    test_scope='MetadataForm',
)

listEntityMetadataForms = gql.QueryField(
    name='listEntityMetadataForms',
    args=[gql.Argument('filter', gql.Ref('MetadataFormFilter'))],
    type=gql.Ref('MetadataFormSearchResult'),
    resolver=list_entity_metadata_forms,
    test_scope='MetadataForm',
)

getMetadataForm = gql.QueryField(
    name='getMetadataForm',
    args=[gql.Argument('uri', gql.NonNullableType(gql.String))],
    type=gql.Ref('MetadataForm'),
    resolver=get_metadata_form,
    test_scope='MetadataForm',
)

listMetadataFormVersions = gql.QueryField(
    name='listMetadataFormVersions',
    args=[gql.Argument('uri', gql.NonNullableType(gql.String))],
    type=gql.ArrayType(gql.Ref('MetadataFormVersion')),
    resolver=list_metadata_form_versions,
    test_scope='MetadataForm',
)

listAttachedMetadataForms = gql.QueryField(
    name='listAttachedMetadataForms',
    args=[gql.Argument('filter', gql.Ref('AttachedMetadataFormFilter'))],
    type=gql.Ref('AttachedMetadataFormSearchResult'),
    resolver=list_attached_forms,
    test_scope='MetadataForm',
)

listMetadataFormEnforcementRules = gql.QueryField(
    name='listMetadataFormEnforcementRules',
    args=[gql.Argument('uri', gql.NonNullableType(gql.String))],
    type=gql.ArrayType(gql.Ref('MetadataFormEnforcementRule')),
    resolver=list_mf_enforcement_rules,
    test_scope='MetadataForm',
)

listEntityAffectedByEnforcementRule = gql.QueryField(
    name='listEntityAffectedByEnforcementRules',
    args=[
        gql.Argument('uri', gql.NonNullableType(gql.String)),
        gql.Argument('filter', gql.Ref('AffectedEntityFilter')),
    ],
    type=gql.Ref('MFAffectedEntitiesSearchResult'),
    resolver=list_mf_affected_entities,
    test_scope='MetadataForm',
)

getAttachedMetadataForm = gql.QueryField(
    name='getAttachedMetadataForm',
    args=[gql.Argument('uri', gql.NonNullableType(gql.String))],
    type=gql.Ref('AttachedMetadataForm'),
    resolver=get_attached_metadata_form,
    test_scope='MetadataForm',
)

getEntityMetadataFormPermissions = gql.QueryField(
    name='getEntityMetadataFormPermissions',
    args=[gql.Argument('entityUri', gql.NonNullableType(gql.String))],
    type=gql.ArrayType(gql.String),
    resolver=get_entity_metadata_form_permissions,
    test_scope='MetadataForm',
)


listEntityTypesWithScope = gql.QueryField(
    name='listEntityTypesWithScope',
    type=gql.ArrayType(gql.Ref('EntityTypeWithScope')),
    resolver=list_entity_types_with_scope,
    test_scope='MetadataForm',
)

listRulesThatAffectEntity = gql.QueryField(
    name='listRulesThatAffectEntity',
    args=[
        gql.Argument('entityUri', gql.NonNullableType(gql.String)),
        gql.Argument('entityType', gql.NonNullableType(gql.String)),
    ],
    type=gql.ArrayType(gql.Ref('AffectingRules')),
    resolver=list_affecting_rules,
    test_scope='MetadataForm',
)

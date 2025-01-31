from dataall.base.api.context import Context
from dataall.core.permissions.services.tenant_policy_service import TenantPolicyService
from dataall.modules.catalog.services.glossaries_service import GlossariesService
from dataall.modules.metadata_forms.db.metadata_form_models import (
    MetadataForm,
    MetadataFormField,
    AttachedMetadataForm,
    AttachedMetadataFormField,
    MetadataFormEnforcementRule,
)
from dataall.modules.metadata_forms.services.attached_metadata_form_service import AttachedMetadataFormService
from dataall.modules.metadata_forms.services.metadata_form_enforcement_service import MetadataFormEnforcementService
from dataall.modules.metadata_forms.services.metadata_form_permissions import MANAGE_METADATA_FORMS
from dataall.modules.metadata_forms.services.metadata_form_service import MetadataFormService, MetadataFormAccessService

from typing import Protocol


def create_metadata_form(context: Context, source, input):
    return MetadataFormService.create_metadata_form(data=input)


def create_metadata_form_version(context: Context, source, formUri, copyVersion):
    return MetadataFormService.create_metadata_form_version(uri=formUri, copyVersion=copyVersion)


def create_attached_metadata_form(context: Context, source, formUri, input):
    return AttachedMetadataFormService.create_or_update_attached_metadata_form(uri=formUri, data=input)


def delete_metadata_form(context: Context, source, formUri):
    return MetadataFormService.delete_metadata_form_by_uri(uri=formUri)


def delete_metadata_form_version(context: Context, source, formUri, version):
    return MetadataFormService.delete_metadata_form_version(uri=formUri, version=version)


def delete_attached_metadata_form(context: Context, source, attachedFormUri):
    return AttachedMetadataFormService.delete_attached_metadata_form(uri=attachedFormUri)


def list_user_metadata_forms(context: Context, source, filter=None):
    return MetadataFormService.paginated_user_metadata_form_list(filter=filter)


def list_entity_metadata_forms(context: Context, source, filter=None):
    return MetadataFormService.paginated_entity_metadata_form_list(filter=filter)


def get_home_entity_name(context: Context, source: MetadataForm):
    return MetadataFormService.get_home_entity_name(metadata_form=source)


def get_entity_name(context: Context, source: AttachedMetadataForm):
    return MetadataFormService.get_entity_name(attached_metadata_form=source)


def get_metadata_form(context: Context, source, uri):
    return MetadataFormService.get_metadata_form_by_uri(uri=uri)


class HasMetadataFormUri(Protocol):
    metadataFormUri: str


def resolve_metadata_form(context: Context, source: HasMetadataFormUri):
    return MetadataFormService.get_metadata_form_by_uri(source.metadataFormUri)


def get_form_fields(context: Context, source: MetadataForm, version):
    return MetadataFormService.get_metadata_form_fields(uri=source.uri, version=version)


def create_metadata_form_fields(context: Context, source, formUri, input):
    return MetadataFormService.create_metadata_form_fields(uri=formUri, data_arr=input)


def delete_metadata_form_field(context: Context, source, formUri, fieldUri):
    return MetadataFormService.delete_metadata_form_field(uri=formUri, fieldUri=fieldUri)


def batch_metadata_form_field_update(context: Context, source, formUri, input):
    return MetadataFormService.batch_metadata_form_field_update(uri=formUri, data=input)


def get_user_role(context: Context, source: MetadataForm):
    return MetadataFormAccessService.get_user_role(uri=source.uri)


def get_fields_glossary_node_name(context: Context, source: MetadataFormField):
    return GlossariesService.get_node(source.glossaryNodeUri).label if source.glossaryNodeUri else None


def list_attached_forms(context: Context, source, filter=None):
    return AttachedMetadataFormService.list_attached_forms(filter=filter)


def get_attached_form_fields(context: Context, source: AttachedMetadataForm):
    return AttachedMetadataFormService.get_attached_metadata_form_fields(uri=source.uri)


def get_attached_metadata_form(context: Context, source, uri):
    return AttachedMetadataFormService.get_attached_metadata_form(uri=uri)


def has_tenant_permissions_for_metadata_forms(context: Context, source: MetadataForm):
    return TenantPolicyService.has_user_tenant_permission(
        groups=context.groups,
        tenant_name=TenantPolicyService.TENANT_NAME,
        permission_name=MANAGE_METADATA_FORMS,
    )


def resolve_metadata_form_field(context: Context, source: AttachedMetadataFormField):
    return MetadataFormService.get_metadata_form_field_by_uri(uri=source.fieldUri)


def get_entity_metadata_form_permissions(context: Context, source, entityUri):
    return MetadataFormService.get_mf_permissions(entityUri=entityUri)


def list_metadata_form_versions(context: Context, source, uri):
    return MetadataFormService.list_metadata_form_versions(uri=uri)


def create_mf_enforcement_rule(context: Context, source, input):
    return MetadataFormEnforcementService.create_mf_enforcement_rule(uri=input.get('metadataFormUri'), data=input)


def list_mf_enforcement_rules(context: Context, source, uri):
    return MetadataFormEnforcementService.list_mf_enforcement_rules(uri=uri)


def list_mf_affected_entities(context: Context, source, uri, filter):
    return MetadataFormEnforcementService.paginate_mf_affected_entities(uri=uri, data=filter)


def get_mf_rule_home_entity_name(context: Context, source: MetadataFormEnforcementRule):
    return MetadataFormEnforcementService.resolve_home_entity(source.uri, source)


def delete_mf_enforcement_rule(context: Context, source, uri, rule_uri):
    return MetadataFormEnforcementService.delete_mf_enforcement_rule(uri=uri, rule_uri=rule_uri)


def list_entity_types_with_scope(context: Context, source):
    return MetadataFormEnforcementService.list_supported_entity_types()


def list_affecting_rules(context: Context, source, entityUri, entityType):
    return MetadataFormEnforcementService.get_rules_that_affect_entity(entity_type=entityType, entity_uri=entityUri)

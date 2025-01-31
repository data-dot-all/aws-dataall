from dataall.base.context import get_context
from dataall.base.db import exceptions, paginate
from dataall.base.db.exceptions import UnauthorizedOperation
from dataall.core.organizations.db.organization_repositories import OrganizationRepository
from dataall.core.environment.db.environment_repositories import EnvironmentRepository
from dataall.core.permissions.db.resource_policy.resource_policy_repositories import ResourcePolicyRepository
from dataall.core.permissions.services.resource_policy_service import ResourcePolicyService
from dataall.core.permissions.services.tenant_policy_service import TenantPolicyService
from dataall.modules.datasets_base.db.dataset_repositories import DatasetBaseRepository
from dataall.modules.metadata_forms.db.enums import (
    MetadataFormVisibility,
    MetadataFormFieldType,
)
from dataall.core.metadata_manager.metadata_form_entity_manager import MetadataFormEntityTypes
from dataall.modules.catalog.db.glossary_repositories import GlossaryRepository
from dataall.modules.metadata_forms.db.metadata_form_repository import MetadataFormRepository
from dataall.modules.metadata_forms.services.metadata_form_access_service import MetadataFormAccessService
from dataall.modules.metadata_forms.services.metadata_form_permissions import (
    MANAGE_METADATA_FORMS,
    DELETE_METADATA_FORM,
    DELETE_METADATA_FORM_FIELD,
    UPDATE_METADATA_FORM_FIELD,
    CREATE_METADATA_FORM,
    ALL_METADATA_FORMS_ENTITY_PERMISSIONS,
)
from dataall.modules.notifications.db.notification_repositories import NotificationRepository


class MetadataFormParamValidationService:
    @staticmethod
    def validate_create_form_params(data):
        visibility = data.get('visibility', MetadataFormVisibility.Team.value)
        if not MetadataFormVisibility.has_value(visibility):
            data['visibility'] = MetadataFormVisibility.Global.value

        if not data.get('SamlGroupName'):
            raise exceptions.RequiredParameter('SamlGroupName')

        if (not data.get('homeEntity')) and (visibility != MetadataFormVisibility.Global.value):
            raise exceptions.RequiredParameter('homeEntity')

        if not data.get('name'):
            raise exceptions.RequiredParameter('name')

    @staticmethod
    def validate_create_field_params(data):
        if 'name' not in data:
            raise exceptions.RequiredParameter('name')
        if 'type' not in data:
            raise exceptions.RequiredParameter('type')
        if 'displayNumber' not in data:
            raise exceptions.RequiredParameter('displayNumber')

        if data.get('type') == MetadataFormFieldType.GlossaryTerm.value:
            if 'glossaryNodeUri' not in data:
                raise exceptions.RequiredParameter('glossaryNodeUri')
            MetadataFormParamValidationService.validate_glossary_node_uri(data.get('glossaryNodeUri'))
        else:
            MetadataFormParamValidationService.validate_field_possible_values_params(data)

    @staticmethod
    def validate_update_field_params(form_uri, data):
        if data.get('metadataFormUri') != form_uri:
            raise Exception('property metadataFormUri does not match form uri')

        if 'displayNumber' not in data:
            raise exceptions.RequiredParameter('displayNumber')

        if data.get('type') == MetadataFormFieldType.GlossaryTerm.value:
            if 'glossaryNodeUri' not in data:
                raise exceptions.RequiredParameter('glossaryNodeUri')
            MetadataFormParamValidationService.validate_glossary_node_uri(data.get('glossaryNodeUri'))
        else:
            MetadataFormParamValidationService.validate_field_possible_values_params(data)

    @staticmethod
    def validate_glossary_node_uri(uri):
        with get_context().db_engine.scoped_session() as session:
            try:
                GlossaryRepository.get_node(session, uri)
                return True
            except exceptions.ObjectNotFound:
                raise exceptions.InvalidInput('glossaryNodeUri', uri, 'from glossary list')

    @staticmethod
    def validate_field_possible_values_params(data):
        def _raise(x):
            raise x

        validator_func = {
            MetadataFormFieldType.Integer.value: lambda x: x[1:].isdigit() if x[0] in ['+', '-'] else x.isdigit(),
            MetadataFormFieldType.Boolean.value: lambda x: _raise(
                Exception('possible values are not supported for boolean fields')
            ),
        }
        if data.get('possibleValues'):
            for value in data.get('possibleValues'):
                if not validator_func.get(data.get('type'), lambda x: True)(value):
                    raise exceptions.InvalidInput('possibleValues', value, data.get('type'))


class MetadataFormService:
    @staticmethod
    @TenantPolicyService.has_tenant_permission(MANAGE_METADATA_FORMS)
    def create_metadata_form(data):
        MetadataFormParamValidationService.validate_create_form_params(data)
        context = get_context()
        with context.db_engine.scoped_session() as session:
            if data.get('visibility') in [
                MetadataFormVisibility.Organization.value,
                MetadataFormVisibility.Environment.value,
            ]:
                ResourcePolicyService.check_user_resource_permission(
                    session=session,
                    username=context.username,
                    groups=context.groups,
                    resource_uri=data.get('homeEntity'),
                    permission_name=CREATE_METADATA_FORM,
                )

            form = MetadataFormRepository.create_metadata_form(session, data)
            try:
                MetadataFormRepository.create_metadata_form_version(session, form.uri, 1)
                return form
            except Exception as e:
                session.delete(form)
                raise e

    # toDo: add permission check
    @staticmethod
    def get_metadata_form_by_uri(uri):
        with get_context().db_engine.scoped_session() as session:
            mf = MetadataFormRepository.get_metadata_form(session, uri)
            if mf:
                mf.versions = MetadataFormRepository.get_metadata_form_versions_numbers(session, uri)
            return mf

    # toDo: deletion logic
    @staticmethod
    @TenantPolicyService.has_tenant_permission(MANAGE_METADATA_FORMS)
    @MetadataFormAccessService.can_perform(DELETE_METADATA_FORM)
    def delete_metadata_form_by_uri(uri):
        if mf := MetadataFormService.get_metadata_form_by_uri(uri):
            with get_context().db_engine.scoped_session() as session:
                return session.delete(mf)

    @staticmethod
    def paginated_entity_metadata_form_list(filter=None) -> dict:
        context = get_context()
        filter = filter or {}
        is_da_admin, user_orgs, user_envs = MetadataFormAccessService.get_user_admin_status_orgs_and_envs_()
        entity_orgs, entity_envs = MetadataFormAccessService.get_target_orgs_and_envs(
            context.username, context.groups, is_da_admin, filter
        )
        with context.db_engine.scoped_session() as session:
            return paginate(
                query=MetadataFormRepository.query_entity_metadata_forms(
                    session,
                    is_da_admin=is_da_admin,
                    groups=context.groups,
                    user_org_uris=user_orgs,
                    user_env_uris=user_envs,
                    entity_orgs_uris=entity_orgs,
                    entity_envs_uris=entity_envs,
                    filter=filter,
                ),
                page=filter.get('page', 1),
                page_size=filter.get('pageSize', 5),
            ).to_dict()

    @staticmethod
    def paginated_user_metadata_form_list(filter=None) -> dict:
        context = get_context()
        filter = filter or {}
        is_da_admin, user_orgs, user_envs = MetadataFormAccessService.get_user_admin_status_orgs_and_envs_()
        with get_context().db_engine.scoped_session() as session:
            return paginate(
                query=MetadataFormRepository.query_user_metadata_forms(
                    session,
                    is_da_admin=is_da_admin,
                    groups=context.groups,
                    env_uris=user_envs,
                    org_uris=user_orgs,
                    filter=filter,
                ),
                page=filter.get('page', 1),
                page_size=filter.get('pageSize', 5),
            ).to_dict()

    @staticmethod
    def get_home_entity_name(metadata_form):
        try:
            if metadata_form.visibility == MetadataFormVisibility.Team.value:
                return metadata_form.homeEntity
            elif metadata_form.visibility == MetadataFormVisibility.Organization.value:
                with get_context().db_engine.scoped_session() as session:
                    return OrganizationRepository.get_organization_by_uri(session, metadata_form.homeEntity).name
            elif metadata_form.visibility == MetadataFormVisibility.Environment.value:
                with get_context().db_engine.scoped_session() as session:
                    return EnvironmentRepository.get_environment_by_uri(session, metadata_form.homeEntity).name
            else:
                return ''
        except exceptions.ObjectNotFound as e:
            return 'Not Found'

    @staticmethod
    def get_metadata_form_fields(uri, version):
        with get_context().db_engine.scoped_session() as session:
            return MetadataFormRepository.get_metadata_form_fields(session, uri, version)

    @staticmethod
    def get_metadata_form_field_by_uri(uri):
        with get_context().db_engine.scoped_session() as session:
            return MetadataFormRepository.get_metadata_form_field_by_uri(session, uri)

    @staticmethod
    @TenantPolicyService.has_tenant_permission(MANAGE_METADATA_FORMS)
    @MetadataFormAccessService.can_perform(UPDATE_METADATA_FORM_FIELD)
    def create_metadata_form_field(uri, data):
        MetadataFormParamValidationService.validate_create_field_params(data)
        with get_context().db_engine.scoped_session() as session:
            return MetadataFormRepository.create_metadata_form_field(session, uri, data)

    @staticmethod
    @TenantPolicyService.has_tenant_permission(MANAGE_METADATA_FORMS)
    @MetadataFormAccessService.can_perform(UPDATE_METADATA_FORM_FIELD)
    def create_metadata_form_fields(uri, data_arr):
        fields = []
        for data in data_arr:
            fields.append(MetadataFormService.create_metadata_form_field(uri=uri, data=data))
        return fields

    @staticmethod
    @TenantPolicyService.has_tenant_permission(MANAGE_METADATA_FORMS)
    @MetadataFormAccessService.can_perform(DELETE_METADATA_FORM_FIELD)
    def delete_metadata_form_field(uri, fieldUri):
        mf = MetadataFormService.get_metadata_form_field_by_uri(fieldUri)
        with get_context().db_engine.scoped_session() as session:
            return session.delete(mf)

    @staticmethod
    @TenantPolicyService.has_tenant_permission(MANAGE_METADATA_FORMS)
    @MetadataFormAccessService.can_perform(UPDATE_METADATA_FORM_FIELD)
    def batch_metadata_form_field_update(uri, data):
        to_delete = []
        to_update = []
        to_create = []

        # validate all inputs first
        # if even one input is invalid -- decline whole batch
        for item in data:
            if item.get('uri') is None:
                MetadataFormParamValidationService.validate_create_field_params(item)
                to_create.append(item)
            elif not item.get('deleted', False):
                MetadataFormParamValidationService.validate_update_field_params(uri, item)
                to_update.append(item)
            else:
                to_delete.append(item['uri'])

        # process sorted items
        for item in to_delete:
            MetadataFormService.delete_metadata_form_field(uri=uri, fieldUri=item)

        with get_context().db_engine.scoped_session() as session:
            for item in to_update:
                MetadataFormRepository.update_metadata_form_field(session, item['uri'], item)
            for item in to_create:
                MetadataFormRepository.create_metadata_form_field(session, uri, item)

        return MetadataFormService.get_metadata_form_fields(uri, None)

    @staticmethod
    @TenantPolicyService.has_tenant_permission(MANAGE_METADATA_FORMS)
    @MetadataFormAccessService.can_perform(UPDATE_METADATA_FORM_FIELD)
    def update_metadata_form_field(uri, fieldUri, data):
        with get_context().db_engine.scoped_session() as session:
            MetadataFormParamValidationService.validate_update_field_params(uri, data)
            return MetadataFormRepository.update_metadata_form_field(session, fieldUri, data)

    @staticmethod
    def get_mf_permissions(entityUri):
        context = get_context()
        result_permissions = []
        with context.db_engine.scoped_session() as session:
            for permissions in ALL_METADATA_FORMS_ENTITY_PERMISSIONS:
                if ResourcePolicyRepository.has_user_resource_permission(
                    session=session,
                    groups=context.groups,
                    permission_name=permissions,
                    resource_uri=entityUri,
                ):
                    result_permissions.append(permissions)
            return result_permissions

    @staticmethod
    @TenantPolicyService.has_tenant_permission(MANAGE_METADATA_FORMS)
    @MetadataFormAccessService.can_perform(UPDATE_METADATA_FORM_FIELD)
    def create_metadata_form_version(uri, copyVersion):
        with get_context().db_engine.scoped_session() as session:
            mf = MetadataFormService.get_metadata_form_by_uri(uri)
            new_version = MetadataFormRepository.create_metadata_form_version_next(session, uri)
            if copyVersion:
                mf_fields = MetadataFormRepository.get_metadata_form_fields(session, uri, copyVersion)
                for field in mf_fields:
                    new_field = MetadataFormRepository.create_metadata_form_field(
                        session, uri, field.__dict__, new_version.version
                    )

            all_attached = MetadataFormRepository.get_all_attached_metadata_forms(session, uri)
            for attached in all_attached:
                owner = MetadataFormService.get_entity_owner(attached)
                if owner:
                    NotificationRepository.create_notification(
                        session,
                        recipient=owner,
                        target_uri=f'{attached.entityUri}|{attached.entityType}',
                        message=f'New version {new_version.version} is available for metadata form "{mf.name}" for {attached.entityType} {attached.entityUri}',
                        notification_type='METADATA_FORM_UPDATE',
                    )

            MetadataFormRepository.update_version_in_rules(session, uri, new_version.version)
        return new_version.version

    @staticmethod
    @TenantPolicyService.has_tenant_permission(MANAGE_METADATA_FORMS)
    @MetadataFormAccessService.can_perform(UPDATE_METADATA_FORM_FIELD)
    def delete_metadata_form_version(uri, version):
        with get_context().db_engine.scoped_session() as session:
            all_versions = MetadataFormRepository.get_metadata_form_versions_numbers(session, uri)
            if len(all_versions) == 1:
                raise UnauthorizedOperation(
                    action='Delete version', message='Cannot delete the only version of the form'
                )
            mf = MetadataFormRepository.get_metadata_form_version(session, uri, version)
            if version == all_versions[0]:
                MetadataFormRepository.update_version_in_rules(session, uri, all_versions[1])
            session.delete(mf)
            return MetadataFormRepository.get_metadata_form_version_number_latest(session, uri)

    @staticmethod
    def list_metadata_form_versions(uri):
        with get_context().db_engine.scoped_session() as session:
            all_versions = MetadataFormRepository.get_metadata_form_versions(session, uri)
            for v in all_versions:
                v.attached_forms = len(MetadataFormRepository.get_all_attached_metadata_forms(session, uri, v.version))
            return all_versions

    @staticmethod
    def resolve_attached_entity(attached_metadata_form):
        with get_context().db_engine.scoped_session() as session:
            if attached_metadata_form.entityType == MetadataFormEntityTypes.Organizations.value:
                return OrganizationRepository.get_organization_by_uri(session, attached_metadata_form.entityUri)
            elif attached_metadata_form.entityType == MetadataFormEntityTypes.Environments.value:
                return EnvironmentRepository.get_environment_by_uri(session, attached_metadata_form.entityUri)
            elif attached_metadata_form.entityType in [
                MetadataFormEntityTypes.S3Datasets.value,
                MetadataFormEntityTypes.RDDatasets.value,
            ]:
                return DatasetBaseRepository.get_dataset_by_uri(session, attached_metadata_form.entityUri)
            else:
                return None

    @staticmethod
    def get_entity_name(attached_metadata_form):
        entity = MetadataFormService.resolve_attached_entity(attached_metadata_form)
        return entity.name if entity else 'Not Found'

    @staticmethod
    def get_entity_owner(attached_metadata_form):
        entity = MetadataFormService.resolve_attached_entity(attached_metadata_form)
        if entity:
            if attached_metadata_form.entityType == MetadataFormEntityTypes.Organizations.value:
                return entity.SamlGroupName
            elif attached_metadata_form.entityType == MetadataFormEntityTypes.Environments.value:
                return entity.SamlGroupName
            elif attached_metadata_form.entityType in [
                MetadataFormEntityTypes.S3Datasets.value,
                MetadataFormEntityTypes.RDDatasets.value,
            ]:
                return entity.SamlAdminGroupName
        return None

from functools import wraps

from dataall.base.context import get_context
from dataall.base.db import exceptions, paginate
from dataall.core.organizations.db.organization_repositories import OrganizationRepository
from dataall.core.environment.db.environment_repositories import EnvironmentRepository
from dataall.core.permissions.services.tenant_policy_service import TenantPolicyValidationService, TenantPolicyService
from dataall.modules.datasets_base.db.dataset_repositories import DatasetBaseRepository
from dataall.modules.metadata_forms.db.enums import (
    MetadataFormVisibility,
    MetadataFormUserRoles,
    MetadataFormFieldType,
    MetadataFormEntityTypes,
)
from dataall.modules.catalog.db.glossary_repositories import GlossaryRepository
from dataall.modules.metadata_forms.db.metadata_form_repository import MetadataFormRepository
from dataall.modules.metadata_forms.services.metadata_form_permissions import MANAGE_METADATA_FORMS


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


class MetadataFormAccessService:
    @staticmethod
    def is_owner(uri):
        context = get_context()
        with context.db_engine.scoped_session() as session:
            return MetadataFormRepository.get_metadata_form_owner(session, uri) in context.groups

    @staticmethod
    def can_perform(action: str):
        def decorator(f):
            @wraps(f)
            def check_permission(*args, **kwds):
                uri = kwds.get('uri')
                if not uri:
                    raise KeyError(f"{f.__name__} doesn't have parameter uri.")

                if MetadataFormAccessService.is_owner(uri):
                    return f(*args, **kwds)
                else:
                    raise exceptions.UnauthorizedOperation(
                        action=action,
                        message=f'User {get_context().username} is not the owner of the metadata form {uri}',
                    )

            return check_permission

        return decorator

    @staticmethod
    def get_user_role(uri):
        if MetadataFormAccessService.is_owner(uri):
            return MetadataFormUserRoles.Owner.value
        else:
            return MetadataFormUserRoles.User.value


class MetadataFormService:
    @staticmethod
    def _target_org_uri_getter(entityType, entityUri):
        if not entityType or not entityUri:
            return None
        if entityType == MetadataFormEntityTypes.Organizations.value:
            return entityUri
        elif entityType == MetadataFormEntityTypes.Environments.value:
            with get_context().db_engine.scoped_session() as session:
                return EnvironmentRepository.get_environment_by_uri(session, entityUri).organizationUri
        elif entityType == MetadataFormEntityTypes.Datasets.value:
            with get_context().db_engine.scoped_session() as session:
                return DatasetBaseRepository.get_dataset_by_uri(session, entityUri).organizationUri
        else:
            # toDo add other entities
            return None

    @staticmethod
    def _target_env_uri_getter(entityType, entityUri):
        if not entityType or not entityUri:
            return None
        if entityType == MetadataFormEntityTypes.Organizations.value:
            return None
        elif entityType == MetadataFormEntityTypes.Environments.value:
            return entityUri
        elif entityType == MetadataFormEntityTypes.Datasets.value:
            with get_context().db_engine.scoped_session() as session:
                return DatasetBaseRepository.get_dataset_by_uri(session, entityUri).environmentUri
        else:
            # toDo add other entities
            return None

    @staticmethod
    def _get_target_orgs_and_envs(username, groups, is_da_admin=False, filter={}):
        envs = None
        orgs = None
        target_org_uri = MetadataFormService._target_org_uri_getter(filter.get('entityType'), filter.get('entityUri'))
        target_env_uri = MetadataFormService._target_env_uri_getter(filter.get('entityType'), filter.get('entityUri'))
        # is user is no dataall admin, query_metadata_forms requires arrays of users envs and orgs uris
        if not is_da_admin:
            with get_context().db_engine.scoped_session() as session:
                envs = EnvironmentRepository.query_user_environments(session, username, groups, {})
                envs = [e.environmentUri for e in envs]
                orgs = OrganizationRepository.query_user_organizations(session, username, groups, {})
                orgs = [o.organizationUri for o in orgs]
        if target_org_uri:
            if orgs and target_org_uri not in orgs:
                raise exceptions.UnauthorizedOperation(
                    action='GET METADATA FORM LIST',
                    message=f'User {username} can not view organization {target_org_uri}',
                )
            orgs = [target_org_uri]

        if target_env_uri:
            if envs and target_env_uri not in envs:
                raise exceptions.UnauthorizedOperation(
                    action='GET METADATA FORM LIST',
                    message=f'User {username} can not view environment {target_env_uri}',
                )
            envs = [target_env_uri]

        if filter.get('entityType') == MetadataFormEntityTypes.Organizations.value:
            envs = []

        return orgs, envs

    @staticmethod
    @TenantPolicyService.has_tenant_permission(MANAGE_METADATA_FORMS)
    def create_metadata_form(data):
        MetadataFormParamValidationService.validate_create_form_params(data)
        with get_context().db_engine.scoped_session() as session:
            form = MetadataFormRepository.create_metadata_form(session, data)
            return form

    # toDo: add permission check
    @staticmethod
    def get_metadata_form_by_uri(uri):
        with get_context().db_engine.scoped_session() as session:
            return MetadataFormRepository.get_metadata_form(session, uri)

    # toDo: deletion logic
    @staticmethod
    @TenantPolicyService.has_tenant_permission(MANAGE_METADATA_FORMS)
    @MetadataFormAccessService.can_perform('DELETE')
    def delete_metadata_form_by_uri(uri):
        if mf := MetadataFormService.get_metadata_form_by_uri(uri):
            with get_context().db_engine.scoped_session() as session:
                return session.delete(mf)

    @staticmethod
    def paginated_metadata_form_list(filter=None) -> dict:
        context = get_context()
        groups = context.groups
        is_da_admin = TenantPolicyValidationService.is_tenant_admin(groups)
        filter = filter if filter is not None else {}
        orgs, envs = MetadataFormService._get_target_orgs_and_envs(
            context.username, context.groups, is_da_admin, filter
        )
        with context.db_engine.scoped_session() as session:
            return paginate(
                query=MetadataFormRepository.query_metadata_forms(session, is_da_admin, groups, envs, orgs, filter),
                page=filter.get('page', 1),
                page_size=filter.get('pageSize', 5),
            ).to_dict()

    @staticmethod
    def get_home_entity_name(metadata_form):
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

    @staticmethod
    def get_metadata_form_fields(uri):
        with get_context().db_engine.scoped_session() as session:
            return MetadataFormRepository.get_metadata_form_fields(session, uri)

    @staticmethod
    def get_metadata_form_field_by_uri(uri):
        with get_context().db_engine.scoped_session() as session:
            return MetadataFormRepository.get_metadata_form_field_by_uri(session, uri)

    @staticmethod
    @TenantPolicyService.has_tenant_permission(MANAGE_METADATA_FORMS)
    @MetadataFormAccessService.can_perform('ADD FIELD')
    def create_metadata_form_field(uri, data):
        MetadataFormParamValidationService.validate_create_field_params(data)
        with get_context().db_engine.scoped_session() as session:
            return MetadataFormRepository.create_metadata_form_field(session, uri, data)

    @staticmethod
    @TenantPolicyService.has_tenant_permission(MANAGE_METADATA_FORMS)
    @MetadataFormAccessService.can_perform('ADD FIELDS')
    def create_metadata_form_fields(uri, data_arr):
        fields = []
        for data in data_arr:
            fields.append(MetadataFormService.create_metadata_form_field(uri=uri, data=data))
        return fields

    @staticmethod
    @TenantPolicyService.has_tenant_permission(MANAGE_METADATA_FORMS)
    @MetadataFormAccessService.can_perform('DELETE FIELD')
    def delete_metadata_form_field(uri, fieldUri):
        mf = MetadataFormService.get_metadata_form_field_by_uri(fieldUri)
        with get_context().db_engine.scoped_session() as session:
            return session.delete(mf)

    @staticmethod
    @TenantPolicyService.has_tenant_permission(MANAGE_METADATA_FORMS)
    @MetadataFormAccessService.can_perform('UPDATE FIELDS')
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

        return MetadataFormService.get_metadata_form_fields(uri)

    @staticmethod
    @TenantPolicyService.has_tenant_permission(MANAGE_METADATA_FORMS)
    @MetadataFormAccessService.can_perform('UPDATE FIELD')
    def update_metadata_form_field(uri, fieldUri, data):
        with get_context().db_engine.scoped_session() as session:
            MetadataFormParamValidationService.validate_update_field_params(uri, data)
            return MetadataFormRepository.update_metadata_form_field(session, fieldUri, data)

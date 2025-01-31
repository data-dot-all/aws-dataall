import logging

from dataall.base.context import get_context
from dataall.core.environment.db.environment_repositories import EnvironmentRepository
from dataall.core.organizations.db.organization_repositories import OrganizationRepository
from dataall.core.permissions.services.resource_policy_service import ResourcePolicyService
from dataall.core.permissions.services.tenant_policy_service import TenantPolicyValidationService
from dataall.modules.datasets_base.db.dataset_repositories import DatasetBaseRepository
from dataall.modules.metadata_forms.db.enums import (
    MetadataFormUserRoles,
    MetadataFormEnforcementScope,
)
from dataall.core.metadata_manager.metadata_form_entity_manager import MetadataFormEntityTypes
from dataall.modules.metadata_forms.db.metadata_form_repository import MetadataFormRepository
from functools import wraps
from dataall.base.db import exceptions
from dataall.modules.metadata_forms.services.metadata_form_permissions import ENFORCE_METADATA_FORM


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

    @staticmethod
    def get_user_admin_status_orgs_and_envs_():
        context = get_context()
        groups = context.groups
        username = context.username
        is_da_admin = TenantPolicyValidationService.is_tenant_admin(context.groups)
        if is_da_admin:
            return True, None, None
        with context.db_engine.scoped_session() as session:
            user_envs = EnvironmentRepository.query_user_environments(session, username, groups, {})
            user_envs = [e.environmentUri for e in user_envs]
            user_orgs = OrganizationRepository.query_user_organizations(session, username, groups, {})
            user_orgs = [o.organizationUri for o in user_orgs]
            return is_da_admin, user_orgs, user_envs

    @staticmethod
    def _target_org_uri_getter(entityType, entityUri):
        if not entityType or not entityUri:
            return None
        if entityType == MetadataFormEntityTypes.Organizations.value:
            return [entityUri]
        elif entityType == MetadataFormEntityTypes.Environments.value:
            with get_context().db_engine.scoped_session() as session:
                return [EnvironmentRepository.get_environment_by_uri(session, entityUri).organizationUri]
        elif entityType in [MetadataFormEntityTypes.S3Datasets.value, MetadataFormEntityTypes.RDDatasets.value]:
            with get_context().db_engine.scoped_session() as session:
                return [DatasetBaseRepository.get_dataset_by_uri(session, entityUri).organizationUri]
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
            return [entityUri]
        elif entityType in [MetadataFormEntityTypes.S3Datasets.value, MetadataFormEntityTypes.RDDatasets.value]:
            with get_context().db_engine.scoped_session() as session:
                return [DatasetBaseRepository.get_dataset_by_uri(session, entityUri).environmentUri]
        else:
            # toDo add other entities
            return None

    @staticmethod
    def get_target_orgs_and_envs(username, groups, is_da_admin=False, filter={}):
        orgs = MetadataFormAccessService._target_org_uri_getter(filter.get('entityType'), filter.get('entityUri'))
        envs = MetadataFormAccessService._target_env_uri_getter(filter.get('entityType'), filter.get('entityUri'))

        return orgs, envs

    @staticmethod
    def check_enforcement_access(entityUri, level):
        context = get_context()
        is_admin = TenantPolicyValidationService.is_tenant_admin(context.groups)

        if level == MetadataFormEnforcementScope.Global.value:
            if is_admin:
                return True
            raise exceptions.UnauthorizedOperation(
                action=ENFORCE_METADATA_FORM, message='Only data.all admins can enforce metadata forms on global level'
            )

        with context.db_engine.scoped_session() as session:
            ResourcePolicyService.check_user_resource_permission(
                session=session,
                username=context.username,
                groups=context.groups,
                resource_uri=entityUri,
                permission_name=ENFORCE_METADATA_FORM,
            )
        return True

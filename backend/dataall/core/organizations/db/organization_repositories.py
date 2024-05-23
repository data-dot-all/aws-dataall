import logging

from sqlalchemy import or_, and_
from sqlalchemy.orm import Query

from dataall.base.db import exceptions, paginate
from dataall.core.organizations.db import organization_models as models
from dataall.core.environment.db.environment_models import Environment
from dataall.base.context import get_context

from dataall.core.permissions.db.permission.permission_models import Permission
from dataall.core.permissions.db.resource_policy.resource_policy_models import ResourcePolicy, ResourcePolicyPermission
from dataall.core.permissions.services.organization_permissions import GET_ORGANIZATION

logger = logging.getLogger(__name__)


class OrganizationRepository:
    @staticmethod
    def get_organization_by_uri(session, uri: str) -> models.Organization:
        if not uri:
            raise exceptions.RequiredParameter(param_name='organizationUri')
        org = OrganizationRepository.find_organization_by_uri(session, uri)
        if not org:
            raise exceptions.ObjectNotFound('Organization', uri)
        return org

    @staticmethod
    def find_organization_by_uri(session, uri) -> models.Organization:
        return session.query(models.Organization).get(uri)

    @staticmethod
    def query_user_organizations(session, username, groups, filter) -> Query:
        query = (
            session.query(models.Organization)
            .outerjoin(
                ResourcePolicy,
                ResourcePolicy.resourceUri == models.Organization.organizationUri,
            )
            .join(
                ResourcePolicyPermission,
                ResourcePolicy.sid == ResourcePolicyPermission.sid,
            )
            .join(
                Permission,
                Permission.permissionUri == ResourcePolicyPermission.permissionUri,
            )
            .filter(
                or_(
                    models.Organization.owner == username,
                    and_(
                        Permission.name == GET_ORGANIZATION,
                        ResourcePolicy.principalType == 'GROUP',
                        ResourcePolicy.principalId.in_(groups),
                    ),
                )
            )
        )
        if filter and filter.get('term'):
            query = query.filter(
                or_(
                    models.Organization.label.ilike('%' + filter.get('term') + '%'),
                    models.Organization.description.ilike('%' + filter.get('term') + '%'),
                    models.Organization.tags.contains(f"{{{filter.get('term')}}}"),
                )
            )
        return query.order_by(models.Organization.label).distinct()

    @staticmethod
    def paginated_user_organizations(session, data=None) -> dict:
        context = get_context()
        return paginate(
            query=OrganizationRepository.query_user_organizations(session, context.username, context.groups, data),
            page=data.get('page', 1),
            page_size=data.get('pageSize', 10),
        ).to_dict()

    @staticmethod
    def query_organization_environments(session, uri, filter) -> Query:
        query = session.query(Environment).filter(Environment.organizationUri == uri)
        if filter and filter.get('term'):
            query = query.filter(
                or_(
                    Environment.label.ilike('%' + filter.get('term') + '%'),
                    Environment.description.ilike('%' + filter.get('term') + '%'),
                )
            )
        return query.order_by(Environment.label)

    @staticmethod
    def paginated_organization_environments(session, uri, data=None) -> dict:
        return paginate(
            query=OrganizationRepository.query_organization_environments(session, uri, data),
            page=data.get('page', 1),
            page_size=data.get('pageSize', 10),
        ).to_dict()

    @staticmethod
    def find_group_membership(session, group, organization):
        membership = (
            session.query(models.OrganizationGroup)
            .filter(
                (
                    and_(
                        models.OrganizationGroup.groupUri == group,
                        models.OrganizationGroup.organizationUri == organization.organizationUri,
                    )
                )
            )
            .first()
        )
        return membership

    @staticmethod
    def query_organization_groups(session, uri, filter) -> Query:
        query = session.query(models.OrganizationGroup).filter(models.OrganizationGroup.organizationUri == uri)
        if filter and filter.get('term'):
            query = query.filter(
                or_(
                    models.OrganizationGroup.groupUri.ilike('%' + filter.get('term') + '%'),
                )
            )
        return query.order_by(models.OrganizationGroup.groupUri)

    @staticmethod
    def query_organization_readers(session, uri, filter) -> Query:
        org_groups = OrganizationRepository.query_organization_groups(session, uri, None).all()
        org_groups = [group.groupUri for group in org_groups]
        query = (
            session.query(ResourcePolicy.principalId.label('groupUri'))
            .join(
                ResourcePolicyPermission,
                ResourcePolicy.sid == ResourcePolicyPermission.sid,
            )
            .join(
                Permission,
                Permission.permissionUri == ResourcePolicyPermission.permissionUri,
            )
            .filter(
                or_(
                    and_(
                        Permission.name == GET_ORGANIZATION,
                        ResourcePolicy.principalType == 'GROUP',
                        ResourcePolicy.principalId.notin_(org_groups),
                    ),
                )
            )
        )
        if filter and filter.get('term'):
            query = query.filter(
                ResourcePolicy.principalId.ilike('%' + filter.get('term') + '%'),
            )

        return query.distinct().order_by(ResourcePolicy.principalId)

    @staticmethod
    def is_group_invited(session, uri, group) -> bool:
        return (
            session.query(models.OrganizationGroup)
            .filter(
                and_(
                    models.OrganizationGroup.organizationUri == uri,
                    models.OrganizationGroup.groupUri == group,
                )
            )
            .count()
        ) > 0

    @staticmethod
    def paginated_organization_groups(session, uri, data=None) -> dict:
        return paginate(
            query=OrganizationRepository.query_organization_groups(session, uri, data),
            page=data.get('page', 1),
            page_size=data.get('pageSize', 10),
        ).to_dict()

    @staticmethod
    def paginated_organization_readers(session, uri, data=None) -> dict:
        return paginate(
            query=OrganizationRepository.query_organization_readers(session, uri, data),
            page=data.get('page', 1),
            page_size=data.get('pageSize', 10),
        ).to_dict()

    @staticmethod
    def count_organization_invited_groups(session, uri, group) -> int:
        groups = (
            session.query(models.OrganizationGroup)
            .filter(
                and_(
                    models.OrganizationGroup.organizationUri == uri,
                    models.OrganizationGroup.groupUri != group,
                )
            )
            .count()
        )
        return groups

    @staticmethod
    def find_organization_membership(session, uri, groups) -> int:
        groups = (
            session.query(models.OrganizationGroup)
            .filter(
                and_(
                    models.OrganizationGroup.organizationUri == uri,
                    models.OrganizationGroup.groupUri.in_(groups),
                )
            )
            .count()
        )
        return groups >= 1

from dataall.base.utils.naming_convention import NamingConventionPattern, NamingConventionService
from dataall.core.environment.db.environment_models import (
    EnvironmentParameter,
    Environment,
    ConsumptionRole,
    EnvironmentGroup,
)
from sqlalchemy.sql import and_, or_
from sqlalchemy.orm import Query

from dataall.base.db import exceptions
from typing import List


class EnvironmentParameterRepository:
    """CRUD operations for EnvironmentParameter"""

    def __init__(self, session):
        self._session = session

    def get_param(self, env_uri, param_key):
        return (
            self._session.query(EnvironmentParameter)
            .filter(and_(EnvironmentParameter.environmentUri == env_uri, EnvironmentParameter.key == param_key))
            .first()
        )

    def get_params(self, env_uri):
        return self._session.query(EnvironmentParameter).filter(EnvironmentParameter.environmentUri == env_uri)

    def update_params(self, env_uri, params):
        """Rewrite all parameters for the environment"""
        self.delete_params(env_uri)
        self._session.add_all(params)

    def delete_params(self, env_uri):
        """Erase all environment parameters"""
        self._session.query(EnvironmentParameter).filter(EnvironmentParameter.environmentUri == env_uri).delete()


class EnvironmentRepository:
    @staticmethod
    def get_environment_by_uri(session, uri):
        if not uri:
            raise exceptions.RequiredParameter('environmentUri')
        environment: Environment = session.query(Environment).get(uri)
        if not environment:
            raise exceptions.ObjectNotFound(Environment.__name__, uri)
        return environment

    @staticmethod
    def count_environments_with_organization_uri(session, uri):
        return session.query(Environment).filter(Environment.organizationUri == uri).count()

    @staticmethod
    def count_environments_with_organization_and_group(session, organization, group):
        return (
            session.query(Environment)
            .filter(
                and_(
                    Environment.organizationUri == organization.organizationUri,
                    Environment.SamlGroupName == group,
                )
            )
            .count()
        )

    @staticmethod
    def find_environment_by_account_region(session, account_id, region):
        environment: Environment = (
            session.query(Environment)
            .filter(and_(Environment.AwsAccountId == account_id, Environment.region == region))
            .first()
        )
        if not environment:
            return None
        return environment

    @staticmethod
    def get_environment_consumption_role(session, role_uri, environment_uri) -> ConsumptionRole:
        return (
            session.query(ConsumptionRole)
            .filter(
                (
                    and_(
                        ConsumptionRole.consumptionRoleUri == role_uri,
                        ConsumptionRole.environmentUri == environment_uri,
                    )
                )
            )
            .first()
        )

    @staticmethod
    def get_environment_group(session, group_uri, environment_uri):
        return (
            session.query(EnvironmentGroup)
            .filter(
                (
                    and_(
                        EnvironmentGroup.groupUri == group_uri,
                        EnvironmentGroup.environmentUri == environment_uri,
                    )
                )
            )
            .first()
        )

    @staticmethod
    def get_consumption_role(session, uri):
        return (
            session.query(ConsumptionRole)
            .filter(
                and_(
                    ConsumptionRole.consumptionRoleUri == uri,
                )
            )
            .first()
        )

    @staticmethod
    def find_consumption_roles_by_IAMArn(session, uri, arn):
        return (
            session.query(ConsumptionRole)
            .filter(and_(ConsumptionRole.environmentUri == uri, ConsumptionRole.IAMRoleArn == arn))
            .first()
        )

    @staticmethod
    def query_all_environment_consumption_roles(session, uri, filter) -> Query:
        query = session.query(ConsumptionRole).filter(ConsumptionRole.environmentUri == uri)
        if filter and filter.get('term'):
            term = filter['term']
            query = query.filter(
                or_(
                    ConsumptionRole.consumptionRoleName.ilike('%' + term + '%'),
                )
            )
        if filter and filter.get('groupUri'):
            group = filter['groupUri']
            query = query.filter(
                or_(
                    ConsumptionRole.groupUri == group,
                )
            )
        return query.order_by(ConsumptionRole.consumptionRoleName)

    @staticmethod
    def query_user_environment_consumption_roles(session, groups, uri, filter) -> Query:
        query = (
            session.query(ConsumptionRole)
            .filter(ConsumptionRole.environmentUri == uri)
            .filter(ConsumptionRole.groupUri.in_(groups))
        )
        if filter and filter.get('term'):
            term = filter['term']
            query = query.filter(
                or_(
                    ConsumptionRole.consumptionRoleName.ilike('%' + term + '%'),
                )
            )
        if filter and filter.get('groupUri'):
            print('filter group')
            group = filter['groupUri']
            query = query.filter(
                or_(
                    ConsumptionRole.groupUri == group,
                )
            )
        return query.order_by(ConsumptionRole.consumptionRoleName)

    @staticmethod
    def query_environment_invited_groups(session, uri, filter) -> Query:
        query = (
            session.query(EnvironmentGroup)
            .join(
                Environment,
                EnvironmentGroup.environmentUri == Environment.environmentUri,
            )
            .filter(
                and_(
                    Environment.environmentUri == uri,
                    EnvironmentGroup.groupUri != Environment.SamlGroupName,
                )
            )
        )
        if filter and filter.get('term'):
            term = filter['term']
            query = query.filter(
                or_(
                    EnvironmentGroup.groupUri.ilike('%' + term + '%'),
                )
            )
        return query.order_by(EnvironmentGroup.groupUri)

    @staticmethod
    def query_user_environment_groups(session, groups, uri, filter) -> Query:
        query = (
            session.query(EnvironmentGroup)
            .filter(EnvironmentGroup.environmentUri == uri)
            .filter(EnvironmentGroup.groupUri.in_(groups))
        )
        if filter and filter.get('term'):
            term = filter['term']
            query = query.filter(
                or_(
                    EnvironmentGroup.groupUri.ilike('%' + term + '%'),
                )
            )
        return query.order_by(EnvironmentGroup.groupUri)

    @staticmethod
    def query_all_environment_groups(session, uri, filter) -> Query:
        query = session.query(EnvironmentGroup).filter(EnvironmentGroup.environmentUri == uri)
        if filter and filter.get('term'):
            term = filter['term']
            query = query.filter(
                or_(
                    EnvironmentGroup.groupUri.ilike('%' + term + '%'),
                )
            )
        return query.order_by(EnvironmentGroup.groupUri)

    @staticmethod
    def query_user_consumption_roles(session, username, groups, filter) -> Query:
        query = (
            session.query(ConsumptionRole)
            .filter(ConsumptionRole.groupUri.in_(groups))
            .distinct(ConsumptionRole.consumptionRoleName)
        )
        if filter and filter.get('term'):
            term = filter['term']
            query = query.filter(
                or_(
                    ConsumptionRole.consumptionRoleName.ilike('%' + term + '%'),
                )
            )
        if filter and filter.get('groupUri'):
            print('filter group')
            group = filter['groupUri']
            query = query.filter(
                or_(
                    ConsumptionRole.groupUri == group,
                )
            )
        return query.order_by(ConsumptionRole.consumptionRoleName)

    @staticmethod
    def query_user_groups(session, username, groups, filter) -> Query:
        query = (
            session.query(EnvironmentGroup)
            .filter(EnvironmentGroup.groupUri.in_(groups))
            .distinct(EnvironmentGroup.groupUri)
        )
        if filter and filter.get('term'):
            term = filter['term']
            query = query.filter(
                or_(
                    EnvironmentGroup.groupUri.ilike('%' + term + '%'),
                )
            )
        return query.order_by(EnvironmentGroup.groupUri)

    @staticmethod
    def query_user_environments(session, username, groups, filter) -> Query:
        query = (
            session.query(Environment)
            .outerjoin(
                EnvironmentGroup,
                Environment.environmentUri == EnvironmentGroup.environmentUri,
            )
            .filter(
                or_(
                    Environment.owner == username,
                    EnvironmentGroup.groupUri.in_(groups),
                )
            )
        )
        if filter and filter.get('term'):
            term = filter['term']
            query = query.filter(
                or_(
                    Environment.label.ilike('%' + term + '%'),
                    Environment.description.ilike('%' + term + '%'),
                    Environment.tags.contains(
                        f'{{{NamingConventionService(pattern=NamingConventionPattern.DEFAULT_SEARCH, target_label=term).sanitize()}}}'
                    ),
                    Environment.region.ilike('%' + term + '%'),
                )
            )
        if filter and filter.get('SamlGroupName') and filter.get('SamlGroupName') in groups:
            query = query.filter(EnvironmentGroup.groupUri == filter.get('SamlGroupName'))
        return query.order_by(Environment.label).distinct()

    @staticmethod
    def is_user_invited_to_environment(session, groups, uri):
        env_group = (
            session.query(EnvironmentGroup)
            .filter(
                and_(
                    EnvironmentGroup.environmentUri == uri,
                    EnvironmentGroup.groupUri.in_(groups),
                )
            )
            .first()
        )
        return env_group is not None

    @staticmethod
    def query_all_active_environments(session) -> List[Environment]:
        return session.query(Environment).filter(Environment.deleted.is_(None)).all()

    @staticmethod
    def query_environment_groups(session, uri):
        return session.query(EnvironmentGroup).filter(EnvironmentGroup.environmentUri == uri).all()

    @staticmethod
    def get_environment_consumption_role_by_name(session, uri, IAMRoleName):
        return (
            session.query(ConsumptionRole)
            .filter(
                and_(
                    ConsumptionRole.environmentUri == uri,
                    ConsumptionRole.IAMRoleName == IAMRoleName,
                )
            )
            .first()
        )

    @staticmethod
    def get_all_envs_by_organization(session, uri):
        return session.query(Environment).filter(Environment.organizationUri == uri).all()

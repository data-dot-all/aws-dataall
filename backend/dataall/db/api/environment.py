import logging
import re

from sqlalchemy import or_
from sqlalchemy.orm import Query
from sqlalchemy.sql import and_

from .. import exceptions, permissions, models
from . import (
    KeyValueTag
)
from ..api.organization import Organization
from ..models import EnvironmentGroup
from ..models.Enums import (
    EnvironmentType,
    EnvironmentPermission,
)
from ..paginator import paginate
from dataall.core.environment.models import EnvironmentParameter
from dataall.core.environment.db.repositories import EnvironmentParameterRepository
from dataall.utils.naming_convention import (
    NamingConventionService,
    NamingConventionPattern,
)
from dataall.core.group.services.environment_resource_manager import EnvironmentResourceManager
from dataall.core.permissions.permission_checker import has_resource_permission, has_tenant_permission
from dataall.base.context import get_context
from dataall.core.permissions.db.permission import Permission
from dataall.core.permissions.db.resource_policy import ResourcePolicy
from ...core.permissions.db.permission_models import PermissionType

log = logging.getLogger(__name__)


class Environment:
    @staticmethod
    @has_tenant_permission(permissions.MANAGE_ENVIRONMENTS)
    @has_resource_permission(permissions.LINK_ENVIRONMENT)
    def create_environment(session, uri, data=None):
        context = get_context()
        Environment._validate_creation_params(data, uri)
        organization = Organization.get_organization_by_uri(session, uri)
        env = models.Environment(
            organizationUri=data.get('organizationUri'),
            label=data.get('label', 'Unnamed'),
            tags=data.get('tags', []),
            owner=context.username,
            description=data.get('description', ''),
            environmentType=data.get('type', EnvironmentType.Data.value),
            AwsAccountId=data.get('AwsAccountId'),
            region=data.get('region'),
            SamlGroupName=data['SamlGroupName'],
            validated=False,
            isOrganizationDefaultEnvironment=False,
            userRoleInEnvironment=EnvironmentPermission.Owner.value,
            EnvironmentDefaultIAMRoleName=data.get(
                'EnvironmentDefaultIAMRoleName', 'unknown'
            ),
            EnvironmentDefaultIAMRoleArn=f'arn:aws:iam::{data.get("AwsAccountId")}:role/{data.get("EnvironmentDefaultIAMRoleName")}',
            CDKRoleArn=f"arn:aws:iam::{data.get('AwsAccountId')}:role/{data['cdk_role_name']}",
            warehousesEnabled=data.get('warehousesEnabled', True),
            resourcePrefix=data.get('resourcePrefix'),
        )

        session.add(env)
        session.commit()

        Environment._update_env_parameters(session, env, data)

        env.EnvironmentDefaultBucketName = NamingConventionService(
            target_uri=env.environmentUri,
            target_label=env.label,
            pattern=NamingConventionPattern.S3,
            resource_prefix=env.resourcePrefix,
        ).build_compliant_name()

        env.EnvironmentDefaultAthenaWorkGroup = NamingConventionService(
            target_uri=env.environmentUri,
            target_label=env.label,
            pattern=NamingConventionPattern.DEFAULT,
            resource_prefix=env.resourcePrefix,
        ).build_compliant_name()

        if not data.get('EnvironmentDefaultIAMRoleName'):
            env_role_name = NamingConventionService(
                target_uri=env.environmentUri,
                target_label=env.label,
                pattern=NamingConventionPattern.IAM,
                resource_prefix=env.resourcePrefix,
            ).build_compliant_name()
            env.EnvironmentDefaultIAMRoleName = env_role_name
            env.EnvironmentDefaultIAMRoleArn = (
                f'arn:aws:iam::{env.AwsAccountId}:role/{env_role_name}'
            )
            env.EnvironmentDefaultIAMRoleImported = False
        else:
            env.EnvironmentDefaultIAMRoleName = data['EnvironmentDefaultIAMRoleName']
            env.EnvironmentDefaultIAMRoleArn = f'arn:aws:iam::{env.AwsAccountId}:role/{env.EnvironmentDefaultIAMRoleName}'
            env.EnvironmentDefaultIAMRoleImported = True

        if data.get('vpcId'):
            vpc = models.Vpc(
                environmentUri=env.environmentUri,
                region=env.region,
                AwsAccountId=env.AwsAccountId,
                VpcId=data.get('vpcId'),
                privateSubnetIds=data.get('privateSubnetIds', []),
                publicSubnetIds=data.get('publicSubnetIds', []),
                SamlGroupName=data['SamlGroupName'],
                owner=context.username,
                label=f"{env.name}-{data.get('vpcId')}",
                name=f"{env.name}-{data.get('vpcId')}",
                default=True,
            )
            session.add(vpc)
            session.commit()
            ResourcePolicy.attach_resource_policy(
                session=session,
                group=data['SamlGroupName'],
                permissions=permissions.NETWORK_ALL,
                resource_uri=vpc.vpcUri,
                resource_type=models.Vpc.__name__,
            )
        env_group = models.EnvironmentGroup(
            environmentUri=env.environmentUri,
            groupUri=data['SamlGroupName'],
            groupRoleInEnvironment=EnvironmentPermission.Owner.value,
            environmentIAMRoleArn=env.EnvironmentDefaultIAMRoleArn,
            environmentIAMRoleName=env.EnvironmentDefaultIAMRoleName,
            environmentAthenaWorkGroup=env.EnvironmentDefaultAthenaWorkGroup,
        )
        session.add(env_group)
        ResourcePolicy.attach_resource_policy(
            session=session,
            resource_uri=env.environmentUri,
            group=data['SamlGroupName'],
            permissions=permissions.ENVIRONMENT_ALL,
            resource_type=models.Environment.__name__,
        )
        session.commit()

        activity = models.Activity(
            action='ENVIRONMENT:CREATE',
            label='ENVIRONMENT:CREATE',
            owner=context.username,
            summary=f'{context.username} linked environment {env.AwsAccountId} to organization {organization.name}',
            targetUri=env.environmentUri,
            targetType='env',
        )
        session.add(activity)
        return env

    @staticmethod
    def _validate_creation_params(data, uri):
        if not uri:
            raise exceptions.RequiredParameter('organizationUri')
        if not data:
            raise exceptions.RequiredParameter('data')
        if not data.get('label'):
            raise exceptions.RequiredParameter('label')
        if not data.get('SamlGroupName'):
            raise exceptions.RequiredParameter('group')
        Environment._validate_resource_prefix(data)

    @staticmethod
    def _validate_resource_prefix(data):
        if data.get('resourcePrefix') and not bool(
            re.match(r'^[a-z-]+$', data.get('resourcePrefix'))
        ):
            raise exceptions.InvalidInput(
                'resourcePrefix',
                data.get('resourcePrefix'),
                'must match the pattern ^[a-z-]+$',
            )

    @staticmethod
    @has_tenant_permission(permissions.MANAGE_ENVIRONMENTS)
    @has_resource_permission(permissions.UPDATE_ENVIRONMENT)
    def update_environment(session, uri, data=None):
        Environment._validate_resource_prefix(data)
        environment = Environment.get_environment_by_uri(session, uri)
        if data.get('label'):
            environment.label = data.get('label')
        if data.get('description'):
            environment.description = data.get('description', 'No description provided')
        if data.get('tags'):
            environment.tags = data.get('tags')
        if 'warehousesEnabled' in data.keys():
            environment.warehousesEnabled = data.get('warehousesEnabled')
        if data.get('resourcePrefix'):
            environment.resourcePrefix = data.get('resourcePrefix')

        Environment._update_env_parameters(session, environment, data)

        ResourcePolicy.attach_resource_policy(
            session=session,
            resource_uri=environment.environmentUri,
            group=environment.SamlGroupName,
            permissions=permissions.ENVIRONMENT_ALL,
            resource_type=models.Environment.__name__,
        )
        return environment

    @staticmethod
    def _update_env_parameters(session, env: models.Environment, data):
        """Removes old parameters and creates new parameters associated with the environment"""
        params = data.get("parameters")
        if not params:
            return

        env_uri = env.environmentUri
        new_params = [EnvironmentParameter(
            env_uri, param.get("key"), param.get("value")
        ) for param in params]
        EnvironmentParameterRepository(session).update_params(env_uri, new_params)

    @staticmethod
    @has_tenant_permission(permissions.MANAGE_ENVIRONMENTS)
    @has_resource_permission(permissions.INVITE_ENVIRONMENT_GROUP)
    def invite_group(session, uri, data=None) -> (models.Environment, models.EnvironmentGroup):
        Environment.validate_invite_params(data)

        group: str = data['groupUri']

        Environment.validate_permissions(session, uri, data['permissions'], group)

        environment = Environment.get_environment_by_uri(session, uri)

        group_membership = Environment.find_environment_group(
            session, group, environment.environmentUri
        )
        if group_membership:
            raise exceptions.UnauthorizedOperation(
                action='INVITE_TEAM',
                message=f'Team {group} is already a member of the environment {environment.name}',
            )

        if data.get('environmentIAMRoleName'):
            env_group_iam_role_name = data['environmentIAMRoleName']
            env_role_imported = True
        else:
            env_group_iam_role_name = NamingConventionService(
                target_uri=environment.environmentUri,
                target_label=group,
                pattern=NamingConventionPattern.IAM,
                resource_prefix=environment.resourcePrefix,
            ).build_compliant_name()
            env_role_imported = False

        athena_workgroup = NamingConventionService(
            target_uri=environment.environmentUri,
            target_label=group,
            pattern=NamingConventionPattern.DEFAULT,
            resource_prefix=environment.resourcePrefix,
        ).build_compliant_name()

        environment_group = EnvironmentGroup(
            environmentUri=environment.environmentUri,
            groupUri=group,
            invitedBy=get_context().username,
            environmentIAMRoleName=env_group_iam_role_name,
            environmentIAMRoleArn=f'arn:aws:iam::{environment.AwsAccountId}:role/{env_group_iam_role_name}',
            environmentIAMRoleImported=env_role_imported,
            environmentAthenaWorkGroup=athena_workgroup,
        )
        session.add(environment_group)
        session.commit()
        ResourcePolicy.attach_resource_policy(
            session=session,
            group=group,
            resource_uri=environment.environmentUri,
            permissions=data['permissions'],
            resource_type=models.Environment.__name__,
        )
        return environment, environment_group

    @staticmethod
    def validate_permissions(session, uri, g_permissions, group):
        if permissions.CREATE_REDSHIFT_CLUSTER in g_permissions:
            g_permissions.append(permissions.LIST_ENVIRONMENT_REDSHIFT_CLUSTERS)

        if permissions.INVITE_ENVIRONMENT_GROUP in g_permissions:
            g_permissions.append(permissions.LIST_ENVIRONMENT_GROUPS)
            g_permissions.append(permissions.REMOVE_ENVIRONMENT_GROUP)

        if permissions.ADD_ENVIRONMENT_CONSUMPTION_ROLES in g_permissions:
            g_permissions.append(permissions.LIST_ENVIRONMENT_CONSUMPTION_ROLES)

        if permissions.CREATE_NETWORK in g_permissions:
            g_permissions.append(permissions.LIST_ENVIRONMENT_NETWORKS)

        g_permissions.append(permissions.GET_ENVIRONMENT)
        g_permissions.append(permissions.LIST_ENVIRONMENT_GROUPS)
        g_permissions.append(permissions.LIST_ENVIRONMENT_GROUP_PERMISSIONS)
        g_permissions.append(permissions.LIST_ENVIRONMENT_REDSHIFT_CLUSTERS)
        g_permissions.append(permissions.LIST_ENVIRONMENT_NETWORKS)
        g_permissions.append(permissions.CREDENTIALS_ENVIRONMENT)

        g_permissions = list(set(g_permissions))

        if g_permissions not in permissions.ENVIRONMENT_INVITED:
            exceptions.PermissionUnauthorized(
                action='INVITE_TEAM', group_name=group, resource_uri=uri
            )

        env_group_permissions = []
        for p in g_permissions:
            env_group_permissions.append(
                Permission.find_permission_by_name(
                    session=session,
                    permission_name=p,
                    permission_type=PermissionType.RESOURCE.name,
                )
            )

    @staticmethod
    @has_tenant_permission(permissions.MANAGE_ENVIRONMENTS)
    @has_resource_permission(permissions.REMOVE_ENVIRONMENT_GROUP)
    def remove_group(session, uri, group):
        environment = Environment.get_environment_by_uri(session, uri)

        if group == environment.SamlGroupName:
            raise exceptions.UnauthorizedOperation(
                action='REMOVE_TEAM',
                message=f'Team: {group} is the owner of the environment {environment.name}',
            )

        group_env_objects_count = (
            session.query(models.Environment)
            .outerjoin(
                models.RedshiftCluster,
                models.RedshiftCluster.environmentUri
                == models.Environment.environmentUri,
            )
            .filter(
                and_(
                    models.Environment.environmentUri == environment.environmentUri,
                    or_(
                        models.RedshiftCluster.SamlGroupName == group,
                    ),
                )
            )
            .count()
        )

        group_env_objects_count += EnvironmentResourceManager.count_group_resources(
            session=session,
            environment=environment,
            group_uri=group
        )

        if group_env_objects_count > 0:
            raise exceptions.EnvironmentResourcesFound(
                action='Remove Team',
                message=f'Team: {group} has created {group_env_objects_count} resources on this environment.',
            )

        group_membership = Environment.find_environment_group(
            session, group, environment.environmentUri
        )
        if group_membership:
            session.delete(group_membership)
            session.commit()

        ResourcePolicy.delete_resource_policy(
            session=session,
            group=group,
            resource_uri=environment.environmentUri,
            resource_type=models.Environment.__name__,
        )
        return environment

    @staticmethod
    @has_tenant_permission(permissions.MANAGE_ENVIRONMENTS)
    @has_resource_permission(permissions.UPDATE_ENVIRONMENT_GROUP)
    def update_group_permissions(session, uri, data=None):
        Environment.validate_invite_params(data)

        group = data['groupUri']

        Environment.validate_permissions(session, uri, data['permissions'], group)

        environment = Environment.get_environment_by_uri(session, uri)

        group_membership = Environment.find_environment_group(
            session, group, environment.environmentUri
        )
        if not group_membership:
            raise exceptions.UnauthorizedOperation(
                action='UPDATE_TEAM_ENVIRONMENT_PERMISSIONS',
                message=f'Team {group.name} is not a member of the environment {environment.name}',
            )

        ResourcePolicy.delete_resource_policy(
            session=session,
            group=group,
            resource_uri=environment.environmentUri,
            resource_type=models.Environment.__name__,
        )
        ResourcePolicy.attach_resource_policy(
            session=session,
            group=group,
            resource_uri=environment.environmentUri,
            permissions=data['permissions'],
            resource_type=models.Environment.__name__,
        )
        return environment

    @staticmethod
    @has_resource_permission(permissions.LIST_ENVIRONMENT_GROUP_PERMISSIONS)
    def list_group_permissions(session, uri, group_uri):
        # the permission checked
        return Environment.list_group_permissions_internal(session, uri, group_uri)

    @staticmethod
    def list_group_permissions_internal(session, uri, group_uri):
        """No permission check, only for internal usages"""
        environment = Environment.get_environment_by_uri(session, uri)

        return ResourcePolicy.get_resource_policy_permissions(
            session=session,
            group_uri=group_uri,
            resource_uri=environment.environmentUri,
        )

    @staticmethod
    def list_group_invitation_permissions(
        session, username, groups, uri, data=None, check_perm=None
    ):
        group_invitation_permissions = []
        for p in permissions.ENVIRONMENT_INVITATION_REQUEST:
            group_invitation_permissions.append(
                Permission.find_permission_by_name(
                    session=session,
                    permission_name=p,
                    permission_type=PermissionType.RESOURCE.name,
                )
            )
        return group_invitation_permissions

    @staticmethod
    @has_tenant_permission(permissions.MANAGE_ENVIRONMENTS)
    @has_resource_permission(permissions.ADD_ENVIRONMENT_CONSUMPTION_ROLES)
    def add_consumption_role(session, uri, data=None) -> (models.Environment, models.EnvironmentGroup):

        group: str = data['groupUri']
        IAMRoleArn: str = data['IAMRoleArn']
        environment = Environment.get_environment_by_uri(session, uri)

        alreadyAdded = Environment.find_consumption_roles_by_IAMArn(
            session, environment.environmentUri, IAMRoleArn
        )
        if alreadyAdded:
            raise exceptions.UnauthorizedOperation(
                action='ADD_CONSUMPTION_ROLE',
                message=f'IAM role {IAMRoleArn} is already added to the environment {environment.name}',
            )

        consumption_role = models.ConsumptionRole(
            consumptionRoleName=data['consumptionRoleName'],
            environmentUri=environment.environmentUri,
            groupUri=group,
            IAMRoleArn=IAMRoleArn,
            IAMRoleName=IAMRoleArn.split("/")[-1],
        )

        session.add(consumption_role)
        session.commit()

        ResourcePolicy.attach_resource_policy(
            session=session,
            group=group,
            resource_uri=consumption_role.consumptionRoleUri,
            permissions=permissions.CONSUMPTION_ROLE_ALL,
            resource_type=models.ConsumptionRole.__name__,
        )
        return consumption_role

    @staticmethod
    @has_tenant_permission(permissions.MANAGE_ENVIRONMENTS)
    @has_resource_permission(permissions.REMOVE_ENVIRONMENT_CONSUMPTION_ROLE)
    def remove_consumption_role(session, uri, env_uri):
        consumption_role = Environment.get_environment_consumption_role(session, uri, env_uri)

        if consumption_role:
            session.delete(consumption_role)
            session.commit()

        ResourcePolicy.delete_resource_policy(
            session=session,
            group=consumption_role.groupUri,
            resource_uri=consumption_role.consumptionRoleUri,
            resource_type=models.ConsumptionRole.__name__,
        )
        return True

    @staticmethod
    def query_user_environments(session, username, groups, filter) -> Query:
        query = (
            session.query(models.Environment)
            .outerjoin(
                models.EnvironmentGroup,
                models.Environment.environmentUri
                == models.EnvironmentGroup.environmentUri,
            )
            .filter(
                or_(
                    models.Environment.owner == username,
                    models.EnvironmentGroup.groupUri.in_(groups),
                )
            )
        )
        if filter and filter.get('term'):
            term = filter['term']
            query = query.filter(
                or_(
                    models.Environment.label.ilike('%' + term + '%'),
                    models.Environment.description.ilike('%' + term + '%'),
                    models.Environment.tags.contains(f'{{{term}}}'),
                    models.Environment.region.ilike('%' + term + '%'),
                )
            )
        return query

    @staticmethod
    def paginated_user_environments(session, data=None) -> dict:
        context = get_context()
        return paginate(
            query=Environment.query_user_environments(session, context.username, context.groups, data),
            page=data.get('page', 1),
            page_size=data.get('pageSize', 5),
        ).to_dict()

    @staticmethod
    def query_user_environment_groups(session, groups, uri, filter) -> Query:
        query = (
            session.query(models.EnvironmentGroup)
            .filter(models.EnvironmentGroup.environmentUri == uri)
            .filter(models.EnvironmentGroup.groupUri.in_(groups))
        )
        if filter and filter.get('term'):
            term = filter['term']
            query = query.filter(
                or_(
                    models.EnvironmentGroup.groupUri.ilike('%' + term + '%'),
                )
            )
        return query

    @staticmethod
    @has_resource_permission(permissions.LIST_ENVIRONMENT_GROUPS)
    def paginated_user_environment_groups(session, uri, data=None) -> dict:
        return paginate(
            query=Environment.query_user_environment_groups(
                session, get_context().groups, uri, data
            ),
            page=data.get('page', 1),
            page_size=data.get('pageSize', 1000),
        ).to_dict()

    @staticmethod
    def query_all_environment_groups(session, uri, filter) -> Query:
        query = session.query(models.EnvironmentGroup).filter(
            models.EnvironmentGroup.environmentUri == uri
        )
        if filter and filter.get('term'):
            term = filter['term']
            query = query.filter(
                or_(
                    models.EnvironmentGroup.groupUri.ilike('%' + term + '%'),
                )
            )
        return query

    @staticmethod
    @has_resource_permission(permissions.LIST_ENVIRONMENT_GROUPS)
    def paginated_all_environment_groups(session, uri, data=None) -> dict:
        return paginate(
            query=Environment.query_all_environment_groups(
                session, uri, data
            ),
            page=data.get('page', 1),
            page_size=data.get('pageSize', 10),
        ).to_dict()

    @staticmethod
    @has_resource_permission(permissions.LIST_ENVIRONMENT_GROUPS)
    def list_environment_groups(session, uri) -> [str]:
        return [
            g.groupUri
            for g in Environment.query_user_environment_groups(
                session, get_context().groups, uri, {}
            ).all()
        ]

    @staticmethod
    def query_environment_invited_groups(session, uri, filter) -> Query:
        query = (
            session.query(models.EnvironmentGroup)
            .join(
                models.Environment,
                models.EnvironmentGroup.environmentUri
                == models.Environment.environmentUri,
            )
            .filter(
                and_(
                    models.Environment.environmentUri == uri,
                    models.EnvironmentGroup.groupUri
                    != models.Environment.SamlGroupName,
                )
            )
        )
        if filter and filter.get('term'):
            term = filter['term']
            query = query.filter(
                or_(
                    models.EnvironmentGroup.groupUri.ilike('%' + term + '%'),
                )
            )
        return query

    @staticmethod
    @has_resource_permission(permissions.LIST_ENVIRONMENT_GROUPS)
    def paginated_environment_invited_groups(session, uri, data=None) -> dict:
        return paginate(
            query=Environment.query_environment_invited_groups(session, uri, data),
            page=data.get('page', 1),
            page_size=data.get('pageSize', 10),
        ).to_dict()

    @staticmethod
    def list_environment_invited_groups(session, uri):
        return Environment.query_environment_invited_groups(session, uri, {}).all()

    @staticmethod
    def query_user_environment_consumption_roles(session, groups, uri, filter) -> Query:
        query = (
            session.query(models.ConsumptionRole)
            .filter(models.ConsumptionRole.environmentUri == uri)
            .filter(models.ConsumptionRole.groupUri.in_(groups))
        )
        if filter and filter.get('term'):
            term = filter['term']
            query = query.filter(
                or_(
                    models.ConsumptionRole.consumptionRoleName.ilike('%' + term + '%'),
                )
            )
        if filter and filter.get('groupUri'):
            print("filter group")
            group = filter['groupUri']
            query = query.filter(
                or_(
                    models.ConsumptionRole.groupUri == group,
                )
            )
        return query

    @staticmethod
    @has_resource_permission(permissions.LIST_ENVIRONMENT_CONSUMPTION_ROLES)
    def paginated_user_environment_consumption_roles(session, uri, data=None) -> dict:
        return paginate(
            query=Environment.query_user_environment_consumption_roles(
                session, get_context().groups, uri, data
            ),
            page=data.get('page', 1),
            page_size=data.get('pageSize', 1000),
        ).to_dict()

    @staticmethod
    def query_all_environment_consumption_roles(session, uri, filter) -> Query:
        query = session.query(models.ConsumptionRole).filter(
            models.ConsumptionRole.environmentUri == uri
        )
        if filter and filter.get('term'):
            term = filter['term']
            query = query.filter(
                or_(
                    models.ConsumptionRole.consumptionRoleName.ilike('%' + term + '%'),
                )
            )
        if filter and filter.get('groupUri'):
            group = filter['groupUri']
            query = query.filter(
                or_(
                    models.ConsumptionRole.groupUri == group,
                )
            )
        return query

    @staticmethod
    @has_resource_permission(permissions.LIST_ENVIRONMENT_CONSUMPTION_ROLES)
    def paginated_all_environment_consumption_roles(
        session, uri, data=None
    ) -> dict:
        return paginate(
            query=Environment.query_all_environment_consumption_roles(
                session, uri, data
            ),
            page=data.get('page', 1),
            page_size=data.get('pageSize', 10),
        ).to_dict()

    @staticmethod
    def find_consumption_roles_by_IAMArn(session, uri, arn) -> Query:
        return session.query(models.ConsumptionRole).filter(
            and_(
                models.ConsumptionRole.environmentUri == uri,
                models.ConsumptionRole.IAMRoleArn == arn
            )
        ).first()

    @staticmethod
    def query_environment_networks(session, uri, filter) -> Query:
        query = session.query(models.Vpc).filter(
            models.Vpc.environmentUri == uri,
        )
        if filter.get('term'):
            term = filter.get('term')
            query = query.filter(
                or_(
                    models.Vpc.label.ilike('%' + term + '%'),
                    models.Vpc.VpcId.ilike('%' + term + '%'),
                )
            )
        return query

    @staticmethod
    @has_resource_permission(permissions.LIST_ENVIRONMENT_NETWORKS)
    def paginated_environment_networks(session, uri, data=None) -> dict:
        return paginate(
            query=Environment.query_environment_networks(session, uri, data),
            page=data.get('page', 1),
            page_size=data.get('pageSize', 10),
        ).to_dict()

    @staticmethod
    def validate_invite_params(data):
        if not data:
            raise exceptions.RequiredParameter('data')
        if not data.get('groupUri'):
            raise exceptions.RequiredParameter('groupUri')
        if not data.get('permissions'):
            raise exceptions.RequiredParameter('permissions')

    @staticmethod
    def find_environment_group(session, group_uri, environment_uri):
        try:
            env_group = Environment.get_environment_group(session, group_uri, environment_uri)
            return env_group
        except Exception:
            return None

    @staticmethod
    def get_environment_group(session, group_uri, environment_uri):
        env_group = (
            session.query(models.EnvironmentGroup)
            .filter(
                (
                    and_(
                        models.EnvironmentGroup.groupUri == group_uri,
                        models.EnvironmentGroup.environmentUri == environment_uri,
                    )
                )
            )
            .first()
        )
        if not env_group:
            raise exceptions.ObjectNotFound(
                'EnvironmentGroup', f'({group_uri},{environment_uri})'
            )
        return env_group

    @staticmethod
    def get_environment_consumption_role(session, role_uri, environment_uri):
        role = (
            session.query(models.ConsumptionRole)
            .filter(
                (
                    and_(
                        models.ConsumptionRole.consumptionRoleUri == role_uri,
                        models.ConsumptionRole.environmentUri == environment_uri,
                    )
                )
            )
            .first()
        )
        if not role:
            raise exceptions.ObjectNotFound(
                'ConsumptionRoleUri', f'({role_uri},{environment_uri})'
            )
        return role

    @staticmethod
    def get_environment_by_uri(session, uri) -> models.Environment:
        if not uri:
            raise exceptions.RequiredParameter('environmentUri')
        environment: models.Environment = session.query(models.Environment).get(uri)
        if not environment:
            raise exceptions.ObjectNotFound(models.Environment.__name__, uri)
        return environment

    @staticmethod
    @has_resource_permission(permissions.GET_ENVIRONMENT)
    def find_environment_by_uri(session, uri) -> models.Environment:
        return Environment.get_environment_by_uri(session, uri)

    @staticmethod
    def list_all_active_environments(session) -> [models.Environment]:
        """
        Lists all active dataall environments
        :param session:
        :return: [models.Environment]
        """
        environments: [models.Environment] = (
            session.query(models.Environment)
            .filter(models.Environment.deleted.is_(None))
            .all()
        )
        log.info(
            f'Retrieved all active dataall environments {[e.AwsAccountId for e in environments]}'
        )
        return environments

    @staticmethod
    def list_environment_redshift_clusters_query(session, environment_uri, filter):
        q = session.query(models.RedshiftCluster).filter(
            models.RedshiftCluster.environmentUri == environment_uri
        )
        term = filter.get('term', None)
        if term:
            q = q.filter(
                or_(
                    models.RedshiftCluster.label.ilike('%' + term + '%'),
                    models.RedshiftCluster.description.ilike('%' + term + '%'),
                )
            )
        return q

    @staticmethod
    @has_resource_permission(permissions.LIST_ENVIRONMENT_REDSHIFT_CLUSTERS)
    def paginated_environment_redshift_clusters(session, uri, data=None):
        query = Environment.list_environment_redshift_clusters_query(session, uri, data)
        return paginate(
            query=query,
            page_size=data.get('pageSize', 10),
            page=data.get('page', 1),
        ).to_dict()

    @staticmethod
    @has_resource_permission(permissions.GET_ENVIRONMENT)
    def get_stack(session, uri, stack_uri) -> models.Stack:
        return session.query(models.Stack).get(stack_uri)

    @staticmethod
    @has_resource_permission(permissions.DELETE_ENVIRONMENT)
    def delete_environment(session, uri, environment):
        env_groups = (
            session.query(models.EnvironmentGroup)
            .filter(models.EnvironmentGroup.environmentUri == uri)
            .all()
        )
        for group in env_groups:

            session.delete(group)

            ResourcePolicy.delete_resource_policy(
                session=session,
                resource_uri=uri,
                group=group.groupUri,
            )

        env_roles = (
            session.query(models.ConsumptionRole)
            .filter(models.ConsumptionRole.environmentUri == uri)
            .all()
        )
        for role in env_roles:
            session.delete(role)

        KeyValueTag.delete_key_value_tags(
            session, environment.environmentUri, 'environment'
        )

        EnvironmentResourceManager.delete_env(session, environment)
        EnvironmentParameterRepository(session).delete_params(environment.environmentUri)

        return session.delete(environment)

    @staticmethod
    def get_environment_parameters(session, env_uri):
        return EnvironmentParameterRepository(session).get_params(env_uri)

    @staticmethod
    def get_boolean_env_param(session, env: models.Environment, param: str) -> bool:
        param = EnvironmentParameterRepository(session).get_param(env.environmentUri, param)
        return param and param.value.lower() == "true"

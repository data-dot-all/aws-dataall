import json
import logging

from dataall.base.aws.sts import SessionHelper
from dataall.core.environment.db.environment_models import Environment
from dataall.core.environment.services.managed_iam_policies import PolicyManager
from dataall.core.environment.services.environment_resource_manager import EnvironmentResourceManager
from dataall.core.environment.services.environment_service import EnvironmentService
from dataall.core.stacks.services.stack_service import StackService

from dataall.core.vpc.services.vpc_service import VpcService

from dataall.base.feature_toggle_checker import is_feature_enabled

from dataall.core.organizations.api.resolvers import Context, exceptions, get_organization_simplified

log = logging.getLogger()


def get_trust_account(context: Context, source, organizationUri):
    return EnvironmentService.get_trust_account(uri=organizationUri)


def create_environment(context: Context, source, input={}):
    env = EnvironmentService.create_environment(
        uri=input.get('organizationUri'),
        data=input,
    )
    StackService.create_stack(
        environment_uri=env.environmentUri, target_type='environment', target_uri=env.environmentUri
    )

    StackService.deploy_stack(targetUri=env.environmentUri)
    return env


def update_environment(context: Context, source, environmentUri: str = None, input: dict = None):
    environment, previous_resource_prefix = EnvironmentService.update_environment(
        uri=environmentUri,
        data=input,
    )

    if EnvironmentResourceManager.deploy_updated_stack(previous_resource_prefix, environment, data=input):
        StackService.deploy_stack(targetUri=environment.environmentUri)

    return environment


def invite_group(context: Context, source, input):
    environment, environment_group = EnvironmentService.invite_group(
        uri=input['environmentUri'],
        data=input,
    )

    StackService.deploy_stack(targetUri=environment.environmentUri)

    return environment


def add_consumption_role(context: Context, source, input):
    consumption_role = EnvironmentService.add_consumption_role(
        uri=input['environmentUri'],
        data=input,
    )
    return consumption_role


def update_group_permissions(context, source, input):
    environment = EnvironmentService.update_group_permissions(
        uri=input['environmentUri'],
        data=input,
    )

    StackService.deploy_stack(targetUri=environment.environmentUri)

    return environment


def remove_group(context: Context, source, environmentUri=None, groupUri=None):
    environment = EnvironmentService.remove_group(
        uri=environmentUri,
        group=groupUri,
    )

    StackService.deploy_stack(targetUri=environment.environmentUri)

    return environment


def remove_consumption_role(context: Context, source, environmentUri=None, consumptionRoleUri=None):
    status = EnvironmentService.remove_consumption_role(
        uri=consumptionRoleUri,
        env_uri=environmentUri,
    )

    return status


def update_consumption_role(context: Context, source, environmentUri=None, consumptionRoleUri=None, input={}):
    consumption_role = EnvironmentService.update_consumption_role(
        uri=consumptionRoleUri,
        env_uri=environmentUri,
        input=input,
    )
    return consumption_role


def list_environment_invited_groups(context: Context, source, environmentUri=None, filter=None):
    return EnvironmentService.paginated_environment_invited_groups(
        uri=environmentUri,
        data=filter,
    )


def list_environment_groups(context: Context, source, environmentUri=None, filter=None):
    return EnvironmentService.paginated_user_environment_groups(
        uri=environmentUri,
        data=filter,
    )


def list_all_environment_groups(context: Context, source, environmentUri=None, filter=None):
    return EnvironmentService.paginated_all_environment_groups(
        uri=environmentUri,
        data=filter,
    )


def list_environment_consumption_roles(context: Context, source, environmentUri=None, filter=None):
    return EnvironmentService.paginated_user_environment_consumption_roles(
        uri=environmentUri,
        data=filter,
    )


def list_all_environment_consumption_roles(context: Context, source, environmentUri=None, filter=None):
    return EnvironmentService.paginated_all_environment_consumption_roles(
        uri=environmentUri,
        data=filter,
    )


def list_environment_group_invitation_permissions(
    context: Context,
    source,
):
    return EnvironmentService.list_group_invitation_permissions()


def list_environments(context: Context, source, filter=None):
    return EnvironmentService.paginated_user_environments(filter)


def list_valid_environments(context: Context, source, filter=None):
    return EnvironmentService.list_valid_user_environments(filter)


def list_groups(context: Context, source, filter=None):
    return EnvironmentService.paginated_user_groups(filter)


def list_consumption_roles(context: Context, source, filter=None):
    return EnvironmentService.paginated_user_consumption_roles(filter)


def list_environment_networks(context: Context, source, environmentUri=None, filter=None):
    return EnvironmentService.paginated_environment_networks(
        uri=environmentUri,
        data=filter,
    )


def get_parent_organization(context: Context, source, **kwargs):
    org = get_organization_simplified(context, source, organizationUri=source.organizationUri)
    return org


# used from getConsumptionRolePolicies query -- query resolver
def get_consumption_role_policies(context: Context, source, environmentUri, IAMRoleName):
    return EnvironmentService.resolve_consumption_role_policies(uri=environmentUri, IAMRoleName=IAMRoleName)


def resolve_environment_networks(context: Context, source, **kwargs):
    return VpcService.get_environment_networks(environment_uri=source.environmentUri)


def get_environment(context: Context, source, environmentUri: str = None):
    return EnvironmentService.find_environment_by_uri(uri=environmentUri)


def resolve_user_role(context: Context, source: Environment):
    return EnvironmentService.resolve_user_role(environment=source)


def list_environment_group_permissions(context, source, environmentUri: str = None, groupUri: str = None):
    return EnvironmentService.list_group_permissions(uri=environmentUri, group_uri=groupUri)


@is_feature_enabled('core.features.env_aws_actions')
def get_environment_assume_role_url(
    context: Context,
    source,
    environmentUri: str = None,
    groupUri: str = None,
):
    return EnvironmentService.get_environment_assume_role_url(uri=environmentUri, groupUri=groupUri)


@is_feature_enabled('core.features.env_aws_actions')
def generate_environment_access_token(context, source, environmentUri: str = None, groupUri: str = None):
    credentials = EnvironmentService.generate_environment_access_token(uri=environmentUri, groupUri=groupUri)
    return json.dumps(credentials)


def get_environment_stack(context: Context, source: Environment, **kwargs):
    return StackService.resolve_parent_obj_stack(
        targetUri=source.environmentUri,
        targetType='environment',
        environmentUri=source.environmentUri,
    )


def delete_environment(context: Context, source, environmentUri: str = None, deleteFromAWS: bool = False):
    session_response, environment = EnvironmentService.delete_environment(uri=environmentUri)

    if deleteFromAWS:
        StackService.delete_stack(
            target_uri=environmentUri,
            accountid=environment.AwsAccountId,
            cdk_role_arn=environment.CDKRoleArn,
            region=environment.region,
        )

    return True


def enable_subscriptions(context: Context, source, environmentUri: str = None, input: dict = None):
    EnvironmentService.enable_subscriptions(uri=environmentUri, input=input)
    StackService.deploy_stack(targetUri=environmentUri)
    return True


def disable_subscriptions(context: Context, source, environmentUri: str = None):
    EnvironmentService.disable_subscriptions(uri=environmentUri)
    StackService.deploy_stack(targetUri=environmentUri)
    return True


def get_pivot_role_template(context: Context, source, organizationUri=None):
    return EnvironmentService.get_template_from_resource_bucket(uri=organizationUri, template_name='pivot_role_prefix')


def get_cdk_exec_policy_template(context: Context, source, organizationUri=None):
    return EnvironmentService.get_template_from_resource_bucket(
        uri=organizationUri, template_name='cdk_exec_policy_prefix'
    )


def get_external_id(context: Context, source, organizationUri=None):
    return EnvironmentService.get_external_id(uri=organizationUri)


def get_pivot_role_name(context: Context, source, organizationUri=None):
    return EnvironmentService.get_pivot_role(uri=organizationUri)


def resolve_environment(context, source, **kwargs):
    """Resolves the environment for a environmental resource"""
    if not source:
        return None
    return EnvironmentService.find_environment_by_uri(uri=source.environmentUri)


def resolve_parameters(context, source: Environment, **kwargs):
    """Resolves a parameters for the environment"""
    if not source:
        return None
    return EnvironmentService.get_environment_parameters(source.environmentUri)

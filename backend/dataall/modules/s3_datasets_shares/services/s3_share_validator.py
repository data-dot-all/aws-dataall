from dataall.base.db.exceptions import UnauthorizedOperation, InvalidInput
from dataall.base.aws.iam import IAM
from dataall.core.environment.services.environment_service import EnvironmentService
from dataall.core.environment.db.environment_models import EnvironmentGroup, ConsumptionRole
from dataall.core.environment.services.managed_iam_policies import PolicyManager
from dataall.modules.shares_base.db.share_object_models import ShareObject
from dataall.modules.shares_base.services.share_object_service import SharesValidatorInterface
from dataall.modules.shares_base.services.shares_enums import (
    PrincipalType,
    ShareObjectDataPermission,
)
from dataall.modules.shares_base.services.share_exceptions import PrincipalRoleNotFound
from dataall.modules.shares_base.services.share_permissions import (
    APPROVE_SHARE_OBJECT,
    SUBMIT_SHARE_OBJECT,
    CREATE_SHARE_OBJECT,
)

import logging

log = logging.getLogger(__name__)


class S3ShareValidator(SharesValidatorInterface):
    @staticmethod
    def validate_share_object_create(
        session,
        dataset,
        group_uri,
        environment,
        principal_type,
        principal_id,
        principal_role_name,
        attachMissingPolicies,
        permissions,
    ) -> bool:
        log.info('Verifying S3 share request input')

        if (
            (dataset.stewards == group_uri or dataset.SamlAdminGroupName == group_uri)
            and environment.environmentUri == dataset.environmentUri
            and principal_type == PrincipalType.Group.value
        ):
            raise UnauthorizedOperation(
                action=CREATE_SHARE_OBJECT,
                message=f'Team: {group_uri} is managing the dataset {dataset.name}',
            )
        if environment.region != dataset.region:
            raise UnauthorizedOperation(
                action=CREATE_SHARE_OBJECT,
                message=f'Requester Team {group_uri} works in region {environment.region} '
                f'and the requested dataset is stored in region {dataset.region}',
            )
        S3ShareValidator._validate_iam_role_and_policy(
            session, environment, principal_type, principal_id, group_uri, attachMissingPolicies
        )
        S3ShareValidator._validate_write_request_in_same_account(
            source_account=dataset.AwsAccountId, target_account=environment.AwsAccountId, permissions=permissions
        )

        return True

    @staticmethod
    def validate_share_object_submit(session, dataset, share) -> bool:
        if not S3ShareValidator._validate_iam_role(session, share):
            raise PrincipalRoleNotFound(
                action=SUBMIT_SHARE_OBJECT,
                message=f'The principal role {share.principalRoleName} is not found.',
            )
        return True

    @staticmethod
    def validate_share_object_approve(session, dataset, share) -> bool:
        if not S3ShareValidator._validate_iam_role(session, share):
            raise PrincipalRoleNotFound(
                action=APPROVE_SHARE_OBJECT,
                message=f'The principal role {share.principalRoleName} is not found.',
            )
        return True

    @staticmethod
    def _validate_iam_role(session, share: ShareObject) -> bool:
        log.info('Verifying principal IAM role...')
        role_name = share.principalRoleName
        env = EnvironmentService.get_environment_by_uri(session, share.environmentUri)
        principal_role = IAM.get_role_arn_by_name(account_id=env.AwsAccountId, region=env.region, role_name=role_name)
        return principal_role is not None

    @staticmethod
    def _validate_write_request_in_same_account(source_account, target_account, permissions):
        log.info('Verifying write request in same account...')
        if source_account != target_account and permissions != [ShareObjectDataPermission.Read.value]:
            raise InvalidInput(
                'Principal Role AWS account',
                target_account,
                f'be the same as the Dataset source account {source_account} when WRITE/MODIFY permissions are specified',
            )

    @staticmethod
    def _validate_iam_role_and_policy(
        session, environment, principal_type: str, principal_id: str, group_uri: str, attachMissingPolicies: bool
    ):
        if principal_type == PrincipalType.ConsumptionRole.value:
            consumption_role: ConsumptionRole = EnvironmentService.get_environment_consumption_role(
                session, principal_id, environment.environmentUri
            )
            principal_role_name = consumption_role.IAMRoleName
            managed = consumption_role.dataallManaged

        else:
            env_group: EnvironmentGroup = EnvironmentService.get_environment_group(
                session, group_uri, environment.environmentUri
            )
            principal_role_name = env_group.environmentIAMRoleName
            managed = True

        log.info(f'Verifying request IAM role {principal_role_name} exists...')
        if not IAM.get_role_arn_by_name(
            account_id=environment.AwsAccountId, region=environment.region, role_name=principal_role_name
        ):
            raise PrincipalRoleNotFound(
                action=principal_type,
                message=f'The principal role {principal_role_name} is not found.',
            )

        log.info('Verifying data.all managed share IAM policy is attached to IAM role...')
        share_policy_manager = PolicyManager(
            role_name=principal_role_name,
            environmentUri=environment.environmentUri,
            account=environment.AwsAccountId,
            region=environment.region,
            resource_prefix=environment.resourcePrefix,
        )
        for policy_manager in [
            Policy for Policy in share_policy_manager.initializedPolicies if Policy.policy_type == 'SharePolicy'
        ]:
            # Backwards compatibility - 1
            # we check if a managed share policy exists. If False, the role was introduced to data.all before this update
            # We create the policy from the inline statements
            # In this case it could also happen that the role is the Admin of the environment
            old_managed_policy_name = policy_manager.generate_old_policy_name()
            old_managed_policy_exists = policy_manager.check_if_policy_exists(policy_name=old_managed_policy_name)
            share_managed_policies_exist = True if policy_manager.get_managed_policies() else False
            # If old managed policy doesn't exist and also new managed policies do not exist.
            # Then there might be inline policies, convert them to managed indexed policies
            if not old_managed_policy_exists and not share_managed_policies_exist:
                policy_manager.create_managed_policy_from_inline_and_delete_inline()
            # End of backwards compatibility

            # Backwards compatibility - 2
            # Check if an already existing managed policy is present in old format
            # If yes, convert it to the indexed format
            old_managed_policy_name = policy_manager.generate_old_policy_name()
            if policy_manager.check_if_policy_exists(old_managed_policy_name):
                policy_manager.create_managed_indexed_policy_from_managed_policy_delete_old_policy()
            # End of backwards compatibility

            unattached = policy_manager.get_policies_unattached_to_role()
            if unattached and not managed and not attachMissingPolicies:
                raise Exception(
                    f'Required customer managed policies {policy_manager.get_policies_unattached_to_role()} are not attached to role {principal_role_name}'
                )
            elif unattached:
                managed_policy_list = policy_manager.get_policies_unattached_to_role()
                policy_manager.attach_policies(managed_policy_list)

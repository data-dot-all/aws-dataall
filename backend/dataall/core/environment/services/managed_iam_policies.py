from typing import List
import logging
import json
from abc import ABC, abstractmethod
from dataall.base.aws.iam import IAM

logger = logging.getLogger(__name__)


class ManagedPolicy(ABC):
    """
    Abstract class for any IAM Managed policy that needs to be atached to data.all team IAM roles and consumption roles
    """

    @abstractmethod
    def __init__(self, role_name, account, region, environmentUri, resource_prefix):
        self.role_name = role_name
        self.account = account
        self.region = region
        self.environmentUri = environmentUri
        self.resource_prefix = resource_prefix

    @property
    @abstractmethod
    def policy_type(self):
        """
        Returns string and needs to be implemented in the ManagedPolicies inherited classes
        """
        ...

    @abstractmethod
    def generate_old_policy_name(self) -> str:
        """
        Returns string and needs to be implemented in the ManagedPolicies inherited classes.
        Used for backwards compatibility. It should be deprecated in the future releases.
        """

    @abstractmethod
    def generate_base_policy_name(self) -> str:
        """
        Returns string and needs to be implemented in the ManagedPolicies inherited classes
        """
        ...

    @abstractmethod
    def generate_indexed_policy_name(self, index) -> str:
        """
        Returns string of policy name with index at the end .Needs to be implemented in the ManagedPolicies inherited classes
        """
        ...

    @abstractmethod
    def generate_empty_policy(self) -> dict:
        """
        Returns dict and needs to be implemented in the ManagedPolicies inherited classes
        """
        ...

    def check_if_policy_exists(self, policy_name) -> bool:
        policy = IAM.get_managed_policy_by_name(self.account, self.region, policy_name)
        return policy is not None

    def get_managed_policies(self) -> List[str]:
        policy_pattern = self.generate_base_policy_name()
        policies = self._get_policy_names(policy_pattern)
        return policies

    def check_if_policy_attached(self, policy_name):
        is_policy_attached = IAM.is_policy_attached(self.account, self.region, policy_name, self.role_name)
        return is_policy_attached

    def get_policies_unattached_to_role(self):
        policy_pattern = self.generate_base_policy_name()
        policies = self._get_policy_names(policy_pattern)
        unattached_policies = []
        for policy_name in policies:
            if not self.check_if_policy_attached(policy_name):
                unattached_policies.append(policy_name)
        return unattached_policies

    def attach_policies(self, managed_policies_list: List[str]):
        for policy_name in managed_policies_list:
            policy_arn = f'arn:aws:iam::{self.account}:policy/{policy_name}'
            try:
                IAM.attach_role_policy(self.account, self.region, self.role_name, policy_arn)
            except Exception as e:
                raise Exception(f"Required customer managed policy {policy_arn} can't be attached: {e}")

    def _get_policy_names(self, base_policy_name):
        filter_pattern = r'{base_policy_name}-\d'.format(base_policy_name=base_policy_name)
        policies = IAM.list_policy_names_by_policy_pattern(self.account, self.region, filter_pattern)
        return policies


class PolicyManager(object):
    def __init__(
        self,
        role_name,
        account,
        region,
        environmentUri,
        resource_prefix,
    ):
        self.role_name = role_name
        self.account = account
        self.region = region
        self.environmentUri = environmentUri
        self.resource_prefix = resource_prefix
        self.ManagedPolicies = ManagedPolicy.__subclasses__()
        logger.info(f'Found {len(self.ManagedPolicies)} subclasses of ManagedPolicy')
        self.initializedPolicies = [self._initialize_policy(policy) for policy in self.ManagedPolicies]

    def _initialize_policy(self, managedPolicy):
        return managedPolicy(
            role_name=self.role_name,
            account=self.account,
            region=self.region,
            environmentUri=self.environmentUri,
            resource_prefix=self.resource_prefix,
        )

    def create_all_policies(self, managed) -> bool:
        """
        Manager that registers and calls all policies created by data.all modules and that
        need to be created for consumption roles and team roles
        """
        for policy_manager in self.initializedPolicies:
            empty_policy = policy_manager.generate_empty_policy()
            policy_name = policy_manager.generate_indexed_policy_name(index=0)
            logger.info(f'Creating policy: {policy_name}')
            try:
                IAM.create_managed_policy(
                    account_id=self.account,
                    region=self.region,
                    policy_name=policy_name,
                    policy=json.dumps(empty_policy),
                )

                if managed:
                    IAM.attach_role_policy(
                        account_id=self.account,
                        region=self.region,
                        role_name=self.role_name,
                        policy_arn=f'arn:aws:iam::{self.account}:policy/{policy_name}',
                    )
            except Exception as e:
                logger.error(f'Error while creating and attaching policies due to: {e}')
                raise e
        return True

    def delete_all_policies(self) -> bool:
        """
        Manager that registers and calls all policies created by data.all modules and that
        need to be deleted for consumption roles and team roles
        """
        for policy_manager in self.initializedPolicies:
            policy_name_list = policy_manager.get_managed_policies()

            # Check if policy with old naming format exists
            if not policy_name_list:
                old_managed_policy_name = policy_manager.generate_old_policy_name()
                if policy_manager.check_if_policy_exists(policy_name=old_managed_policy_name):
                    policy_name_list.append(old_managed_policy_name)

            for policy_name in policy_name_list:
                logger.info(f'Deleting policy {policy_name}')
                try:
                    if policy_manager.check_if_policy_attached(policy_name=policy_name):
                        IAM.detach_policy_from_role(
                            account_id=self.account,
                            region=self.region,
                            role_name=self.role_name,
                            policy_name=policy_name,
                        )
                    if policy_manager.check_if_policy_exists(policy_name=policy_name):
                        IAM.delete_managed_policy_non_default_versions(
                            account_id=self.account, region=self.region, policy_name=policy_name
                        )
                        IAM.delete_managed_policy_by_name(
                            account_id=self.account, region=self.region, policy_name=policy_name
                        )
                except Exception as e:
                    logger.error(f'Error while deleting managed policies due to: {e}')
                    raise e
        return True

    def get_all_policies(self) -> List[dict]:
        """
        Manager that registers and calls all policies created by data.all modules and that
        need to be listed for consumption roles and team roles
        """
        all_policies = []
        for policy_manager in self.initializedPolicies:
            policy_name_list = policy_manager.get_managed_policies()

            # Check if policy with old naming format exists
            if not policy_name_list:
                old_managed_policy_name = policy_manager.generate_old_policy_name()
                if policy_manager.check_if_policy_exists(policy_name=old_managed_policy_name):
                    policy_name_list.append(old_managed_policy_name)

            for policy_name in policy_name_list:
                policy_dict = {
                    'policy_name': policy_name,
                    'policy_type': policy_manager.policy_type,
                    'exists': policy_manager.check_if_policy_exists(policy_name=policy_name),
                    'attached': policy_manager.check_if_policy_attached(policy_name=policy_name),
                }
                all_policies.append(policy_dict)
        logger.info(f'All policies currently added to role: {self.role_name} are: {str(all_policies)}')
        return all_policies

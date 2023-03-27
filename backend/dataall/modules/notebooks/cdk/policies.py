from dataall.cdkproxy.stacks.policies.service_policy import ServicePolicy

from dataall.modules.notebooks.services.permissions import CREATE_NOTEBOOK
from dataall.modules.common.sagemaker.statements import create_sagemaker_statements


class SagemakerPolicy(ServicePolicy):
    """
    Creates a sagemaker policy for accessing and interacting with notebooks
    """

    def get_statements(self, group_permissions, **kwargs):
        if CREATE_NOTEBOOK not in group_permissions:
            return []

        return create_sagemaker_statements(self.account, self.region, self.tag_key, self.tag_value)

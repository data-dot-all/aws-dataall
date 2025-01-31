"""Contains the code related to SageMaker notebooks"""

import logging

from dataall.base.loader import ImportMode, ModuleInterface
from dataall.modules.notebooks.db.notebook_models import SagemakerNotebook

log = logging.getLogger(__name__)


class NotebookApiModuleInterface(ModuleInterface):
    """Implements ModuleInterface for notebook GraphQl lambda"""

    @staticmethod
    def is_supported(modes):
        return ImportMode.API in modes

    def __init__(self):
        import dataall.modules.notebooks.api
        from dataall.core.stacks.db.target_type_repositories import TargetType
        from dataall.core.metadata_manager import MetadataFormEntityManager, MetadataFormEntityTypes
        from dataall.modules.notebooks.services.notebook_permissions import (
            GET_NOTEBOOK,
            UPDATE_NOTEBOOK,
            MANAGE_NOTEBOOKS,
        )

        TargetType('notebook', GET_NOTEBOOK, UPDATE_NOTEBOOK, MANAGE_NOTEBOOKS)
        MetadataFormEntityManager.register(SagemakerNotebook, MetadataFormEntityTypes.Notebooks.value)
        log.info('API of sagemaker notebooks has been imported')


class NotebookCdkModuleInterface(ModuleInterface):
    """Implements ModuleInterface for notebook ecs tasks"""

    @staticmethod
    def is_supported(modes):
        return ImportMode.CDK in modes

    def __init__(self):
        import dataall.modules.notebooks.cdk

        log.info('API of sagemaker notebooks has been imported')

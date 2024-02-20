"""Contains the code related to X"""
import logging
from typing import Set

from dataall.base.loader import ImportMode, ModuleInterface
from dataall.core.environment.services.environment_resource_manager import EnvironmentResourceManager
from dataall.modules.omics.db.omics_repository import OmicsRepository

log = logging.getLogger(__name__)

#todo: dependency on Datasets and CDK is wrong we need to update it for ECS
class OmicsApiModuleInterface(ModuleInterface):
    """Implements ModuleInterface for omics GraphQl lambda"""

    @staticmethod
    def is_supported(modes: Set[ImportMode]) -> bool:
        return ImportMode.API in modes

    def __init__(self):
        import dataall.modules.omics.api
        from dataall.modules.omics.services.omics_permissions import GET_OMICS_RUN, UPDATE_OMICS_RUN

        log.info("API of omics has been imported")


class OmicsCdkModuleInterface(ModuleInterface):
    """Implements ModuleInterface for omics ecs tasks"""

    @staticmethod
    def is_supported(modes: Set[ImportMode]) -> bool:
        return ImportMode.CDK in modes

    def __init__(self):
        import dataall.modules.omics.cdk
        log.info("API of Omics has been imported")

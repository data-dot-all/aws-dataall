"""Contains the code related to worksheets"""
import logging
from typing import Type, List

from dataall.core.environment.services.environment_resource_manager import EnvironmentResourceManager
from dataall.base.loader import ImportMode, ModuleInterface
from dataall.modules.worksheets.db.worksheet_models import Worksheet
from dataall.modules.worksheets.db.worksheet_repositories import WorksheetRepository

log = logging.getLogger(__name__)


class WorksheetApiModuleInterface(ModuleInterface):
    """Implements ModuleInterface for worksheet GraphQl lambda"""

    @staticmethod
    def is_supported(modes):
        return ImportMode.API in modes

    def __init__(self):
        import dataall.modules.worksheets.api

        EnvironmentResourceManager.register(WorksheetRepository())
        log.info("API of worksheets has been imported")

    @staticmethod
    def depends_on() -> List[Type['ModuleInterface']]:
        from dataall.modules.datasets import DatasetApiModuleInterface

        return [DatasetApiModuleInterface]


class WorksheetCdkModuleInterface(ModuleInterface):
    """Implements ModuleInterface for worksheet"""

    @staticmethod
    def is_supported(modes):
        return ImportMode.CDK in modes

    def __init__(self):
        import dataall.modules.worksheets.cdk

        log.info("CDK module of worksheets has been imported")

    @staticmethod
    def depends_on() -> List[Type['ModuleInterface']]:
        from dataall.modules.datasets import DatasetCdkModuleInterface

        return [DatasetCdkModuleInterface]

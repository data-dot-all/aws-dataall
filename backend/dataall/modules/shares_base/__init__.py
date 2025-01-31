import logging
from typing import Set, List, Type
from dataall.base.loader import ModuleInterface, ImportMode
from dataall.modules.shares_base.db.share_object_models import ShareObject, ShareObjectItem

log = logging.getLogger(__name__)


class SharesBaseAPIModuleInterface(ModuleInterface):
    @staticmethod
    def is_supported(modes: Set[ImportMode]) -> bool:
        return ImportMode.API in modes

    @staticmethod
    def depends_on() -> List[Type['ModuleInterface']]:
        from dataall.modules.datasets_base import DatasetBaseApiModuleInterface

        return [DatasetBaseApiModuleInterface]

    def __init__(self):
        import dataall.modules.shares_base.api
        from dataall.core.metadata_manager.metadata_form_entity_manager import (
            MetadataFormEntityManager,
            MetadataFormEntityTypes,
        )

        MetadataFormEntityManager.register(ShareObject, MetadataFormEntityTypes.Share.value)


class SharesBaseAsyncHandlerModuleInterface(ModuleInterface):
    @staticmethod
    def is_supported(modes: Set[ImportMode]) -> bool:
        return ImportMode.HANDLERS in modes

    @staticmethod
    def depends_on() -> List[Type['ModuleInterface']]:
        from dataall.modules.datasets_base import DatasetBaseModuleInterface

        return [DatasetBaseModuleInterface]

    def __init__(self):
        import dataall.modules.shares_base.handlers


class SharesBaseECSTaskModuleInterface(ModuleInterface):
    @staticmethod
    def is_supported(modes: Set[ImportMode]) -> bool:
        return ImportMode.SHARES_TASK in modes

    @staticmethod
    def depends_on() -> List[Type['ModuleInterface']]:
        from dataall.modules.datasets_base import DatasetBaseModuleInterface

        return [DatasetBaseModuleInterface]

    def __init__(self):
        from dataall.modules.shares_base.services.sharing_service import SharingService

        log.info('Sharing ECS task has been imported')

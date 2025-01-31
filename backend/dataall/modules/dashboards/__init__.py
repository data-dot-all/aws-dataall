"""Contains the code related to dashboards"""

import logging
from typing import Set, List, Type

from dataall.base.loader import ImportMode, ModuleInterface

log = logging.getLogger(__name__)


class DashboardApiModuleInterface(ModuleInterface):
    """Implements ModuleInterface for dashboard GraphQl lambda"""

    @staticmethod
    def is_supported(modes: Set[ImportMode]) -> bool:
        return ImportMode.API in modes

    @staticmethod
    def depends_on() -> List[Type['ModuleInterface']]:
        from dataall.modules.feed import FeedApiModuleInterface
        from dataall.modules.vote import VoteApiModuleInterface
        from dataall.modules.catalog import CatalogApiModuleInterface

        return [FeedApiModuleInterface, CatalogApiModuleInterface, VoteApiModuleInterface]

    def __init__(self):
        from dataall.core.environment.services.environment_resource_manager import EnvironmentResourceManager
        from dataall.core.metadata_manager import MetadataFormEntityManager, MetadataFormEntityTypes
        from dataall.modules.dashboards.db.dashboard_repositories import DashboardRepository
        from dataall.modules.dashboards.db.dashboard_models import Dashboard
        import dataall.modules.dashboards.api
        from dataall.modules.feed.api.registry import FeedRegistry, FeedDefinition
        from dataall.modules.catalog.indexers.registry import GlossaryRegistry, GlossaryDefinition
        from dataall.modules.vote.services.vote_service import add_vote_type
        from dataall.modules.dashboards.indexers.dashboard_indexer import DashboardIndexer
        from dataall.modules.dashboards.services.dashboard_permissions import GET_DASHBOARD

        FeedRegistry.register(FeedDefinition('Dashboard', Dashboard, GET_DASHBOARD))

        GlossaryRegistry.register(
            GlossaryDefinition(
                target_type='Dashboard', object_type='Dashboard', model=Dashboard, reindexer=DashboardIndexer
            )
        )

        add_vote_type('dashboard', DashboardIndexer, GET_DASHBOARD)

        EnvironmentResourceManager.register(DashboardRepository())
        MetadataFormEntityManager.register(Dashboard, MetadataFormEntityTypes.Dashboards.value)
        log.info('Dashboard API has been loaded')


class DashboardCdkModuleInterface(ModuleInterface):
    @staticmethod
    def is_supported(modes: Set[ImportMode]) -> bool:
        return ImportMode.CDK in modes

    def __init__(self):
        import dataall.modules.dashboards.cdk

        log.info('Dashboard CDK code has been loaded')


class DashboardCatalogIndexerModuleInterface(ModuleInterface):
    @staticmethod
    def is_supported(modes: Set[ImportMode]) -> bool:
        return ImportMode.CATALOG_INDEXER_TASK in modes

    @staticmethod
    def depends_on() -> List[Type['ModuleInterface']]:
        from dataall.modules.catalog import CatalogIndexerModuleInterface

        return [CatalogIndexerModuleInterface]

    def __init__(self):
        from dataall.modules.dashboards.indexers.dashboard_catalog_indexer import DashboardCatalogIndexer

        DashboardCatalogIndexer()
        log.info('Dashboard catalog indexer task has been loaded')


class DashboardAsyncHandlersModuleInterface(ModuleInterface):
    """Implements ModuleInterface for dashboard async lambda"""

    @staticmethod
    def is_supported(modes: Set[ImportMode]):
        return ImportMode.HANDLERS in modes

    @staticmethod
    def depends_on() -> List[Type['ModuleInterface']]:
        from dataall.modules.catalog import CatalogAsyncHandlersModuleInterface

        return [CatalogAsyncHandlersModuleInterface]

    def __init__(self):
        pass
        log.info('S3 Dataset handlers have been imported')

"""Contains the code related to datasets"""

import logging
from typing import List, Type, Set

from dataall.base.loader import ModuleInterface, ImportMode

log = logging.getLogger(__name__)


class RedshiftDatasetApiModuleInterface(ModuleInterface):
    """Implements ModuleInterface for dataset GraphQl lambda"""

    @staticmethod
    def is_supported(modes):
        return ImportMode.API in modes

    @staticmethod
    def depends_on() -> List[Type['ModuleInterface']]:
        from dataall.modules.datasets_base import DatasetBaseApiModuleInterface
        from dataall.modules.catalog import CatalogApiModuleInterface
        from dataall.modules.feed import FeedApiModuleInterface
        from dataall.modules.vote import VoteApiModuleInterface

        return [
            DatasetBaseApiModuleInterface,
            CatalogApiModuleInterface,
            FeedApiModuleInterface,
            VoteApiModuleInterface,
        ]

    def __init__(self):
        from dataall.modules.vote.services.vote_service import add_vote_type
        from dataall.modules.feed.api.registry import FeedRegistry, FeedDefinition
        from dataall.modules.catalog.indexers.registry import GlossaryRegistry, GlossaryDefinition
        from dataall.core.environment.services.environment_resource_manager import EnvironmentResourceManager

        from dataall.modules.redshift_datasets.indexers.dataset_indexer import DatasetIndexer
        from dataall.modules.redshift_datasets.indexers.table_indexer import DatasetTableIndexer
        from dataall.modules.redshift_datasets.db.redshift_dataset_repositories import (
            RedshiftDatasetEnvironmentResource,
        )
        from dataall.modules.redshift_datasets.db.redshift_connection_repositories import (
            RedshiftConnectionEnvironmentResource,
        )
        from dataall.modules.redshift_datasets.db.redshift_models import RedshiftDataset, RedshiftTable
        import dataall.modules.redshift_datasets.api

        FeedRegistry.register(FeedDefinition('RedshiftDatasetTable', RedshiftTable))
        FeedRegistry.register(FeedDefinition('RedshiftDataset', RedshiftDataset))

        GlossaryRegistry.register(
            GlossaryDefinition(
                target_type='RedshiftDataset',
                object_type='RedshiftDataset',
                model=RedshiftDataset,
                reindexer=DatasetIndexer,
            )
        )

        GlossaryRegistry.register(
            GlossaryDefinition(
                target_type='RedshiftDatasetTable',
                object_type='RedshiftDatasetTable',
                model=RedshiftTable,
                reindexer=DatasetTableIndexer,
            )
        )

        add_vote_type('redshiftdataset', DatasetIndexer)

        EnvironmentResourceManager.register(RedshiftDatasetEnvironmentResource())
        EnvironmentResourceManager.register(RedshiftConnectionEnvironmentResource())

        log.info('API of Redshift datasets has been imported')


class RedshiftDatasetCdkModuleInterface(ModuleInterface):
    """Loads dataset cdk stacks"""

    @staticmethod
    def is_supported(modes: Set[ImportMode]):
        return ImportMode.CDK in modes

    def __init__(self):
        import dataall.modules.redshift_datasets.cdk

        log.info('Redshift Dataset CDK has been imported')

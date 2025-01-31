"""Contains the code related to datasets"""

import logging
from typing import List, Type, Set

from dataall.base.loader import ModuleInterface, ImportMode
from dataall.modules.s3_datasets.db.dataset_models import DatasetBucket

log = logging.getLogger(__name__)


class DatasetApiModuleInterface(ModuleInterface):
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
        # these imports are placed inside the method because they are only related to GraphQL api.
        from dataall.core.stacks.db.target_type_repositories import TargetType
        from dataall.core.metadata_manager.metadata_form_entity_manager import (
            MetadataFormEntityTypes,
            MetadataFormEntityManager,
        )
        from dataall.modules.vote.services.vote_service import add_vote_type
        from dataall.modules.feed.api.registry import FeedRegistry, FeedDefinition
        from dataall.modules.catalog.indexers.registry import GlossaryRegistry, GlossaryDefinition
        from dataall.core.environment.services.environment_resource_manager import EnvironmentResourceManager
        from dataall.modules.s3_datasets.indexers.dataset_indexer import DatasetIndexer
        from dataall.modules.s3_datasets.indexers.location_indexer import DatasetLocationIndexer
        from dataall.modules.s3_datasets.indexers.table_indexer import DatasetTableIndexer

        import dataall.modules.s3_datasets.api
        from dataall.modules.s3_datasets.services.dataset_permissions import (
            GET_DATASET,
            UPDATE_DATASET,
            GET_DATASET_TABLE,
            GET_DATASET_FOLDER,
            MANAGE_DATASETS,
        )
        from dataall.modules.s3_datasets.db.dataset_repositories import DatasetRepository
        from dataall.modules.s3_datasets.db.dataset_models import DatasetStorageLocation, DatasetTable, S3Dataset

        FeedRegistry.register(FeedDefinition('DatasetStorageLocation', DatasetStorageLocation, GET_DATASET_FOLDER))
        FeedRegistry.register(FeedDefinition('DatasetTable', DatasetTable, GET_DATASET_TABLE))
        FeedRegistry.register(FeedDefinition('Dataset', S3Dataset, GET_DATASET))

        GlossaryRegistry.register(
            GlossaryDefinition(
                target_type='Folder',
                object_type='DatasetStorageLocation',
                model=DatasetStorageLocation,
                reindexer=DatasetLocationIndexer,
            )
        )

        GlossaryRegistry.register(
            GlossaryDefinition(target_type='Dataset', object_type='Dataset', model=S3Dataset, reindexer=DatasetIndexer)
        )

        GlossaryRegistry.register(
            GlossaryDefinition(
                target_type='DatasetTable',
                object_type='DatasetTable',
                model=DatasetTable,
                reindexer=DatasetTableIndexer,
            )
        )

        add_vote_type('dataset', DatasetIndexer, GET_DATASET)

        TargetType('dataset', GET_DATASET, UPDATE_DATASET, MANAGE_DATASETS)

        EnvironmentResourceManager.register(DatasetRepository())
        MetadataFormEntityManager.register(S3Dataset, MetadataFormEntityTypes.S3Datasets.value)
        MetadataFormEntityManager.register(DatasetTable, MetadataFormEntityTypes.Tables.value)
        MetadataFormEntityManager.register(DatasetStorageLocation, MetadataFormEntityTypes.Folder.value)
        MetadataFormEntityManager.register(DatasetBucket, MetadataFormEntityTypes.Bucket.value)

        log.info('API of S3 datasets has been imported')


class DatasetAsyncHandlersModuleInterface(ModuleInterface):
    """Implements ModuleInterface for dataset async lambda"""

    @staticmethod
    def is_supported(modes: Set[ImportMode]):
        return ImportMode.HANDLERS in modes

    @staticmethod
    def depends_on() -> List[Type['ModuleInterface']]:
        from dataall.modules.datasets_base import DatasetBaseModuleInterface
        from dataall.modules.catalog import CatalogAsyncHandlersModuleInterface

        return [DatasetBaseModuleInterface, CatalogAsyncHandlersModuleInterface]

    def __init__(self):
        import dataall.modules.s3_datasets.handlers
        import dataall.modules.s3_datasets.db.dataset_models
        import dataall.modules.s3_datasets.db.dataset_repositories
        import dataall.modules.s3_datasets.services.dataset_permissions

        log.info('S3 Dataset handlers have been imported')


class DatasetCdkModuleInterface(ModuleInterface):
    """Loads dataset cdk stacks"""

    @staticmethod
    def is_supported(modes: Set[ImportMode]):
        return ImportMode.CDK in modes

    @staticmethod
    def depends_on() -> List[Type['ModuleInterface']]:
        from dataall.modules.datasets_base import DatasetBaseModuleInterface

        return [DatasetBaseModuleInterface]

    def __init__(self):
        import dataall.modules.s3_datasets.cdk
        from dataall.core.environment.cdk.environment_stack import EnvironmentSetup
        from dataall.modules.s3_datasets.cdk.dataset_glue_profiler_extension import DatasetGlueProfilerExtension
        from dataall.modules.s3_datasets.cdk.dataset_custom_resources_extension import DatasetCustomResourcesExtension

        EnvironmentSetup.register(DatasetGlueProfilerExtension)
        EnvironmentSetup.register(DatasetCustomResourcesExtension)

        log.info('S3 Dataset stacks have been imported')


class DatasetStackUpdaterModuleInterface(ModuleInterface):
    @staticmethod
    def is_supported(modes: Set[ImportMode]) -> bool:
        return ImportMode.STACK_UPDATER_TASK in modes

    @staticmethod
    def depends_on() -> List[Type['ModuleInterface']]:
        from dataall.modules.datasets_base import DatasetBaseModuleInterface

        return [DatasetBaseModuleInterface]

    def __init__(self):
        from dataall.modules.s3_datasets.tasks.dataset_stack_finder import DatasetStackFinder

        DatasetStackFinder()
        log.info('S3 Dataset stack updater task has been loaded')


class DatasetCatalogIndexerModuleInterface(ModuleInterface):
    @staticmethod
    def is_supported(modes: Set[ImportMode]) -> bool:
        return ImportMode.CATALOG_INDEXER_TASK in modes

    @staticmethod
    def depends_on() -> List[Type['ModuleInterface']]:
        from dataall.modules.catalog import CatalogIndexerModuleInterface
        from dataall.modules.datasets_base import DatasetBaseModuleInterface

        return [CatalogIndexerModuleInterface, DatasetBaseModuleInterface]

    def __init__(self):
        from dataall.modules.s3_datasets.indexers.dataset_catalog_indexer import DatasetCatalogIndexer

        DatasetCatalogIndexer()
        log.info('S3 Dataset catalog indexer task has been loaded')

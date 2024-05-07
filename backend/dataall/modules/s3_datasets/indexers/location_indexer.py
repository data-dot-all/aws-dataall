"""Indexes DatasetStorageLocation in OpenSearch"""

import re

from dataall.core.environment.services.environment_service import EnvironmentService
from dataall.core.organizations.db.organization_repositories import OrganizationRepository
from dataall.modules.s3_datasets.db.dataset_location_repositories import DatasetLocationRepository
from dataall.modules.s3_datasets.db.dataset_repositories import S3DatasetRepository
from dataall.modules.s3_datasets.db.dataset_models import S3Dataset
from dataall.modules.s3_datasets.indexers.dataset_indexer import DatasetIndexer
from dataall.modules.catalog.indexers.base_indexer import BaseIndexer


class DatasetLocationIndexer(BaseIndexer):
    @classmethod
    def upsert(cls, session, folder_uri: str):
        folder = DatasetLocationRepository.get_location_by_uri(session, folder_uri)

        if folder:
            dataset: S3Dataset = S3DatasetRepository.get_dataset_by_uri(session, folder.datasetUri)
            env = EnvironmentService.get_environment_by_uri(session, dataset.environmentUri)
            org = OrganizationRepository.get_organization_by_uri(session, dataset.organizationUri)
            glossary = BaseIndexer._get_target_glossary_terms(session, folder_uri)

            BaseIndexer._index(
                doc_id=folder_uri,
                doc={
                    'name': folder.name,
                    'admins': dataset.SamlAdminGroupName,
                    'owner': folder.owner,
                    'label': folder.label,
                    'resourceKind': 'folder',
                    'description': folder.description,
                    'source': dataset.S3BucketName,
                    'classification': re.sub('[^A-Za-z0-9]+', '', dataset.confidentiality),
                    'tags': [f.replace('-', '') for f in folder.tags or []],
                    'topics': dataset.topics,
                    'region': folder.region.replace('-', ''),
                    'datasetUri': folder.datasetUri,
                    'environmentUri': env.environmentUri,
                    'environmentName': env.name,
                    'organizationUri': org.organizationUri,
                    'organizationName': org.name,
                    'created': folder.created,
                    'updated': folder.updated,
                    'deleted': folder.deleted,
                    'glossary': glossary,
                },
            )
            DatasetIndexer.upsert(session=session, dataset_uri=folder.datasetUri)
        return folder

    @classmethod
    def upsert_all(cls, session, dataset_uri: str):
        folders = DatasetLocationRepository.get_dataset_folders(session, dataset_uri)
        for folder in folders:
            DatasetLocationIndexer.upsert(session=session, folder_uri=folder.locationUri)
        return folders

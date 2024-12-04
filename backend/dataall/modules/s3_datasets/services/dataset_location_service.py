import logging

from dataall.modules.s3_datasets.indexers.dataset_indexer import DatasetIndexer
from dataall.base.context import get_context
from dataall.core.permissions.services.resource_policy_service import ResourcePolicyService
from dataall.core.permissions.services.tenant_policy_service import TenantPolicyService

##TODO
##from dataall.core.resource_threshold.services.resource_threshold_service import ResourceThresholdService
from dataall.modules.catalog.db.glossary_repositories import GlossaryRepository
from dataall.base.db.exceptions import ResourceShared, ResourceAlreadyExists
from dataall.modules.s3_datasets.services.dataset_service import DatasetService
from dataall.modules.s3_datasets.aws.s3_location_client import S3LocationClient
from dataall.modules.s3_datasets.db.dataset_location_repositories import DatasetLocationRepository
from dataall.modules.s3_datasets.indexers.location_indexer import DatasetLocationIndexer
from dataall.modules.s3_datasets.services.dataset_permissions import (
    UPDATE_DATASET_FOLDER,
    MANAGE_DATASETS,
    CREATE_DATASET_FOLDER,
    LIST_DATASET_FOLDERS,
    DELETE_DATASET_FOLDER,
)
from dataall.modules.s3_datasets.services.dataset_permissions import DATASET_FOLDER_READ, GET_DATASET_FOLDER
from dataall.modules.s3_datasets.db.dataset_repositories import DatasetRepository
from dataall.modules.s3_datasets.db.dataset_models import DatasetStorageLocation, S3Dataset
from dataall.modules.s3_datasets.aws.bedrock_metadata_client import BedrockClient
from dataall.modules.s3_datasets.aws.s3_dataset_client import S3DatasetClient

log = logging.getLogger(__name__)


class DatasetLocationService:
    @staticmethod
    def _get_dataset_uri(session, uri):
        location = DatasetLocationRepository.get_location_by_uri(session, uri)
        return location.datasetUri

    @staticmethod
    @TenantPolicyService.has_tenant_permission(MANAGE_DATASETS)
    @ResourcePolicyService.has_resource_permission(CREATE_DATASET_FOLDER)
    def create_storage_location(uri: str, data: dict):
        with get_context().db_engine.scoped_session() as session:
            exists = DatasetLocationRepository.exists(session, uri, data['prefix'])

            if exists:
                raise ResourceAlreadyExists(
                    action='Create Folder',
                    message=f'Folder: {data["prefix"]} already exist on dataset {uri}',
                )

            dataset = DatasetRepository.get_dataset_by_uri(session, uri)
            location = DatasetLocationRepository.create_dataset_location(session, dataset, data)
            DatasetLocationService._attach_dataset_folder_read_permission(session, dataset, location.locationUri)

            if 'terms' in data.keys():
                DatasetLocationService._create_glossary_links(session, location, data['terms'])

            S3LocationClient(location, dataset).create_bucket_prefix()

        DatasetLocationIndexer.upsert(session=session, folder_uri=location.locationUri)
        DatasetIndexer.upsert(session, dataset.datasetUri)
        return location

    @staticmethod
    @ResourcePolicyService.has_resource_permission(LIST_DATASET_FOLDERS)
    def list_dataset_locations(uri: str, filter: dict = None):
        with get_context().db_engine.scoped_session() as session:
            return DatasetLocationRepository.list_dataset_locations(session=session, uri=uri, data=filter)

    @staticmethod
    @ResourcePolicyService.has_resource_permission(GET_DATASET_FOLDER)
    def get_storage_location(uri):
        with get_context().db_engine.scoped_session() as session:
            return DatasetLocationRepository.get_location_by_uri(session, uri)

    @staticmethod
    @TenantPolicyService.has_tenant_permission(MANAGE_DATASETS)
    @ResourcePolicyService.has_resource_permission(UPDATE_DATASET_FOLDER, parent_resource=_get_dataset_uri)
    def update_storage_location(uri: str, data: dict):
        with get_context().db_engine.scoped_session() as session:
            location = DatasetLocationRepository.get_location_by_uri(session, uri)
            for k in data.keys():
                setattr(location, k, data.get(k))

            if 'terms' in data.keys():
                DatasetLocationService._create_glossary_links(session, location, data['terms'])

            DatasetLocationIndexer.upsert(session, folder_uri=location.locationUri)
            DatasetIndexer.upsert(session, location.datasetUri)

            return location

    @staticmethod
    @TenantPolicyService.has_tenant_permission(MANAGE_DATASETS)
    @ResourcePolicyService.has_resource_permission(DELETE_DATASET_FOLDER, parent_resource=_get_dataset_uri)
    def remove_storage_location(uri: str = None):
        with get_context().db_engine.scoped_session() as session:
            location = DatasetLocationRepository.get_location_by_uri(session, uri)
            DatasetService.check_before_delete(session, location.locationUri, action=DELETE_DATASET_FOLDER)
            DatasetService.execute_on_delete(session, location.locationUri, action=DELETE_DATASET_FOLDER)
            dataset = DatasetRepository.get_dataset_by_uri(session, location.datasetUri)
            DatasetLocationService._delete_dataset_folder_read_permission(session, dataset, location.locationUri)
            DatasetLocationRepository.delete(session, location)
            GlossaryRepository.delete_glossary_terms_links(
                session,
                target_uri=location.locationUri,
                target_type='DatasetStorageLocation',
            )
            DatasetLocationIndexer.delete_doc(doc_id=location.locationUri)
        return True

    @staticmethod
    def _create_glossary_links(session, location, terms):
        GlossaryRepository.set_glossary_terms_links(
            session, get_context().username, location.locationUri, 'Folder', terms
        )

    @staticmethod
    def _attach_dataset_folder_read_permission(session, dataset: S3Dataset, location_uri):
        """
        Attach Folder permissions to dataset groups
        """
        permission_group = {
            dataset.SamlAdminGroupName,
            dataset.stewards if dataset.stewards is not None else dataset.SamlAdminGroupName,
        }
        for group in permission_group:
            ResourcePolicyService.attach_resource_policy(
                session=session,
                group=group,
                permissions=DATASET_FOLDER_READ,
                resource_uri=location_uri,
                resource_type=DatasetStorageLocation.__name__,
            )

    @staticmethod
    def _delete_dataset_folder_read_permission(session, dataset: S3Dataset, location_uri):
        """
        Delete Folder permissions to dataset groups
        """
        permission_group = {
            dataset.SamlAdminGroupName,
            dataset.stewards if dataset.stewards is not None else dataset.SamlAdminGroupName,
        }
        for group in permission_group:
            ResourcePolicyService.delete_resource_policy(session=session, group=group, resource_uri=location_uri)

    @staticmethod
    @ResourcePolicyService.has_resource_permission(UPDATE_DATASET_FOLDER)
    # @ResourceThresholdService.check_invocation_count(
    #     'metadata', 'modules.s3_datasets.features.generate_metadata_ai.max_count_per_day'
    # )
    def generate_metadata_for_folder(uri, metadata_types):
        context = get_context()
        with context.db_engine.scoped_session() as session:
            folder = DatasetLocationRepository.get_location_by_uri(session, uri)
            dataset = DatasetRepository.get_dataset_by_uri(session, folder.datasetUri)
            files = S3DatasetClient(dataset).list_bucket_files(folder.S3BucketName, folder.S3Prefix)
            metadata = BedrockClient().invoke_model_folder_metadata(
                metadata_types=metadata_types, folder=folder, files=[f['Key'] for f in files]
            )
            return [{'targetUri': uri, 'targetType': 'Folder'} | metadata]

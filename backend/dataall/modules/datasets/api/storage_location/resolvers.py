from dataall.api.context import Context
from dataall.aws.handlers.service_handlers import Worker
from dataall.db import models
from dataall.db.api import (
    ResourcePolicy,
    Glossary,
    Environment,
)
from dataall.modules.datasets.aws.s3_location_client import S3LocationClient
from dataall.modules.datasets.indexers.location_indexer import DatasetLocationIndexer
from dataall.modules.datasets_base.db.models import DatasetStorageLocation, Dataset
from dataall.modules.datasets.db.dataset_location_repository import DatasetLocationRepository
from dataall.modules.datasets.services.dataset_service import DatasetService
from dataall.modules.datasets.services.dataset_permissions import UPDATE_DATASET_FOLDER


def create_storage_location(
    context, source, datasetUri: str = None, input: dict = None
):
    with context.engine.scoped_session() as session:
        location = DatasetLocationRepository.create_dataset_location(
            session=session,
            uri=datasetUri,
            data=input,
        )

        S3LocationClient(location).create_bucket_prefix()

        DatasetLocationIndexer.upsert(session=session, folder_uri=location.locationUri)
    return location


def list_dataset_locations(context, source, filter: dict = None):
    if not source:
        return None
    if not filter:
        filter = {}
    with context.engine.scoped_session() as session:
        return DatasetLocationRepository.list_dataset_locations(
            session=session, uri=source.datasetUri, data=filter
        )


def get_storage_location(context, source, locationUri=None):
    with context.engine.scoped_session() as session:
        location = DatasetLocationRepository.get_location_by_uri(session, locationUri)
        return DatasetLocationRepository.get_dataset_location(
            session=session,
            uri=location.datasetUri,
            data={'locationUri': location.locationUri},
        )


def update_storage_location(
    context, source, locationUri: str = None, input: dict = None
):
    with context.engine.scoped_session() as session:
        location = DatasetLocationRepository.get_location_by_uri(session, locationUri)
        input['location'] = location
        input['locationUri'] = location.locationUri
        DatasetLocationRepository.update_dataset_location(
            session=session,
            uri=location.datasetUri,
            data=input,
        )
        DatasetLocationIndexer.upsert(session, folder_uri=location.locationUri)

        return location


def remove_storage_location(context, source, locationUri: str = None):
    with context.engine.scoped_session() as session:
        location = DatasetLocationRepository.get_location_by_uri(session, locationUri)
        DatasetLocationRepository.delete_dataset_location(
            session=session,
            uri=location.datasetUri,
            data={'locationUri': location.locationUri},
        )
        DatasetLocationIndexer.delete_doc(doc_id=location.locationUri)
    return True


def resolve_dataset(context, source: DatasetStorageLocation, **kwargs):
    if not source:
        return None
    with context.engine.scoped_session() as session:
        d = session.query(Dataset).get(source.datasetUri)
    return d


def publish_location_update(context: Context, source, locationUri: str = None):
    with context.engine.scoped_session() as session:
        location = DatasetLocationRepository.get_location_by_uri(session, locationUri)
        ResourcePolicy.check_user_resource_permission(
            session=session,
            username=context.username,
            groups=context.groups,
            resource_uri=location.datasetUri,
            permission_name=UPDATE_DATASET_FOLDER,
        )
        dataset = DatasetService.get_dataset_by_uri(session, location.datasetUri)
        env = Environment.get_environment_by_uri(session, dataset.environmentUri)
        if not env.subscriptionsEnabled or not env.subscriptionsProducersTopicName:
            raise Exception(
                'Subscriptions are disabled. '
                "First enable subscriptions for this dataset's environment then retry."
            )
        task = models.Task(
            targetUri=location.datasetUri,
            action='sns.dataset.publish_update',
            payload={'s3Prefix': location.S3Prefix},
        )
        session.add(task)

    Worker.process(engine=context.engine, task_ids=[task.taskUri], save_response=False)
    return True


def resolve_glossary_terms(
    context: Context, source: DatasetStorageLocation, **kwargs
):
    if not source:
        return None
    with context.engine.scoped_session() as session:
        return Glossary.get_glossary_terms_links(
            session, source.locationUri, 'DatasetStorageLocation'
        )

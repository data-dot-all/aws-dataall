import logging

from dataall.api.Objects.Stack import stack_helper
from dataall import db
from dataall.api.context import Context
from dataall.db import paginate, exceptions, models
from dataall.db.api import Environment
from dataall.db.api.organization import Organization
from dataall.modules.dataset_sharing.db.models import ShareObject
from dataall.modules.datasets import Dataset
from dataall.modules.datasets.api.dataset.enums import DatasetRole
from dataall.modules.datasets.services.dataset_service import DatasetService

log = logging.getLogger(__name__)


def create_dataset(context: Context, source, input=None):
    return DatasetService.create_dataset(env_uri=input['environmentUri'], data=input)


def import_dataset(context: Context, source, input=None):
    if not input:
        raise exceptions.RequiredParameter(input)
    if not input.get('environmentUri'):
        raise exceptions.RequiredParameter('environmentUri')
    if not input.get('bucketName'):
        raise exceptions.RequiredParameter('bucketName')
    if not input.get('SamlAdminGroupName'):
        raise exceptions.RequiredParameter('group')

    return DatasetService.import_dataset(data=input)


def get_dataset(context, source, datasetUri=None):
    return DatasetService.get_dataset(uri=datasetUri)


def resolve_user_role(context: Context, source: Dataset, **kwargs):
    if not source:
        return None
    if source.owner == context.username:
        return DatasetRole.Creator.value
    elif source.SamlAdminGroupName in context.groups:
        return DatasetRole.Admin.value
    elif source.stewards in context.groups:
        return DatasetRole.DataSteward.value
    else:
        with context.engine.scoped_session() as session:
            share = (
                session.query(ShareObject)
                .filter(ShareObject.datasetUri == source.datasetUri)
                .first()
            )
            if share and (
                share.owner == context.username or share.principalId in context.groups
            ):
                return DatasetRole.Shared.value
    return DatasetRole.NoPermission.value


def get_file_upload_presigned_url(
    context, source, datasetUri: str = None, input: dict = None
):
    return DatasetService.get_file_upload_presigned_url(uri=datasetUri, data=input)


def list_datasets(context: Context, source, filter: dict = None):
    if not filter:
        filter = {'page': 1, 'pageSize': 5}
    return DatasetService.list_datasets(filter)


def list_locations(context, source: Dataset, filter: dict = None):
    if not source:
        return None
    if not filter:
        filter = {'page': 1, 'pageSize': 5}
    return DatasetService.list_locations(source.datasetUri, filter)


def list_tables(context, source: Dataset, filter: dict = None):
    if not source:
        return None
    if not filter:
        filter = {'page': 1, 'pageSize': 5}
    return DatasetService.list_tables(source.datasetUri, filter)


def get_dataset_organization(context, source: Dataset, **kwargs):
    if not source:
        return None
    with context.engine.scoped_session() as session:
        return Organization.get_organization_by_uri(session, source.organizationUri)


def get_dataset_environment(context, source: Dataset, **kwargs):
    if not source:
        return None
    with context.engine.scoped_session() as session:
        return Environment.get_environment_by_uri(session, source.environmentUri)


def get_dataset_owners_group(context, source: Dataset, **kwargs):
    if not source:
        return None
    return source.SamlAdminGroupName


def get_dataset_stewards_group(context, source: Dataset, **kwargs):
    if not source:
        return None
    return source.stewards


def update_dataset(context, source, datasetUri: str = None, input: dict = None):
    return DatasetService.update_dataset(uri=datasetUri)


def get_dataset_statistics(context: Context, source: Dataset, **kwargs):
    if not source:
        return None
    return DatasetService.get_dataset_statistics(source)


def get_dataset_etl_credentials(context: Context, source, datasetUri: str = None):
    return DatasetService.get_dataset_etl_credentials(uri=datasetUri)


def get_dataset_assume_role_url(context: Context, source, datasetUri: str = None):
    return DatasetService.get_dataset_assume_role_url(uri=datasetUri)


def sync_tables(context: Context, source, datasetUri: str = None):
    return DatasetService.sync_tables(uri=datasetUri)


def start_crawler(context: Context, source, datasetUri: str, input: dict = None):
    return DatasetService.start_crawler(uri=datasetUri, data=input)


def list_dataset_share_objects(context, source, filter: dict = None):
    if not source:
        return None
    if not filter:
        filter = {'page': 1, 'pageSize': 5}
    return DatasetService.list_dataset_share_objects(source, filter)


def generate_dataset_access_token(context, source, datasetUri: str = None):
    return DatasetService.generate_dataset_access_token(uri=datasetUri)


def get_dataset_summary(context, source, datasetUri: str = None):
    return DatasetService.get_dataset_summary(uri=datasetUri)


def save_dataset_summary(
    context: Context, source, datasetUri: str = None, content: str = None
):
    return DatasetService.save_dataset_summary(uri=datasetUri, content=content)


def get_dataset_stack(context: Context, source: Dataset, **kwargs):
    if not source:
        return None
    return stack_helper.get_stack_with_cfn_resources(
        targetUri=source.datasetUri,
        environmentUri=source.environmentUri,
    )


def get_crawler(context, source, datasetUri: str = None, name: str = None):
    return DatasetService.get_crawler(uri=datasetUri, name=name)


def delete_dataset(
    context: Context, source, datasetUri: str = None, deleteFromAWS: bool = False
):
    return DatasetService.delete_dataset(uri=datasetUri, delete_from_aws=deleteFromAWS)


def get_dataset_glossary_terms(context: Context, source: Dataset, **kwargs):
    if not source:
        return None
    with context.engine.scoped_session() as session:
        terms = (
            session.query(models.GlossaryNode)
            .join(
                models.TermLink, models.TermLink.nodeUri == models.GlossaryNode.nodeUri
            )
            .filter(models.TermLink.targetUri == source.datasetUri)
        )

    return paginate(terms, page_size=100, page=1).to_dict()


def publish_dataset_update(
    context: Context, source, datasetUri: str = None, s3Prefix: str = None
):
    return DatasetService.publish_dataset_update(uri=datasetUri, s3_prefix=s3Prefix)


def resolve_redshift_copy_enabled(context, source: Dataset, clusterUri: str):
    if not source:
        return None
    with context.engine.scoped_session() as session:
        return db.api.RedshiftCluster.get_cluster_dataset(
            session, clusterUri, source.datasetUri
        ).datasetCopyEnabled


def list_datasets_created_in_environment(
    context: Context, source, environmentUri: str = None, filter: dict = None
):
    if not filter:
        filter = {}
    return DatasetService.list_datasets_created_in_environment(environmentUri, filter)


def list_datasets_owned_by_env_group(
    context, source, environmentUri: str = None, groupUri: str = None, filter: dict = None
):
    if not filter:
        filter = {}
    return DatasetService.list_datasets_owned_by_env_group(environmentUri, groupUri, filter)

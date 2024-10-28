import logging

from dataall.base.api.context import Context
from dataall.base.feature_toggle_checker import is_feature_enabled
from dataall.base.utils.expiration_util import Expiration
from dataall.core.stacks.services.stack_service import StackService
from dataall.modules.catalog.db.glossary_repositories import GlossaryRepository
from dataall.core.environment.services.environment_service import EnvironmentService
from dataall.core.organizations.db.organization_repositories import OrganizationRepository
from dataall.base.db.exceptions import RequiredParameter, InvalidInput
from dataall.modules.s3_datasets.db.dataset_models import S3Dataset
from dataall.modules.datasets_base.services.datasets_enums import DatasetRole, ConfidentialityClassification
from dataall.modules.s3_datasets.services.dataset_service import DatasetService

log = logging.getLogger(__name__)


def create_dataset(context: Context, source, input=None):
    RequestValidator.validate_creation_request(input)

    admin_group = input['SamlAdminGroupName']
    uri = input['environmentUri']
    return DatasetService.create_dataset(uri=uri, admin_group=admin_group, data=input)


def import_dataset(context: Context, source, input=None):
    RequestValidator.validate_import_request(input)

    admin_group = input['SamlAdminGroupName']
    uri = input['environmentUri']
    return DatasetService.import_dataset(uri=uri, admin_group=admin_group, data=input)


def get_dataset(context, source, datasetUri=None):
    return DatasetService.get_dataset(uri=datasetUri)


def resolve_user_role(context: Context, source: S3Dataset, **kwargs):
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
            other_modules_user_role = DatasetService.get_other_modules_dataset_user_role(
                session, source.datasetUri, context.username, context.groups
            )
            if other_modules_user_role is not None:
                return other_modules_user_role
    return DatasetRole.NoPermission.value


@is_feature_enabled('modules.s3_datasets.features.file_uploads')
def get_file_upload_presigned_url(context, source, datasetUri: str = None, input: dict = None):
    return DatasetService.get_file_upload_presigned_url(uri=datasetUri, data=input)


def list_locations(context, source: S3Dataset, filter: dict = None):
    if not source:
        return None
    if not filter:
        filter = {'page': 1, 'pageSize': 5}
    return DatasetService.list_locations(source.datasetUri, filter)


def list_tables(context, source: S3Dataset, filter: dict = None):
    if not source:
        return None
    if not filter:
        filter = {'page': 1, 'pageSize': 5}
    return DatasetService.list_tables(source.datasetUri, filter)


def get_dataset_organization(context, source: S3Dataset, **kwargs):
    if not source:
        return None
    with context.engine.scoped_session() as session:
        return OrganizationRepository.get_organization_by_uri(session, source.organizationUri)


def get_dataset_environment(context, source: S3Dataset, **kwargs):
    if not source:
        return None
    with context.engine.scoped_session() as session:
        return EnvironmentService.get_environment_by_uri(session, source.environmentUri)


def get_dataset_owners_group(context, source: S3Dataset, **kwargs):
    if not source:
        return None
    return source.SamlAdminGroupName


def get_dataset_stewards_group(context, source: S3Dataset, **kwargs):
    if not source:
        return None
    return source.stewards


def update_dataset(context, source, datasetUri: str = None, input: dict = None):
    if input.get('enableExpiration', False):
        RequestValidator.validate_share_expiration_request(input)
    return DatasetService.update_dataset(uri=datasetUri, data=input)


def get_dataset_statistics(context: Context, source: S3Dataset, **kwargs):
    if not source:
        return None
    return DatasetService.get_dataset_statistics(source)


@is_feature_enabled('modules.s3_datasets.features.aws_actions')
def get_dataset_assume_role_url(context: Context, source, datasetUri: str = None):
    return DatasetService.get_dataset_assume_role_url(uri=datasetUri)


@is_feature_enabled('modules.s3_datasets.features.glue_crawler')
def start_crawler(context: Context, source, datasetUri: str, input: dict = None):
    return DatasetService.start_crawler(uri=datasetUri, data=input)


@is_feature_enabled('modules.s3_datasets.features.aws_actions')
def generate_dataset_access_token(context, source, datasetUri: str = None):
    return DatasetService.generate_dataset_access_token(uri=datasetUri)


def resolve_dataset_stack(context: Context, source: S3Dataset, **kwargs):
    if not source:
        return None
    return StackService.resolve_parent_obj_stack(
        targetUri=source.datasetUri,
        environmentUri=source.environmentUri,
    )


def delete_dataset(context: Context, source, datasetUri: str = None, deleteFromAWS: bool = False):
    return DatasetService.delete_dataset(uri=datasetUri, delete_from_aws=deleteFromAWS)


def get_dataset_glossary_terms(context: Context, source: S3Dataset, **kwargs):
    if not source:
        return None
    with context.engine.scoped_session() as session:
        return GlossaryRepository.get_glossary_terms_links(session, source.datasetUri, 'Dataset')


def list_datasets_owned_by_env_group(
    context, source, environmentUri: str = None, groupUri: str = None, filter: dict = None
):
    if not filter:
        filter = {}
    return DatasetService.list_datasets_owned_by_env_group(environmentUri, groupUri, filter)


def list_s3_object_keys(context, source, datasetUri: str = None):
    return DatasetService.list_s3_object_keys(uri=datasetUri)


class RequestValidator:
    @staticmethod
    def validate_creation_request(data):
        if not data:
            raise RequiredParameter(data)
        if not data.get('environmentUri'):
            raise RequiredParameter('environmentUri')
        if not data.get('SamlAdminGroupName'):
            raise RequiredParameter('group')
        if not data.get('label'):
            raise RequiredParameter('label')
        ConfidentialityClassification.validate_confidentiality_level(data.get('confidentiality', ''))
        if len(data['label']) > 52:
            raise InvalidInput('Dataset name', data['label'], 'less than 52 characters')
        if data.get('enableExpiration', False):
            RequestValidator.validate_share_expiration_request(data)

    @staticmethod
    def validate_share_expiration_request(data):
        if not isinstance(data.get('expiryMinDuration'), int) or not isinstance(data.get('expiryMaxDuration'), int):
            raise InvalidInput(
                'Expiration durations (Minimum and Maximum)',
                '',
                'must be valid integers',
            )
        if data.get('expiryMinDuration') < 0 or data.get('expiryMaxDuration') < 0:
            raise InvalidInput(
                'expiration duration ',
                '',
                'must be greater than zero',
            )
        if data.get('expiryMinDuration') > data.get('expiryMaxDuration'):
            raise InvalidInput(
                'Minimum expiration duration ',
                data.get('expiryMinDuration'),
                f'cannot be greater than max expiration {data.get("expiryMaxDuration")}',
            )
        if data.get('expirySetting') not in [item.value for item in list(Expiration)]:
            raise InvalidInput(
                'Expiration Setting',
                data.get('expirySetting'),
                'is of invalid type',
            )

    @staticmethod
    def validate_import_request(data):
        RequestValidator.validate_creation_request(data)
        if not data.get('bucketName'):
            raise RequiredParameter('bucketName')

import os
import json
import logging
from typing import List
from dataall.base.aws.quicksight import QuicksightClient
from dataall.base.db import exceptions
from dataall.base.utils.naming_convention import NamingConventionPattern, NamingConventionService
from dataall.base.utils.expiration_util import ExpirationUtils
from dataall.core.permissions.services.resource_policy_service import ResourcePolicyService
from dataall.core.permissions.services.tenant_policy_service import TenantPolicyService
from dataall.core.stacks.services.stack_service import StackService
from dataall.core.tasks.service_handlers import Worker
from dataall.base.aws.sts import SessionHelper
from dataall.modules.s3_datasets.aws.kms_dataset_client import KmsClient
from dataall.base.context import get_context
from dataall.core.permissions.services.group_policy_service import GroupPolicyService
from dataall.core.environment.services.environment_service import EnvironmentService
from dataall.core.stacks.db.keyvaluetag_repositories import KeyValueTagRepository
from dataall.core.stacks.db.stack_repositories import StackRepository
from dataall.core.stacks.db.stack_models import Stack
from dataall.core.tasks.db.task_models import Task
from dataall.modules.catalog.db.glossary_repositories import GlossaryRepository
from dataall.modules.s3_datasets.db.dataset_bucket_repositories import DatasetBucketRepository
from dataall.modules.shares_base.db.share_object_repositories import ShareObjectRepository
from dataall.modules.vote.db.vote_repositories import VoteRepository
from dataall.modules.s3_datasets.aws.glue_dataset_client import DatasetCrawler
from dataall.modules.s3_datasets.aws.s3_dataset_client import S3DatasetClient
from dataall.modules.s3_datasets.db.dataset_location_repositories import DatasetLocationRepository
from dataall.modules.s3_datasets.db.dataset_table_repositories import DatasetTableRepository
from dataall.modules.s3_datasets.indexers.dataset_indexer import DatasetIndexer
from dataall.modules.s3_datasets.services.dataset_permissions import (
    CREDENTIALS_DATASET,
    CRAWL_DATASET,
    DELETE_DATASET,
    MANAGE_DATASETS,
    UPDATE_DATASET,
    CREATE_DATASET,
    DATASET_ALL,
    DATASET_READ,
    IMPORT_DATASET,
    GET_DATASET,
)
from dataall.modules.s3_datasets.db.dataset_repositories import DatasetRepository
from dataall.modules.datasets_base.db.dataset_repositories import DatasetBaseRepository
from dataall.modules.datasets_base.services.datasets_enums import DatasetRole
from dataall.modules.s3_datasets.db.dataset_models import S3Dataset, DatasetTable
from dataall.modules.datasets_base.db.dataset_models import DatasetBase
from dataall.modules.s3_datasets.services.dataset_permissions import DATASET_TABLE_ALL
from dataall.modules.datasets_base.services.dataset_service_interface import DatasetServiceInterface

log = logging.getLogger(__name__)


class DatasetService:
    _interfaces: List[DatasetServiceInterface] = []

    @classmethod
    def register(cls, interface: DatasetServiceInterface):
        cls._interfaces.append(interface)

    @classmethod
    def get_other_modules_dataset_user_role(cls, session, uri, username, groups) -> str:
        """All other user role types that might come from other modules"""
        for interface in cls._interfaces:
            role = interface.resolve_additional_dataset_user_role(session, uri, username, groups)
            if role is not None:
                return role
        return None

    @classmethod
    def check_before_delete(cls, session, uri, **kwargs) -> bool:
        """All actions from other modules that need to be executed before deletion"""
        can_be_deleted = [interface.check_before_delete(session, uri, **kwargs) for interface in cls._interfaces]
        return all(can_be_deleted)

    @classmethod
    def execute_on_delete(cls, session, uri, **kwargs) -> bool:
        """All actions from other modules that need to be executed during deletion"""
        for interface in cls._interfaces:
            interface.execute_on_delete(session, uri, **kwargs)
        return True

    @classmethod
    def _attach_additional_steward_permissions(cls, session, dataset, new_stewards):
        """All permissions from other modules that need to be granted to stewards"""
        for interface in cls._interfaces:
            interface.extend_attach_steward_permissions(session, dataset, new_stewards)

    @classmethod
    def _delete_additional_steward_permissions(cls, session, dataset):
        """All permissions from other modules that need to be deleted to stewards"""
        for interface in cls._interfaces:
            interface.extend_delete_steward_permissions(session, dataset)

    @staticmethod
    def check_dataset_account(session, environment):
        dashboards_enabled = EnvironmentService.get_boolean_env_param(session, environment, 'dashboardsEnabled')
        if dashboards_enabled:
            quicksight_subscription = QuicksightClient.check_quicksight_enterprise_subscription(
                AwsAccountId=environment.AwsAccountId, region=environment.region
            )
            if quicksight_subscription:
                group = QuicksightClient.create_quicksight_group(
                    AwsAccountId=environment.AwsAccountId, region=environment.region
                )
                return True if group else False
        return True

    @staticmethod
    def check_imported_resources(dataset: S3Dataset, data: dict = {}):
        # check that resource names are valid
        if dataset.S3BucketName:
            NamingConventionService(
                target_uri=dataset.datasetUri,
                target_label=dataset.S3BucketName,
                pattern=NamingConventionPattern.S3,
            ).validate_imported_name()

        if dataset.importedGlueDatabase:
            NamingConventionService(
                target_uri=dataset.datasetUri,
                target_label=data.get('glueDatabaseName', 'undefined'),
                pattern=NamingConventionPattern.GLUE,
            ).validate_imported_name()

        with get_context().db_engine.scoped_session() as session:
            if DatasetBucketRepository.get_dataset_bucket_by_name(session, dataset.S3BucketName):
                raise exceptions.ResourceAlreadyExists(
                    action=IMPORT_DATASET,
                    message=f'Dataset with bucket {dataset.S3BucketName} already exists',
                )

        kms_alias = dataset.KmsAlias

        s3_encryption, kms_id_type, kms_id = S3DatasetClient(dataset).get_bucket_encryption()
        if kms_alias not in [None, 'Undefined', '', 'SSE-S3']:  # user-defined KMS encryption
            if s3_encryption == 'AES256':
                raise exceptions.InvalidInput(
                    param_name='KmsAlias',
                    param_value=dataset.KmsAlias,
                    constraint=f'empty, Bucket {dataset.S3BucketName} is encrypted with AWS managed key (SSE-S3). KmsAlias {kms_alias} should NOT be provided as input parameter.',
                )
            NamingConventionService(
                target_uri=dataset.datasetUri,
                target_label=kms_alias,
                pattern=NamingConventionPattern.KMS,
            ).validate_imported_name()

            key_exists = KmsClient(account_id=dataset.AwsAccountId, region=dataset.region).check_key_exists(
                key_alias=f'alias/{kms_alias}'
            )
            if not key_exists:
                raise exceptions.AWSResourceNotFound(
                    action=IMPORT_DATASET,
                    message=f'KMS key with alias={kms_alias} cannot be found - Please check if KMS Key Alias exists in account {dataset.AwsAccountId}',
                )

            key_matches = kms_id == kms_alias
            if kms_id_type == 'key':
                key_id = KmsClient(account_id=dataset.AwsAccountId, region=dataset.region).get_key_id(
                    key_alias=f'alias/{kms_alias}'
                )
                key_matches = key_id == kms_id

            if not key_matches:
                raise exceptions.InvalidInput(
                    param_name='KmsAlias',
                    param_value=dataset.KmsAlias,
                    constraint=f'the KMS Alias of the KMS key used to encrypt the Bucket {dataset.S3BucketName}. Provide the correct KMS Alias as input parameter.',
                )

        else:  # user-defined S3 encryption
            if s3_encryption != 'AES256':
                raise exceptions.RequiredParameter(param_name='KmsAlias')

        return True

    @staticmethod
    @TenantPolicyService.has_tenant_permission(MANAGE_DATASETS)
    @ResourcePolicyService.has_resource_permission(CREATE_DATASET)
    @GroupPolicyService.has_group_permission(CREATE_DATASET)
    def create_dataset(uri, admin_group, data: dict):
        context = get_context()
        with context.db_engine.scoped_session() as session:
            environment = EnvironmentService.get_environment_by_uri(session, uri)
            DatasetService.check_dataset_account(session=session, environment=environment)
            dataset = DatasetRepository.build_dataset(username=context.username, env=environment, data=data)

            if dataset.imported:
                DatasetService.check_imported_resources(dataset, data)

            dataset = DatasetRepository.create_dataset(session=session, env=environment, dataset=dataset, data=data)
            DatasetBucketRepository.create_dataset_bucket(session, dataset, data)

            ResourcePolicyService.attach_resource_policy(
                session=session,
                group=dataset.SamlAdminGroupName,
                permissions=DATASET_ALL,
                resource_uri=dataset.datasetUri,
                resource_type=DatasetBase.__name__,
            )
            if dataset.stewards and dataset.stewards != dataset.SamlAdminGroupName:
                ResourcePolicyService.attach_resource_policy(
                    session=session,
                    group=dataset.stewards,
                    permissions=DATASET_READ,
                    resource_uri=dataset.datasetUri,
                    resource_type=DatasetBase.__name__,
                )

            if environment.SamlGroupName != dataset.SamlAdminGroupName:
                ResourcePolicyService.attach_resource_policy(
                    session=session,
                    group=environment.SamlGroupName,
                    permissions=DATASET_ALL,
                    resource_uri=dataset.datasetUri,
                    resource_type=DatasetBase.__name__,
                )

            DatasetService._create_dataset_stack(session, dataset)

            DatasetIndexer.upsert(session=session, dataset_uri=dataset.datasetUri)

        DatasetService._deploy_dataset_stack(dataset)

        dataset.userRoleForDataset = DatasetRole.Creator.value

        return dataset

    @staticmethod
    def import_dataset(uri, admin_group, data):
        data['imported'] = True
        return DatasetService.create_dataset(uri=uri, admin_group=admin_group, data=data)

    @staticmethod
    @TenantPolicyService.has_tenant_permission(MANAGE_DATASETS)
    def get_dataset(uri):
        context = get_context()
        with context.db_engine.scoped_session() as session:
            dataset = DatasetRepository.get_dataset_by_uri(session, uri)
            if dataset.SamlAdminGroupName in context.groups:
                dataset.userRoleForDataset = DatasetRole.Admin.value
            return dataset

    @staticmethod
    @ResourcePolicyService.has_resource_permission(CREDENTIALS_DATASET)
    def get_file_upload_presigned_url(uri: str, data: dict):
        with get_context().db_engine.scoped_session() as session:
            dataset = DatasetRepository.get_dataset_by_uri(session, uri)
            return S3DatasetClient(dataset).get_file_upload_presigned_url(data)

    @staticmethod
    def list_locations(dataset_uri, data: dict):
        with get_context().db_engine.scoped_session() as session:
            return DatasetLocationRepository.paginated_dataset_locations(
                session=session,
                uri=dataset_uri,
                data=data,
            )

    @staticmethod
    def list_tables(dataset_uri, data: dict):
        context = get_context()
        with context.db_engine.scoped_session() as session:
            return DatasetRepository.paginated_dataset_tables(
                session=session,
                uri=dataset_uri,
                data=data,
            )

    @staticmethod
    @TenantPolicyService.has_tenant_permission(MANAGE_DATASETS)
    @ResourcePolicyService.has_resource_permission(UPDATE_DATASET)
    def update_dataset(uri: str, data: dict):
        with get_context().db_engine.scoped_session() as session:
            dataset = DatasetRepository.get_dataset_by_uri(session, uri)
            environment = EnvironmentService.get_environment_by_uri(session, dataset.environmentUri)
            DatasetService.check_dataset_account(session=session, environment=environment)

            username = get_context().username
            dataset: S3Dataset = DatasetRepository.get_dataset_by_uri(session, uri)
            if data and isinstance(data, dict):
                if data.get('imported', False):
                    DatasetService.check_imported_resources(dataset, data)

                for k in data.keys():
                    if k not in ['stewards', 'KmsAlias']:
                        setattr(dataset, k, data.get(k))

                ShareObjectRepository.update_dataset_shares_expiration(
                    session=session,
                    enabledExpiration=dataset.enableExpiration,
                    datasetUri=dataset.datasetUri,
                    expirationDate=ExpirationUtils.calculate_expiry_date(
                        expirationPeriod=dataset.expiryMinDuration, expirySetting=dataset.expirySetting
                    ),
                )

                if data.get('KmsAlias') not in ['Undefined'] and data.get('KmsAlias') != dataset.KmsAlias:
                    dataset.KmsAlias = 'SSE-S3' if data.get('KmsAlias') == '' else data.get('KmsAlias')
                    dataset.importedKmsKey = False if data.get('KmsAlias') == '' else True

                if data.get('stewards') and data.get('stewards') != dataset.stewards:
                    if data.get('stewards') != dataset.SamlAdminGroupName:
                        DatasetService._transfer_stewardship_to_new_stewards(session, dataset, data['stewards'])
                        dataset.stewards = data['stewards']
                    else:
                        DatasetService._transfer_stewardship_to_owners(session, dataset)
                        dataset.stewards = dataset.SamlAdminGroupName

                ResourcePolicyService.attach_resource_policy(
                    session=session,
                    group=dataset.SamlAdminGroupName,
                    permissions=DATASET_ALL,
                    resource_uri=dataset.datasetUri,
                    resource_type=DatasetBase.__name__,
                )
                if data.get('terms'):
                    GlossaryRepository.set_glossary_terms_links(session, username, uri, 'Dataset', data.get('terms'))
                DatasetBaseRepository.update_dataset_activity(session, dataset, username)

            DatasetIndexer.upsert(session, dataset_uri=uri)

        DatasetService._deploy_dataset_stack(dataset)

        return dataset

    @staticmethod
    def get_dataset_statistics(dataset: S3Dataset):
        with get_context().db_engine.scoped_session() as session:
            count_tables = DatasetRepository.count_dataset_tables(session, dataset.datasetUri)
            count_locations = DatasetLocationRepository.count_dataset_locations(session, dataset.datasetUri)
            count_upvotes = VoteRepository.count_upvotes(session, dataset.datasetUri, target_type='dataset')
        return {
            'tables': count_tables or 0,
            'locations': count_locations or 0,
            'upvotes': count_upvotes or 0,
        }

    @staticmethod
    @ResourcePolicyService.has_resource_permission(CREDENTIALS_DATASET)
    def get_dataset_assume_role_url(uri):
        context = get_context()
        with context.db_engine.scoped_session() as session:
            dataset = DatasetRepository.get_dataset_by_uri(session, uri)
            if dataset.SamlAdminGroupName in context.groups:
                role_arn = dataset.IAMDatasetAdminRoleArn
                account_id = dataset.AwsAccountId
                region = dataset.region

            else:
                raise exceptions.UnauthorizedOperation(
                    action=CREDENTIALS_DATASET,
                    message=f'{context.username=} is not a member of the group {dataset.SamlAdminGroupName}',
                )
        pivot_session = SessionHelper.remote_session(account_id, region)
        aws_session = SessionHelper.get_session(base_session=pivot_session, role_arn=role_arn)
        url = SessionHelper.get_console_access_url(
            aws_session,
            region=dataset.region,
            bucket=dataset.S3BucketName,
        )
        return url

    @staticmethod
    @ResourcePolicyService.has_resource_permission(CRAWL_DATASET)
    def start_crawler(uri: str, data: dict = None):
        engine = get_context().db_engine
        with engine.scoped_session() as session:
            dataset = DatasetRepository.get_dataset_by_uri(session, uri)
            location = os.path.join('s3://', dataset.S3BucketName, data.get('prefix', ''), '')
            crawler = DatasetCrawler(dataset).get_crawler()
            if not crawler:
                raise exceptions.AWSResourceNotFound(
                    action=CRAWL_DATASET,
                    message=f'Crawler {dataset.GlueCrawlerName} cannot be found',
                )

            task = Task(
                targetUri=uri,
                action='glue.crawler.start',
                payload={'location': location},
            )
            session.add(task)
            session.commit()

            Worker.queue(engine=engine, task_ids=[task.taskUri])

            return {
                'Name': dataset.GlueCrawlerName,
                'AwsAccountId': dataset.AwsAccountId,
                'region': dataset.region,
                'status': crawler.get('LastCrawl', {}).get('Status', 'N/A'),
            }

    @staticmethod
    @ResourcePolicyService.has_resource_permission(CREDENTIALS_DATASET)
    def generate_dataset_access_token(uri):
        with get_context().db_engine.scoped_session() as session:
            dataset = DatasetRepository.get_dataset_by_uri(session, uri)

        pivot_session = SessionHelper.remote_session(dataset.AwsAccountId, dataset.region)
        aws_session = SessionHelper.get_session(base_session=pivot_session, role_arn=dataset.IAMDatasetAdminRoleArn)
        c = aws_session.get_credentials()
        credentials = {
            'AccessKey': c.access_key,
            'SessionKey': c.secret_key,
            'sessionToken': c.token,
        }

        return json.dumps(credentials)

    @staticmethod
    @ResourcePolicyService.has_resource_permission(DELETE_DATASET)
    def delete_dataset(uri: str, delete_from_aws: bool = False):
        context = get_context()
        with context.db_engine.scoped_session() as session:
            dataset: S3Dataset = DatasetRepository.get_dataset_by_uri(session, uri)
            env = EnvironmentService.get_environment_by_uri(session, dataset.environmentUri)
            DatasetService.check_before_delete(session, uri, action=DELETE_DATASET)

            tables = [t.tableUri for t in DatasetRepository.get_dataset_tables(session, uri)]
            for tableUri in tables:
                DatasetIndexer.delete_doc(doc_id=tableUri)

            folders = [f.locationUri for f in DatasetLocationRepository.get_dataset_folders(session, uri)]
            for folderUri in folders:
                DatasetIndexer.delete_doc(doc_id=folderUri)

            DatasetIndexer.delete_doc(doc_id=uri)

            DatasetService.execute_on_delete(session, uri, action=DELETE_DATASET)
            DatasetService.delete_dataset_term_links(session, uri)
            DatasetTableRepository.delete_dataset_tables(session, dataset.datasetUri)
            DatasetLocationRepository.delete_dataset_locations(session, dataset.datasetUri)
            DatasetBucketRepository.delete_dataset_buckets(session, dataset.datasetUri)
            KeyValueTagRepository.delete_key_value_tags(session, dataset.datasetUri, 'dataset')
            VoteRepository.delete_votes(session, dataset.datasetUri, 'dataset')

            ResourcePolicyService.delete_resource_policy(
                session=session, resource_uri=uri, group=dataset.SamlAdminGroupName
            )
            env = EnvironmentService.get_environment_by_uri(session, dataset.environmentUri)
            if dataset.SamlAdminGroupName != env.SamlGroupName:
                ResourcePolicyService.delete_resource_policy(session=session, resource_uri=uri, group=env.SamlGroupName)
            if dataset.stewards:
                ResourcePolicyService.delete_resource_policy(session=session, resource_uri=uri, group=dataset.stewards)
            DatasetRepository.delete_dataset(session, dataset)

        if delete_from_aws:
            StackService.delete_stack(
                target_uri=uri,
                accountid=env.AwsAccountId,
                cdk_role_arn=env.CDKRoleArn,
                region=env.region,
            )
            StackService.deploy_stack(dataset.environmentUri)
        return True

    @staticmethod
    def _deploy_dataset_stack(dataset: S3Dataset):
        """
        Each dataset stack deployment triggers environment stack update
        to rebuild teams IAM roles data access policies
        """
        StackService.deploy_stack(dataset.datasetUri)
        StackService.deploy_stack(dataset.environmentUri)

    @staticmethod
    def _create_dataset_stack(session, dataset: S3Dataset) -> Stack:
        return StackRepository.create_stack(
            session=session,
            environment_uri=dataset.environmentUri,
            target_uri=dataset.datasetUri,
            target_type='dataset',
            payload={
                'bucket_name': dataset.S3BucketName,
                'database_name': dataset.GlueDatabaseName,
                'role_name': dataset.S3BucketName,
                'user_name': dataset.S3BucketName,
            },
        )

    @staticmethod
    def list_datasets_owned_by_env_group(env_uri: str, group_uri: str, data: dict):
        with get_context().db_engine.scoped_session() as session:
            return DatasetRepository.paginated_environment_group_datasets(
                session=session,
                env_uri=env_uri,
                group_uri=group_uri,
                data=data,
            )

    @staticmethod
    def _transfer_stewardship_to_owners(session, dataset):
        env = EnvironmentService.get_environment_by_uri(session, dataset.environmentUri)
        if dataset.stewards != env.SamlGroupName:
            ResourcePolicyService.delete_resource_policy(
                session=session,
                group=dataset.stewards,
                resource_uri=dataset.datasetUri,
            )

        # Remove Steward Resource Policy on Dataset Tables
        dataset_tables = [t.tableUri for t in DatasetRepository.get_dataset_tables(session, dataset.datasetUri)]
        for tableUri in dataset_tables:
            if dataset.stewards != env.SamlGroupName:
                ResourcePolicyService.delete_resource_policy(
                    session=session,
                    group=dataset.stewards,
                    resource_uri=tableUri,
                )

        DatasetService._delete_additional_steward_permissions(session, dataset)
        return dataset

    @staticmethod
    def _transfer_stewardship_to_new_stewards(session, dataset, new_stewards):
        env = EnvironmentService.get_environment_by_uri(session, dataset.environmentUri)
        if dataset.stewards != dataset.SamlAdminGroupName:
            ResourcePolicyService.delete_resource_policy(
                session=session,
                group=dataset.stewards,
                resource_uri=dataset.datasetUri,
            )
        ResourcePolicyService.attach_resource_policy(
            session=session,
            group=new_stewards,
            permissions=DATASET_READ,
            resource_uri=dataset.datasetUri,
            resource_type=DatasetBase.__name__,
        )

        dataset_tables = [t.tableUri for t in DatasetRepository.get_dataset_tables(session, dataset.datasetUri)]
        for tableUri in dataset_tables:
            if dataset.stewards != dataset.SamlAdminGroupName:
                ResourcePolicyService.delete_resource_policy(
                    session=session,
                    group=dataset.stewards,
                    resource_uri=tableUri,
                )
            ResourcePolicyService.attach_resource_policy(
                session=session,
                group=new_stewards,
                permissions=DATASET_TABLE_ALL,
                resource_uri=tableUri,
                resource_type=DatasetTable.__name__,
            )

        DatasetService._attach_additional_steward_permissions(session, dataset, new_stewards)

        return dataset

    @staticmethod
    def delete_dataset_term_links(session, dataset_uri):
        tables = [t.tableUri for t in DatasetRepository.get_dataset_tables(session, dataset_uri)]
        for table_uri in tables:
            GlossaryRepository.delete_glossary_terms_links(session, table_uri, 'DatasetTable')
        GlossaryRepository.delete_glossary_terms_links(session, dataset_uri, 'Dataset')

    @staticmethod
    @ResourcePolicyService.has_resource_permission(GET_DATASET)
    def list_s3_object_keys(uri):
        with get_context().db_engine.scoped_session() as session:
            dataset = DatasetRepository.get_dataset_by_uri(session, uri)

            return S3DatasetClient(dataset).list_object_keys(dataset.S3BucketName)

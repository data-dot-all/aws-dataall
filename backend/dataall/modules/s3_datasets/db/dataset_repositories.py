import logging

from sqlalchemy import and_, or_
from dataall.core.activity.db.activity_models import Activity
from dataall.core.environment.db.environment_models import Environment
from dataall.core.organizations.db.organization_repositories import OrganizationRepository
from dataall.base.db import paginate
from dataall.base.db.exceptions import ObjectNotFound
from dataall.modules.datasets_base.services.datasets_enums import ConfidentialityClassification, Language
from dataall.core.environment.services.environment_resource_manager import EnvironmentResource
from dataall.modules.s3_datasets.db.dataset_models import DatasetTable, S3Dataset
from dataall.base.utils.naming_convention import (
    NamingConventionService,
    NamingConventionPattern,
)

logger = logging.getLogger(__name__)


class DatasetRepository(EnvironmentResource):
    """DAO layer for Datasets"""

    @classmethod
    def build_dataset(cls, username: str, env: Environment, data: dict) -> S3Dataset:
        """Builds a datasets based on the request data, but doesn't save it in the database"""
        dataset = S3Dataset(
            label=data.get('label'),
            owner=username,
            description=data.get('description', 'No description provided'),
            tags=data.get('tags', []),
            AwsAccountId=env.AwsAccountId,
            SamlAdminGroupName=data['SamlAdminGroupName'],
            region=env.region,
            S3BucketName=data.get('bucketName', 'undefined'),
            GlueDatabaseName='undefined',
            IAMDatasetAdminRoleArn='undefined',
            IAMDatasetAdminUserArn='undefined',
            KmsAlias='undefined',
            environmentUri=env.environmentUri,
            organizationUri=env.organizationUri,
            language=data.get('language', Language.English.value),
            confidentiality=data.get('confidentiality', ConfidentialityClassification.Unclassified.value),
            topics=data.get('topics', []),
            businessOwnerEmail=data.get('businessOwnerEmail'),
            businessOwnerDelegationEmails=data.get('businessOwnerDelegationEmails', []),
            stewards=data.get('stewards') if data.get('stewards') else data['SamlAdminGroupName'],
            autoApprovalEnabled=data.get('autoApprovalEnabled', False),
        )

        cls._set_import_data(dataset, data)
        return dataset

    @staticmethod
    def get_dataset_by_uri(session, dataset_uri) -> S3Dataset: #TODO:rename as get_s3_dataset_by_uri; duplicated with base repo
        dataset: S3Dataset = session.query(S3Dataset).get(dataset_uri)
        if not dataset:
            raise ObjectNotFound('S3Dataset', dataset_uri)
        return dataset

    @classmethod
    def create_dataset(cls, session, env: Environment, dataset: S3Dataset, data: dict):
        organization = OrganizationRepository.get_organization_by_uri(session, env.organizationUri)
        session.add(dataset)
        session.commit()

        cls._set_dataset_aws_resources(dataset, data, env)

        activity = Activity(
            action='dataset:create',
            label='dataset:create',
            owner=dataset.owner,
            summary=f'{dataset.owner} created dataset {dataset.name} in {env.name} on organization {organization.name}',
            targetUri=dataset.datasetUri,
            targetType='dataset',
        )
        session.add(activity)
        return dataset

    @staticmethod
    def _set_dataset_aws_resources(dataset: S3Dataset, data, environment):
        bucket_name = NamingConventionService(
            target_uri=dataset.datasetUri,
            target_label=dataset.label,
            pattern=NamingConventionPattern.S3,
            resource_prefix=environment.resourcePrefix,
        ).build_compliant_name()
        dataset.S3BucketName = data.get('bucketName') or bucket_name

        glue_db_name = NamingConventionService(
            target_uri=dataset.datasetUri,
            target_label=dataset.label,
            pattern=NamingConventionPattern.GLUE,
            resource_prefix=environment.resourcePrefix,
        ).build_compliant_name()
        dataset.GlueDatabaseName = data.get('glueDatabaseName') or glue_db_name

        if not dataset.imported:
            dataset.KmsAlias = bucket_name

        iam_role_name = NamingConventionService(
            target_uri=dataset.datasetUri,
            target_label=dataset.label,
            pattern=NamingConventionPattern.IAM,
            resource_prefix=environment.resourcePrefix,
        ).build_compliant_name()
        iam_role_arn = f'arn:aws:iam::{dataset.AwsAccountId}:role/{iam_role_name}'
        if data.get('adminRoleName'):
            dataset.IAMDatasetAdminRoleArn = f"arn:aws:iam::{dataset.AwsAccountId}:role/{data['adminRoleName']}"
            dataset.IAMDatasetAdminUserArn = f"arn:aws:iam::{dataset.AwsAccountId}:role/{data['adminRoleName']}"
        else:
            dataset.IAMDatasetAdminRoleArn = iam_role_arn
            dataset.IAMDatasetAdminUserArn = iam_role_arn

        glue_etl_basename = NamingConventionService(
            target_uri=dataset.datasetUri,
            target_label=dataset.label,
            pattern=NamingConventionPattern.GLUE_ETL,
            resource_prefix=environment.resourcePrefix,
        ).build_compliant_name()

        dataset.GlueCrawlerName = f'{glue_etl_basename}-crawler'
        dataset.GlueProfilingJobName = f'{glue_etl_basename}-profiler'
        dataset.GlueProfilingTriggerSchedule = None
        dataset.GlueProfilingTriggerName = f'{glue_etl_basename}-trigger'
        dataset.GlueDataQualityJobName = f'{glue_etl_basename}-dataquality'
        dataset.GlueDataQualitySchedule = None
        dataset.GlueDataQualityTriggerName = f'{glue_etl_basename}-dqtrigger'
        return dataset

    @staticmethod
    def paginated_dataset_tables(session, uri, data=None) -> dict:
        query = (
            session.query(DatasetTable)
            .filter(
                and_(
                    DatasetTable.datasetUri == uri,
                    DatasetTable.LastGlueTableStatus != 'Deleted',
                )
            )
            .order_by(DatasetTable.created.desc())
        )
        if data and data.get('term'):
            query = query.filter(
                or_(
                    *[
                        DatasetTable.name.ilike('%' + data.get('term') + '%'),
                        DatasetTable.GlueTableName.ilike('%' + data.get('term') + '%'),
                    ]
                )
            )
        return paginate(query=query, page_size=data.get('pageSize', 10), page=data.get('page', 1)).to_dict()

    @staticmethod
    def update_bucket_status(session, dataset_uri):
        """
        helper method to update the dataset bucket status
        """
        dataset = DatasetRepository.get_dataset_by_uri(session, dataset_uri)
        dataset.bucketCreated = True
        return dataset

    @staticmethod
    def update_glue_database_status(session, dataset_uri):
        """
        helper method to update the dataset db status
        """
        dataset = DatasetRepository.get_dataset_by_uri(session, dataset_uri)
        dataset.glueDatabaseCreated = True

    @staticmethod
    def get_dataset_tables(session, dataset_uri):
        """return the dataset tables"""
        return session.query(DatasetTable).filter(DatasetTable.datasetUri == dataset_uri).all()

    @staticmethod
    def delete_dataset(session, dataset: S3Dataset) -> bool: # TODO: rename as S3_DATASET and check if needed
        session.delete(dataset)
        return True

    @staticmethod
    def get_dataset_by_bucket_name(session, bucket) -> [S3Dataset]:
        return session.query(S3Dataset).filter(S3Dataset.S3BucketName == bucket).first()

    @staticmethod
    def count_dataset_tables(session, dataset_uri):
        return session.query(DatasetTable).filter(DatasetTable.datasetUri == dataset_uri).count()


    @staticmethod
    def _set_import_data(dataset, data):
        dataset.imported = True if data.get('imported') else False
        dataset.importedS3Bucket = True if data.get('bucketName') else False
        dataset.importedGlueDatabase = True if data.get('glueDatabaseName') else False
        dataset.importedKmsKey = True if data.get('KmsKeyAlias') else False
        dataset.importedAdminRole = True if data.get('adminRoleName') else False
        if data.get('imported'):
            dataset.KmsAlias = data.get('KmsKeyAlias') if data.get('KmsKeyAlias') else 'SSE-S3'

from sqlalchemy import Boolean, Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSON, ARRAY
from sqlalchemy.orm import query_expression
from dataall.base.db import Base, Resource, utils
from dataall.modules.datasets_base.db.dataset_models import DatasetBase
from dataall.modules.datasets_base.services.datasets_enums import DatasetType


class DatasetTableColumn(Resource, Base):
    __tablename__ = 'dataset_table_column'
    datasetUri = Column(String, nullable=False)
    tableUri = Column(String, nullable=False)
    columnUri = Column(String, primary_key=True, default=utils.uuid('col'))
    AWSAccountId = Column(String, nullable=False)
    region = Column(String, nullable=False)
    GlueDatabaseName = Column(String, nullable=False)
    GlueTableName = Column(String, nullable=False)
    region = Column(String, default='eu-west-1')
    typeName = Column(String, nullable=False)
    columnType = Column(String, default='column')  # can be either "column" or "partition"

    @classmethod
    def uri(cls):
        return cls.columnUri


class DatasetProfilingRun(Resource, Base):
    __tablename__ = 'dataset_profiling_run'
    profilingRunUri = Column(String, primary_key=True, default=utils.uuid('profilingrun'))
    datasetUri = Column(String, nullable=False)
    GlueJobName = Column(String)
    GlueJobRunId = Column(String)
    GlueTriggerSchedule = Column(String)
    GlueTriggerName = Column(String)
    GlueTableName = Column(String)
    AwsAccountId = Column(String)
    results = Column(JSON, default={})
    status = Column(String, default='Created')


class DatasetStorageLocation(Resource, Base):
    __tablename__ = 'dataset_storage_location'
    datasetUri = Column(String, nullable=False)
    locationUri = Column(String, primary_key=True, default=utils.uuid('location'))
    AWSAccountId = Column(String, nullable=False)
    S3BucketName = Column(String, nullable=False)
    S3Prefix = Column(String, nullable=False)
    S3AccessPoint = Column(String, nullable=True)
    region = Column(String, default='eu-west-1')
    locationCreated = Column(Boolean, default=False)
    userRoleForStorageLocation = query_expression()
    projectPermission = query_expression()
    environmentEndPoint = query_expression()

    @classmethod
    def uri(cls):
        return cls.locationUri


class DatasetTable(Resource, Base):
    __tablename__ = 'dataset_table'
    datasetUri = Column(String, nullable=False)
    tableUri = Column(String, primary_key=True, default=utils.uuid('table'))
    AWSAccountId = Column(String, nullable=False)
    S3BucketName = Column(String, nullable=False)
    S3Prefix = Column(String, nullable=False)
    GlueDatabaseName = Column(String, nullable=False)
    GlueTableName = Column(String, nullable=False)
    GlueTableConfig = Column(Text)
    GlueTableProperties = Column(JSON, default={})
    LastGlueTableStatus = Column(String, default='InSync')
    region = Column(String, default='eu-west-1')
    # LastGeneratedPreviewDate= Column(DateTime, default=None)
    confidentiality = Column(String, nullable=True)
    userRoleForTable = query_expression()
    projectPermission = query_expression()
    stage = Column(String, default='RAW')
    topics = Column(ARRAY(String), nullable=True)
    confidentiality = Column(String, nullable=False, default='C1')

    @classmethod
    def uri(cls):
        return cls.tableUri


class S3Dataset(DatasetBase):
    __tablename__ = 's3_dataset'
    datasetUri = Column(String, ForeignKey('dataset.datasetUri'), primary_key=True)
    S3BucketName = Column(String, nullable=False)
    GlueDatabaseName = Column(String, nullable=False)
    GlueCrawlerName = Column(String)
    GlueCrawlerSchedule = Column(String)
    GlueProfilingJobName = Column(String)
    GlueProfilingTriggerSchedule = Column(String)
    GlueProfilingTriggerName = Column(String)
    GlueDataQualityJobName = Column(String)
    GlueDataQualitySchedule = Column(String)
    GlueDataQualityTriggerName = Column(String)
    IAMDatasetAdminRoleArn = Column(String, nullable=False)
    IAMDatasetAdminUserArn = Column(String, nullable=False)
    KmsAlias = Column(String, nullable=False)

    bucketCreated = Column(Boolean, default=False)
    glueDatabaseCreated = Column(Boolean, default=False)
    iamAdminRoleCreated = Column(Boolean, default=False)
    iamAdminUserCreated = Column(Boolean, default=False)
    kmsAliasCreated = Column(Boolean, default=False)
    lakeformationLocationCreated = Column(Boolean, default=False)
    bucketPolicyCreated = Column(Boolean, default=False)

    importedS3Bucket = Column(Boolean, default=False)
    importedGlueDatabase = Column(Boolean, default=False)
    importedKmsKey = Column(Boolean, default=False)
    importedAdminRole = Column(Boolean, default=False)

    __mapper_args__ = {
        'polymorphic_identity': DatasetType.S3.value,
    }


class DatasetBucket(Resource, Base):
    __tablename__ = 'dataset_bucket'
    datasetUri = Column(String, ForeignKey('dataset.datasetUri', ondelete='CASCADE'), nullable=False)
    bucketUri = Column(String, primary_key=True, default=utils.uuid('bucket'))
    AwsAccountId = Column(String, nullable=False)
    S3BucketName = Column(String, nullable=False)
    region = Column(String, default='eu-west-1')
    partition = Column(String, default='aws', nullable=False)
    KmsAlias = Column(String, nullable=False)
    imported = Column(Boolean, default=False)
    importedKmsKey = Column(Boolean, default=False)
    userRoleForStorageBucket = query_expression()
    projectPermission = query_expression()
    environmentEndPoint = query_expression()

    @classmethod
    def uri(cls):
        return cls.bucketUri


class DatasetLock(Base):
    __tablename__ = 'dataset_lock'
    datasetUri = Column(String, ForeignKey('dataset.datasetUri'), nullable=False, primary_key=True)
    isLocked = Column(Boolean, default=False, nullable=False)
    acquiredBy = Column(String, nullable=True)

    def __init__(self, datasetUri, isLocked=False, acquiredBy=None):
        self.datasetUri = datasetUri
        self.isLocked = isLocked
        self.acquiredBy = acquiredBy

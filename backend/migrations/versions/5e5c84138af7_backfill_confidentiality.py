"""backfill confidentiality

Revision ID: 5e5c84138af7
Revises: 94697ee46c0c
Create Date: 2021-09-15 13:41:44.102866

"""
from alembic import op

# revision identifiers, used by Alembic.
from sqlalchemy import orm, Column, String, Boolean
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.declarative import declarative_base

from dataall.base.db import utils, Resource
from dataall.modules.datasets_base.constants.enums import ConfidentialityClassification, Language


revision = '5e5c84138af7'
down_revision = '94697ee46c0c'
branch_labels = None
depends_on = None

Base = declarative_base()


class Dataset(Resource, Base):
    __tablename__ = 'dataset'
    environmentUri = Column(String, nullable=False)
    organizationUri = Column(String, nullable=False)
    datasetUri = Column(String, primary_key=True, default=utils.uuid('dataset'))
    region = Column(String, default='eu-west-1')
    AwsAccountId = Column(String, nullable=False)
    S3BucketName = Column(String, nullable=False)
    GlueDatabaseName = Column(String, nullable=False)
    GlueProfilingJobName = Column(String)
    GlueProfilingTriggerSchedule = Column(String)
    GlueProfilingTriggerName = Column(String)
    GlueDataQualityJobName = Column(String)
    GlueDataQualitySchedule = Column(String)
    GlueDataQualityTriggerName = Column(String)
    IAMDatasetAdminRoleArn = Column(String, nullable=False)
    IAMDatasetAdminUserArn = Column(String, nullable=False)
    KmsAlias = Column(String, nullable=False)
    language = Column(String, nullable=False, default=Language.English.value)
    topics = Column(postgresql.ARRAY(String), nullable=True)
    confidentiality = Column(String, nullable=False, default=ConfidentialityClassification.Unclassified.value)
    tags = Column(postgresql.ARRAY(String))

    bucketCreated = Column(Boolean, default=False)
    glueDatabaseCreated = Column(Boolean, default=False)
    iamAdminRoleCreated = Column(Boolean, default=False)
    iamAdminUserCreated = Column(Boolean, default=False)
    kmsAliasCreated = Column(Boolean, default=False)
    lakeformationLocationCreated = Column(Boolean, default=False)
    bucketPolicyCreated = Column(Boolean, default=False)

    businessOwnerEmail = Column(String, nullable=True)
    businessOwnerDelegationEmails = Column(postgresql.ARRAY(String), nullable=True)
    stewards = Column(String, nullable=True)

    SamlAdminGroupName = Column(String, nullable=True)

    importedS3Bucket = Column(Boolean, default=False)
    importedGlueDatabase = Column(Boolean, default=False)
    importedKmsKey = Column(Boolean, default=False)
    importedAdminRole = Column(Boolean, default=False)
    imported = Column(Boolean, default=False)


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    try:
        bind = op.get_bind()
        session = orm.Session(bind=bind)
        print('Updating datasets...')
        datasets: [Dataset] = session.query(Dataset).all()
        for dataset in datasets:
            if dataset.confidentiality not in ConfidentialityClassification:
                dataset.confidentiality = ConfidentialityClassification.Unclassified.value
                session.commit()
        print('Datasets updated successfully')
    except Exception as e:
        print(f'Failed to init permissions due to: {e}')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###

import logging

import pytest

import dataall

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logging.getLogger('boto3').setLevel(logging.CRITICAL)
logging.getLogger('botocore').setLevel(logging.CRITICAL)

REGION = 'eu-central-1'

ENV_ACCOUNT = ''
ENV_ROLE_NAME = 'dataall-World-Happiness-Report-i6v1v1c2'
ENV_ROLE_ARN = f'arn:aws:iam::{ENV_ACCOUNT}:role/{ENV_ROLE_NAME}'


CROSS_ACCOUNT_ENV = ''
CROSS_ACCOUNT_ENV_ROLE_NAME = 'dataall-ConsumersEnvironment-r71ucp4m'
CROSS_ACCOUNT_ENV_ROLE_ARN = (
    f'arn:aws:iam::{CROSS_ACCOUNT_ENV}:role/{CROSS_ACCOUNT_ENV_ROLE_NAME}'
)

DATASET_GLUE_DB = 'dataall_world_happiness_report_i6v1v1c2'
DATASET_S3_BUCKET = 'dataall-world-happiness-report-i6v1v1c2'

TABLE_NAME = 'dataall_world_happiness_report_i6v1v1c2'
TABLE_S3_PREFIX = f's3://{DATASET_S3_BUCKET}/'

FOLDER_NAME = 'dataall_folder'
FOLDER_NAME_2 = 'dataall_folder_2'


@pytest.fixture(scope='module')
def org(db):
    with db.scoped_session() as session:
        org = dataall.db.models.Organization(
            label='org',
            owner='alice',
            tags=[],
            description='desc',
            SamlGroupName='admins',
        )
        session.add(org)
    yield org


@pytest.fixture(scope='module')
def env(org, db):
    with db.scoped_session() as session:
        env = dataall.db.models.Environment(
            organizationUri=org.organizationUri,
            AwsAccountId=ENV_ACCOUNT,
            region='eu-central-1',
            label='org',
            owner='alice',
            tags=[],
            description='desc',
            SamlGroupName='admins',
            EnvironmentDefaultIAMRoleName=ENV_ROLE_NAME,
            EnvironmentDefaultIAMRoleArn=ENV_ROLE_ARN,
            CDKRoleArn=f'arn:aws::{ENV_ACCOUNT}:role/EnvRole',
            environmentUri='mytest',
        )
        session.add(env)
        session.commit()
        env_group = dataall.db.models.EnvironmentGroup(
            environmentUri=env.environmentUri,
            groupUri='bobTeam',
            environmentIAMRoleArn=env.EnvironmentDefaultIAMRoleArn,
            environmentIAMRoleName=env.EnvironmentDefaultIAMRoleName,
            environmentAthenaWorkGroup='workgroup',
        )
        session.add(env_group)
    yield env


@pytest.fixture(scope='module')
def cross_account_env(org, db):
    with db.scoped_session() as session:
        env = dataall.db.models.Environment(
            organizationUri=org.organizationUri,
            AwsAccountId=CROSS_ACCOUNT_ENV,
            region='eu-central-1',
            label='org',
            owner='bob',
            tags=[],
            description='desc',
            SamlGroupName='bobTeam',
            EnvironmentDefaultIAMRoleName=CROSS_ACCOUNT_ENV_ROLE_NAME,
            EnvironmentDefaultIAMRoleArn=CROSS_ACCOUNT_ENV_ROLE_ARN,
            CDKRoleArn=f'arn:aws::{CROSS_ACCOUNT_ENV}:role/EnvRole',
        )
        session.add(env)
        session.commit()
        env_group = dataall.db.models.EnvironmentGroup(
            environmentUri=env.environmentUri,
            groupUri=env.SamlGroupName,
            environmentIAMRoleArn=env.EnvironmentDefaultIAMRoleArn,
            environmentIAMRoleName=env.EnvironmentDefaultIAMRoleName,
            environmentAthenaWorkGroup='workgroup',
        )
        session.add(env_group)
    yield env


@pytest.fixture(scope='module')
def dataset(org, env, db):
    with db.scoped_session() as session:
        dataset = dataall.db.models.Dataset(
            organizationUri=org.organizationUri,
            environmentUri=env.environmentUri,
            label=DATASET_S3_BUCKET,
            owner='alice',
            SamlAdminGroupName='admins',
            businessOwnerDelegationEmails=['foo@amazon.com'],
            name=DATASET_S3_BUCKET,
            S3BucketName=DATASET_S3_BUCKET,
            GlueDatabaseName=DATASET_GLUE_DB,
            KmsAlias='kmsalias',
            AwsAccountId=env.AwsAccountId,
            region=env.region,
            IAMDatasetAdminUserArn=f'arn:aws:iam::{ENV_ACCOUNT}:user/dataset',
            IAMDatasetAdminRoleArn=f'arn:aws:iam::{ENV_ACCOUNT}:role/dataset',
        )
        session.add(dataset)
    yield dataset


@pytest.fixture(scope='module')
def table(org, env, db, dataset):
    with db.scoped_session() as session:
        table = dataall.db.models.DatasetTable(
            label=TABLE_NAME,
            name=TABLE_NAME,
            owner='alice',
            description='test table',
            tags=['a', 'b'],
            datasetUri=dataset.datasetUri,
            S3Prefix=TABLE_S3_PREFIX,
            GlueDatabaseName=dataset.GlueDatabaseName,
            GlueTableName=TABLE_NAME,
            S3BucketName=dataset.S3BucketName,
            AWSAccountId=dataset.AwsAccountId,
            region=dataset.region,
        )
        session.add(table)
    yield table


@pytest.fixture(scope='module')
def table2(org, env, db, dataset):
    with db.scoped_session() as session:
        table = dataall.db.models.DatasetTable(
            label='deleted_glue_table',
            name='deleted_glue_table',
            owner='alice',
            description='test table',
            tags=['a', 'b'],
            datasetUri=dataset.datasetUri,
            S3Prefix='s3://dataall-world-happiness-report-i6v1v1c2/',
            GlueDatabaseName=dataset.GlueDatabaseName,
            GlueTableName='deleted_glue_table',
            S3BucketName=dataset.S3BucketName,
            AWSAccountId=dataset.AwsAccountId,
            region=dataset.region,
        )
        session.add(table)
    yield table


@pytest.fixture(scope='module')
def folder(org, env, db, dataset):
    with db.scoped_session() as session:
        folder = dataall.db.models.DatasetStorageLocation(
            label=FOLDER_NAME,
            name=FOLDER_NAME,
            owner='alice',
            description='test table',
            datasetUri=dataset.datasetUri,
            AWSAccountId=dataset.AwsAccountId,
            S3BucketName=dataset.S3BucketName,
            S3Prefix=FOLDER_NAME,
            region=dataset.region
        )
        session.add(folder)
    yield folder


@pytest.fixture(scope='module')
def folder2(org, env, db, dataset):
    with db.scoped_session() as session:
        folder = dataall.db.models.DatasetStorageLocation(
            label=FOLDER_NAME_2,
            name=FOLDER_NAME_2,
            owner='alice',
            description='test table 2',
            datasetUri=dataset.datasetUri,
            AWSAccountId=dataset.AwsAccountId,
            S3BucketName=dataset.S3BucketName,
            S3Prefix=FOLDER_NAME_2,
            region=dataset.region
        )
        session.add(folder)
    yield folder


@pytest.fixture(scope='module')
def cross_account_table_share(
    dataset: dataall.db.models.Dataset,
    db: dataall.db.Engine,
    cross_account_env: dataall.db.models.Environment,
    table: dataall.db.models.DatasetTable,
    table2: dataall.db.models.DatasetTable,
):
    with db.scoped_session() as session:
        share = dataall.db.models.ShareObject(
            shareUri='cross',
            datasetUri=dataset.datasetUri,
            environmentUri=cross_account_env.environmentUri,
            owner='bob',
            principalId=cross_account_env.SamlGroupName,
            principalType=dataall.api.constants.PrincipalType.Group.value,
            principalIAMRoleName=cross_account_env.SamlGroupName,
            status=dataall.api.constants.ShareObjectStatus.Approved.value,
        )
        session.add(share)
        session.commit()
        share_item = dataall.db.models.ShareObjectItem(
            shareUri=share.shareUri,
            owner='alice',
            itemUri=table.tableUri,
            itemType=dataall.api.constants.ShareableType.Table.value,
            itemName=table.GlueTableName,
            GlueDatabaseName=table.GlueDatabaseName,
            GlueTableName=table.GlueTableName,
            S3AccessPointName='',
            status=dataall.api.constants.ShareItemStatus.Share_Approved.value,
        )
        session.add(share_item)
        share_item = dataall.db.models.ShareObjectItem(
            shareUri=share.shareUri,
            owner='alice',
            itemUri=table2.tableUri,
            itemType=dataall.api.constants.ShareableType.Table.value,
            itemName=table2.GlueTableName,
            GlueDatabaseName=table2.GlueDatabaseName,
            GlueTableName=table2.GlueTableName,
            S3AccessPointName='',
            status=dataall.api.constants.ShareItemStatus.Share_Approved.value,
        )
        session.add(share_item)
        session.commit()
        yield share


@pytest.fixture(scope='module')
def same_account_table_share(
    dataset: dataall.db.models.Dataset,
    db: dataall.db.Engine,
    env: dataall.db.models.Environment,
    table: dataall.db.models.DatasetTable,
):
    with db.scoped_session() as session:
        share = dataall.db.models.ShareObject(
            shareUri='same',
            datasetUri=dataset.datasetUri,
            environmentUri=env.environmentUri,
            owner='bob',
            principalId='bobTeam',
            principalType=dataall.api.constants.PrincipalType.Group.value,
            principalIAMRoleName='bobTeam',
            status=dataall.api.constants.ShareObjectStatus.Approved.value,
        )
        session.add(share)
        session.commit()
        share_item = dataall.db.models.ShareObjectItem(
            shareUri=share.shareUri,
            owner='alice',
            itemUri=table.tableUri,
            itemType=dataall.api.constants.ShareableType.Table.value,
            itemName=table.GlueTableName,
            GlueDatabaseName=table.GlueDatabaseName,
            GlueTableName=table.GlueTableName,
            S3AccessPointName='',
            status=dataall.api.constants.ShareItemStatus.Share_Approved.value,
        )
        session.add(share_item)
        yield share

@pytest.fixture(scope='module')
def cross_account_folder_share(
    dataset: dataall.db.models.Dataset,
    db: dataall.db.Engine,
    cross_account_env: dataall.db.models.Environment,
    folder: dataall.db.models.DatasetStorageLocation,
    folder2: dataall.db.models.DatasetStorageLocation,
):
    with db.scoped_session() as session:
        share = dataall.db.models.ShareObject(
            shareUri='cross',
            datasetUri=dataset.datasetUri,
            environmentUri=cross_account_env.environmentUri,
            owner='bob',
            principalId=cross_account_env.SamlGroupName,
            principalType=dataall.api.constants.PrincipalType.Group.value,
            principalIAMRoleName=cross_account_env.SamlGroupName,
            status=dataall.api.constants.ShareObjectStatus.Approved.value,
        )
        session.add(share)
        session.commit()
        share_item = dataall.db.models.ShareObjectItem(
            shareUri=share.shareUri,
            owner='alice',
            itemUri=folder.locationUri,
            itemType=dataall.api.constants.ShareableType.StorageLocation.value,
            itemName=table.GlueTableName,
            GlueDatabaseName="",
            GlueTableName="",
            S3AccessPointName=f'{share.datasetUri}-{share.principalId}'.lower(),
            status=dataall.api.constants.ShareItemStatus.Share_Approved.value,
        )
        session.add(share_item)
        share_item = dataall.db.models.ShareObjectItem(
            shareUri=share.shareUri,
            owner='alice',
            itemUri=folder2.locationUri,
            itemType=dataall.api.constants.ShareableType.StorageLocation.value,
            itemName=table2.GlueTableName,
            GlueDatabaseName="",
            GlueTableName="",
            S3AccessPointName=f'{share.datasetUri}-{share.principalId}'.lower(),
            status=dataall.api.constants.ShareItemStatus.Share_Approved.value,
        )
        session.add(share_item)
        session.commit()
        yield share


@pytest.fixture(scope='module')
def same_account_folder_share(
    dataset: dataall.db.models.Dataset,
    db: dataall.db.Engine,
    env: dataall.db.models.Environment,
    table: dataall.db.models.DatasetTable,
):
    with db.scoped_session() as session:
        share = dataall.db.models.ShareObject(
            shareUri='same',
            datasetUri=dataset.datasetUri,
            environmentUri=env.environmentUri,
            owner='bob',
            principalId='bobTeam',
            principalType=dataall.api.constants.PrincipalType.Group.value,
            principalIAMRoleName='bobTeam',
            status=dataall.api.constants.ShareObjectStatus.Approved.value,
        )
        session.add(share)
        session.commit()
        share_item = dataall.db.models.ShareObjectItem(
            shareUri=share.shareUri,
            owner='alice',
            itemUri=table.tableUri,
            itemType=dataall.api.constants.ShareableType.Table.value,
            itemName=table.GlueTableName,
            GlueDatabaseName=table.GlueDatabaseName,
            GlueTableName=table.GlueTableName,
            status=dataall.api.constants.ShareItemStatus.Share_Approved.value,
        )
        session.add(share_item)
        yield share


def __update_to_rejected_status(db, share):
    with db.scoped_session() as session:
        share.status = dataall.api.constants.ShareObjectStatus.Rejected.value
        session.merge(share)


def test_cross_account_table_sharing(db, cross_account_share, dataset, mocker):
    mocker.patch(
        'dataall.tasks.data_sharing.data_sharing_service.DataSharingService.process_share',
        return_value=True,
    )
    mocker.patch(
        'dataall.tasks.data_sharing.data_sharing_service.DataSharingService.revoke_share',
        return_value=True,
    )
    dataall.tasks.data_sharing.data_sharing_service.DataSharingService.process_share(
        db, cross_account_share.shareUri
    )

    __update_to_rejected_status(db, cross_account_share)

    dataall.tasks.data_sharing.data_sharing_service.DataSharingService.revoke_share(
        db, cross_account_share.shareUri
    )


def test_same_account_table_sharing(db, same_account_share, dataset, mocker):
    mocker.patch(
        'dataall.tasks.data_sharing.data_sharing_service.DataSharingService.process_share',
        return_value=True,
    )
    mocker.patch(
        'dataall.tasks.data_sharing.data_sharing_service.DataSharingService.revoke_share',
        return_value=True,
    )
    dataall.tasks.data_sharing.data_sharing_service.DataSharingService.process_share(
        db, same_account_share.shareUri
    )

    __update_to_rejected_status(db, same_account_share)

    dataall.tasks.data_sharing.data_sharing_service.DataSharingService.revoke_share(
        db, same_account_share.shareUri
    )


def test_refresh_shares(db, same_account_share, cross_account_share, dataset, mocker):
    mocker.patch(
        'dataall.tasks.data_sharing.data_sharing_service.DataSharingService.refresh_shares',
        return_value=True,
    )
    mocker.patch('dataall.utils.Parameter.get_parameter', return_value='True')
    assert dataall.tasks.data_sharing.data_sharing_service.DataSharingService.refresh_shares(
        db
    )

    __update_to_rejected_status(db, same_account_share)
    __update_to_rejected_status(db, cross_account_share)

    assert dataall.tasks.data_sharing.data_sharing_service.DataSharingService.refresh_shares(
        db
    )


def test_share_object_actions(db, same_account_table_share):
    with db.scoped_session() as session:
        share_SM = dataall.db.api.ShareObjectSM(same_account_table_share.status)

        assert share_SM._state == dataall.api.constants.ShareObjectStatus.Draft.value
        new_share_state = share_SM.run_transition(dataall.api.constants.ShareObjectActions.Submit.value)
        share_SM.update_state(session, same_account_table_share, new_share_state)

        assert share_SM._state == dataall.api.constants.ShareObjectStatus.Submitted.value
        assert same_account_table_share.status == dataall.api.constants.ShareObjectStatus.Submitted.value


def test_share_item_actions(db):
    assert None == None
import logging
import time

import pytest
import boto3
import json
import os
from integration_tests.client import GqlError
from integration_tests.core.stack.utils import check_stack_ready

from integration_tests.modules.s3_datasets.queries import (
    create_dataset,
    generate_dataset_access_token,
    import_dataset,
    delete_dataset,
    get_dataset,
    sync_tables,
    create_folder,
    create_table_data_filter,
)
from tests_new.integration_tests.modules.datasets_base.queries import list_datasets
from integration_tests.aws_clients.s3 import S3Client as S3CommonClient
from integration_tests.modules.s3_datasets.aws_clients import S3Client, KMSClient, GlueClient, LakeFormationClient
from integration_tests.core.stack.queries import update_stack

log = logging.getLogger(__name__)

COL_FILTER_INPUT = {
    'filterName': 'columnfilter',
    'description': 'test column',
    'filterType': 'COLUMN',
    'includedCols': ['column1'],
}
ROW_FILTER_INPUT = {
    'filterName': 'rowfilter',
    'description': 'test row',
    'filterType': 'ROW',
    'rowExpression': '"column2" LIKE \'%value%\' AND "column1" IS NOT NULL',
}


def create_s3_dataset(
    client, name, owner, group, org_uri, env_uri, tags=[], autoApprovalEnabled=False, confidentiality=None
):
    dataset = create_dataset(
        client,
        name=name,
        owner=owner,
        group=group,
        organizationUri=org_uri,
        environmentUri=env_uri,
        tags=tags,
        autoApprovalEnabled=autoApprovalEnabled,
        confidentiality=confidentiality,
    )
    check_stack_ready(
        client=client,
        env_uri=env_uri,
        stack_uri=dataset.stack.stackUri,
        target_uri=dataset.datasetUri,
        target_type='dataset',
    )
    return get_dataset(client, dataset.datasetUri)


def create_aws_imported_resources(
    aws_client, env, bucket_name, kms_alias_name=None, glue_database_name=None, integration_role_arn=None
):
    bucket = None
    kms_alias = None
    database = None
    existing_lf_admins = None
    try:
        if bucket_name:
            if kms_alias_name:
                kms_id, kms_alias = KMSClient(
                    session=aws_client,
                    account_id=env['AwsAccountId'],
                    region=env['region'],
                ).create_key_with_alias(kms_alias_name)
                bucket = S3Client(session=aws_client, region=env['region']).create_bucket(
                    bucket_name=bucket_name,
                    kms_key_arn=f"arn:aws:kms:{env['region']}:{env['AwsAccountId']}:key/{kms_id}",
                )
            else:
                bucket = S3Client(session=aws_client, region=env['region']).create_bucket(
                    bucket_name=bucket_name,
                )
        if glue_database_name:
            lf_client = LakeFormationClient(session=aws_client, region=env['region'])
            existing_lf_admins = lf_client.add_role_to_datalake_admin(role_arn=integration_role_arn)
            if lf_client.grant_create_database(role_arn=integration_role_arn):
                database = GlueClient(session=aws_client, region=env['region']).create_database(
                    database_name=glue_database_name, bucket=bucket
                )
    except Exception as e:
        log.exception(f'Error creating imported dataset AWS resources due to: {e}')
    return bucket, kms_alias, database, existing_lf_admins


def delete_aws_dataset_resources(aws_client, env, bucket=None, kms_alias=None, database=None, existing_lf_admins=None):
    try:
        if bucket:
            S3CommonClient(session=aws_client, account=env.AwsAccountId, region=env.region).delete_bucket(bucket)
        if kms_alias:
            KMSClient(
                session=aws_client,
                account_id=env['AwsAccountId'],
                region=env['region'],
            ).delete_key_by_alias(kms_alias)
        if existing_lf_admins:
            LakeFormationClient(session=aws_client, region=env['region']).remove_role_from_datalake_admin(
                existing_lf_admins
            )
        if database:
            GlueClient(session=aws_client, region=env['region']).delete_database(database)
    except Exception:
        log.exception('Error deleting imported dataset AWS resources')


def import_s3_dataset(
    client,
    name,
    owner,
    group,
    org_uri,
    env_uri,
    bucket,
    kms_alias='',
    glue_db_name='',
    tags=[],
    autoApprovalEnabled=False,
    confidentiality=None,
):
    dataset = import_dataset(
        client,
        name=name,
        owner=owner,
        group=group,
        organizationUri=org_uri,
        environmentUri=env_uri,
        tags=tags,
        bucketName=bucket,
        KmsKeyAlias=kms_alias,
        glueDatabaseName=glue_db_name,
        autoApprovalEnabled=autoApprovalEnabled,
        confidentiality=confidentiality,
    )
    check_stack_ready(
        client=client,
        env_uri=env_uri,
        stack_uri=dataset.stack.stackUri,
        target_uri=dataset.datasetUri,
        target_type='dataset',
    )
    return get_dataset(client, dataset.datasetUri)


def delete_s3_dataset(client, env_uri, dataset):
    check_stack_ready(
        client=client,
        env_uri=env_uri,
        stack_uri=dataset.stack.stackUri,
        target_uri=dataset.datasetUri,
        target_type='dataset',
    )
    try:
        return delete_dataset(client, dataset.datasetUri)
    except GqlError:
        log.exception('unexpected error when deleting dataset')
        return False


def create_tables(client, dataset):
    creds = json.loads(generate_dataset_access_token(client, dataset.datasetUri))
    dataset_session = boto3.Session(
        aws_access_key_id=creds['AccessKey'],
        aws_secret_access_key=creds['SessionKey'],
        aws_session_token=creds['sessionToken'],
    )
    file_path = os.path.join(os.path.dirname(__file__), 'sample_data/csv_table/csv_sample.csv')
    s3_client = S3Client(dataset_session, dataset.region)
    glue_client = GlueClient(dataset_session, dataset.region)
    s3_client.upload_file_to_prefix(local_file_path=file_path, s3_path=f'{dataset.S3BucketName}/integrationtest1')
    glue_client.create_table(
        database_name=dataset.GlueDatabaseName, table_name='integrationtest1', bucket=dataset.S3BucketName
    )

    s3_client.upload_file_to_prefix(local_file_path=file_path, s3_path=f'{dataset.S3BucketName}/integrationtest2')
    glue_client.create_table(
        database_name=dataset.GlueDatabaseName, table_name='integrationtest2', bucket=dataset.S3BucketName
    )
    response = sync_tables(client, datasetUri=dataset.datasetUri)
    return [table for table in response.get('nodes', []) if table.GlueTableName.startswith('integrationtest')]


def create_folders(client, dataset):
    folderA = create_folder(
        client, datasetUri=dataset.datasetUri, input={'prefix': 'sessionFolderA', 'label': 'labelSessionFolderA'}
    )
    folderB = create_folder(
        client, datasetUri=dataset.datasetUri, input={'prefix': 'sessionFolderB', 'label': 'labelSessionFolderB'}
    )

    return [folderA, folderB]


def create_filters(client, tables):
    filter_list = []
    for table in tables:
        filter_list.append(create_table_data_filter(client, table.tableUri, input=COL_FILTER_INPUT))
        filter_list.append(create_table_data_filter(client, table.tableUri, input=ROW_FILTER_INPUT))

    return filter_list


"""
Session envs persist across the duration of the whole integ test suite and are meant to make the test suite run faster (env creation takes ~2 mins).
For this reason they must stay immutable as changes to them will affect the rest of the tests.
"""


@pytest.fixture(scope='session')
def session_s3_dataset1(client1, group1, org1, session_env1, session_id, testdata, session_env1_aws_client):
    ds = None
    try:
        ds = create_s3_dataset(
            client1,
            name='session_s3_dataset1',
            owner='someone',
            group=group1,
            org_uri=org1['organizationUri'],
            env_uri=session_env1['environmentUri'],
            tags=[session_id],
            confidentiality='Unclassified',
        )
        yield ds
    finally:
        if ds:
            delete_s3_dataset(client1, session_env1['environmentUri'], ds)
            delete_aws_dataset_resources(aws_client=session_env1_aws_client, env=session_env1, bucket=ds.S3BucketName)


@pytest.fixture(scope='session')
def session_s3_dataset1_tables(client1, session_s3_dataset1):
    yield create_tables(client1, session_s3_dataset1)


@pytest.fixture(scope='session')
def session_s3_dataset1_folders(client1, session_s3_dataset1):
    yield create_folders(client1, session_s3_dataset1)


@pytest.fixture(scope='session')
def session_imported_sse_s3_dataset1(
    client1, group1, org1, session_env1, session_id, testdata, session_env1_aws_client, resources_prefix
):
    bucket, kms_alias, database, existing_lf_admins = create_aws_imported_resources(
        aws_client=session_env1_aws_client,
        env=session_env1,
        bucket_name=f'{resources_prefix}importedsses3',
    )
    if not bucket:
        raise Exception('Error creating import dataset AWS resources')
    ds = None
    try:
        ds = import_s3_dataset(
            client1,
            name='session_imported_sse_s3_dataset1',
            owner='someone',
            group=group1,
            org_uri=org1['organizationUri'],
            env_uri=session_env1['environmentUri'],
            tags=[session_id],
            bucket=bucket,
            confidentiality='Official',
            autoApprovalEnabled=True,
        )
        yield ds
    finally:
        if ds:
            delete_s3_dataset(client1, session_env1['environmentUri'], ds)
        delete_aws_dataset_resources(aws_client=session_env1_aws_client, env=session_env1, bucket=bucket)


@pytest.fixture(scope='session')
def session_imported_sse_s3_dataset1_tables(client1, session_imported_sse_s3_dataset1):
    yield create_tables(client1, session_imported_sse_s3_dataset1)


@pytest.fixture(scope='session')
def session_imported_sse_s3_dataset1_folders(client1, session_imported_sse_s3_dataset1):
    yield create_folders(client1, session_imported_sse_s3_dataset1)


@pytest.fixture(scope='session')
def session_imported_kms_s3_dataset1(
    client1,
    group1,
    org1,
    session_env1,
    session_id,
    testdata,
    session_env1_aws_client,
    session_env1_integration_role_arn,
    resources_prefix,
):
    resource_name = f'{resources_prefix}importedkms'
    bucket, kms_alias, database, existing_lf_admins = create_aws_imported_resources(
        aws_client=session_env1_aws_client,
        integration_role_arn=session_env1_integration_role_arn,
        env=session_env1,
        bucket_name=resource_name,
        kms_alias_name=resource_name,
        glue_database_name=resource_name,
    )
    if None in [bucket, database, kms_alias]:
        raise Exception('Error creating import dataset AWS resources')
    ds = None
    try:
        ds = import_s3_dataset(
            client1,
            name='session_imported_kms_s3_dataset1',
            owner='someone',
            group=group1,
            org_uri=org1['organizationUri'],
            env_uri=session_env1['environmentUri'],
            tags=[session_id],
            bucket=bucket,
            kms_alias=kms_alias,
            glue_db_name=database,
            confidentiality='Secret',
        )
        yield ds
    finally:
        if ds:
            delete_s3_dataset(client1, session_env1['environmentUri'], ds)
        delete_aws_dataset_resources(
            aws_client=session_env1_aws_client,
            env=session_env1,
            bucket=bucket,
            kms_alias=kms_alias,
            database=database,
            existing_lf_admins=existing_lf_admins,
        )


@pytest.fixture(scope='session')
def session_imported_kms_s3_dataset1_tables(client1, session_imported_kms_s3_dataset1):
    yield create_tables(client1, session_imported_kms_s3_dataset1)


@pytest.fixture(scope='session')
def session_imported_kms_s3_dataset1_folders(client1, session_imported_kms_s3_dataset1):
    yield create_folders(client1, session_imported_kms_s3_dataset1)


@pytest.fixture(scope='session')
def session_s3_dataset1_tables_data_filters(client1, session_s3_dataset1_tables):
    yield create_filters(client1, session_s3_dataset1_tables)


@pytest.fixture(scope='session')
def session_imported_sse_s3_dataset1_tables_data_filters(client1, session_imported_sse_s3_dataset1_tables):
    yield create_filters(client1, session_imported_sse_s3_dataset1_tables)


@pytest.fixture(scope='session')
def session_imported_kms_s3_dataset1_tables_data_filters(client1, session_imported_kms_s3_dataset1_tables):
    yield create_filters(client1, session_imported_kms_s3_dataset1_tables)


"""
Temp envs will be created and deleted per test, use with caution as they might increase the runtime of the test suite.
They are suitable to test env mutations.
"""


@pytest.fixture(scope='function')
def temp_s3_dataset1(client1, group1, org1, session_env1, session_id, testdata, session_env1_aws_client):
    ds = None
    try:
        ds = create_s3_dataset(
            client1,
            name='temp_s3_dataset1',
            owner='someone',
            group=group1,
            org_uri=org1['organizationUri'],
            env_uri=session_env1['environmentUri'],
            tags=[session_id],
        )
        yield ds
    finally:
        if ds:
            delete_s3_dataset(client1, session_env1['environmentUri'], ds)

            delete_aws_dataset_resources(aws_client=session_env1_aws_client, env=session_env1, bucket=ds.S3BucketName)


"""
Persistent environments must always be present (if not i.e first run they will be created but won't be removed).
They are suitable for testing backwards compatibility. 
"""


def get_or_create_persistent_s3_dataset(
    dataset_name,
    client,
    group,
    env,
    autoApprovalEnabled=False,
    bucket=None,
    kms_alias='',
    glue_database='',
    withContent=False,
):
    dataset_name = dataset_name or 'persistent_s3_dataset1'
    s3_datasets = list_datasets(client, term=dataset_name).nodes
    if s3_datasets:
        return s3_datasets[0]
    else:
        if bucket:
            s3_dataset = import_s3_dataset(
                client,
                name=dataset_name,
                owner='someone',
                group=group,
                org_uri=env['organization']['organizationUri'],
                env_uri=env['environmentUri'],
                tags=[dataset_name],
                bucket=bucket,
                kms_alias=kms_alias,
                glue_db_name=glue_database,
                autoApprovalEnabled=autoApprovalEnabled,
            )

        else:
            s3_dataset = create_s3_dataset(
                client,
                name=dataset_name,
                owner='someone',
                group=group,
                org_uri=env['organization']['organizationUri'],
                env_uri=env['environmentUri'],
                tags=[dataset_name],
                autoApprovalEnabled=autoApprovalEnabled,
            )
            if withContent:
                create_tables(client, s3_dataset)
                create_folders(client, s3_dataset)
                creds = json.loads(generate_dataset_access_token(client, s3_dataset.datasetUri))
                dataset_session = boto3.Session(
                    aws_access_key_id=creds['AccessKey'],
                    aws_secret_access_key=creds['SessionKey'],
                    aws_session_token=creds['sessionToken'],
                )
                file_path = os.path.join(os.path.dirname(__file__), 'sample_data/folder1/txt_sample.txt')
                s3_client = S3Client(dataset_session, s3_dataset.region)
                s3_client.upload_file_to_prefix(
                    local_file_path=file_path, s3_path=f'{s3_dataset.S3BucketName}/sessionFolderA'
                )

        if s3_dataset.stack.status in ['CREATE_COMPLETE', 'UPDATE_COMPLETE']:
            return s3_dataset
        else:
            delete_s3_dataset(client, env['environmentUri'], s3_dataset.datasetUri)
            raise RuntimeError(f'failed to create {dataset_name=} {s3_dataset=}')


@pytest.fixture(scope='session')
def persistent_s3_dataset1(client1, group1, persistent_env1, testdata):
    return get_or_create_persistent_s3_dataset(
        'persistent_s3_dataset1', client1, group1, persistent_env1, withContent=True
    )


@pytest.fixture(scope='session')
def updated_persistent_s3_dataset1(client1, persistent_s3_dataset1):
    target_type = 'dataset'
    stack_uri = persistent_s3_dataset1.stack.stackUri
    env_uri = persistent_s3_dataset1.environment.environmentUri
    dataset_uri = persistent_s3_dataset1.datasetUri
    update_stack(client1, dataset_uri, target_type)
    time.sleep(120)
    check_stack_ready(client1, env_uri=env_uri, stack_uri=stack_uri, target_uri=dataset_uri, target_type=target_type)
    return get_dataset(client1, dataset_uri)


@pytest.fixture(scope='session')
def persistent_imported_sse_s3_dataset1(client1, group1, persistent_env1, persistent_env1_aws_client, testdata):
    bucket_name = f"dataalltesting{persistent_env1.environmentUri}perssses3{persistent_env1['AwsAccountId']}"
    bucket = None
    try:
        s3_client = S3Client(session=persistent_env1_aws_client, region=persistent_env1['region'])
        bucket = s3_client.bucket_exists(bucket_name)
        if not bucket:
            bucket, kms_alias, database, existing_lf_admins = create_aws_imported_resources(
                aws_client=persistent_env1_aws_client,
                env=persistent_env1,
                bucket_name=bucket_name,
            )
            if not bucket:
                raise Exception('Error creating import dataset AWS resources')
    except Exception as e:
        raise Exception(f'Error creating {bucket_name=} due to: {e}')
    return get_or_create_persistent_s3_dataset(
        'persistent_imported_sse_s3_dataset1',
        client1,
        group1,
        persistent_env1,
        autoApprovalEnabled=False,
        bucket=bucket_name,
    )


@pytest.fixture(scope='session')
def persistent_imported_kms_s3_dataset1(
    client1, group1, persistent_env1, persistent_env1_aws_client, persistent_env1_integration_role_arn, testdata
):
    resource_name = f"dataalltesting{persistent_env1.environmentUri}perskms{persistent_env1['AwsAccountId']}"
    existing_bucket = S3Client(session=persistent_env1_aws_client, region=persistent_env1['region']).bucket_exists(
        resource_name
    )
    existing_kms_alias = KMSClient(
        session=persistent_env1_aws_client,
        account_id=persistent_env1['AwsAccountId'],
        region=persistent_env1['region'],
    ).get_key_alias(resource_name)
    existing_database = GlueClient(session=persistent_env1_aws_client, region=persistent_env1['region']).get_database(
        resource_name
    )
    bucket, kms_alias, database, existing_lf_admins = create_aws_imported_resources(
        aws_client=persistent_env1_aws_client,
        integration_role_arn=persistent_env1_integration_role_arn,
        env=persistent_env1,
        bucket_name=resource_name if not existing_bucket else None,
        kms_alias_name=resource_name if not existing_kms_alias else None,
        glue_database_name=resource_name if not existing_database else None,
    )
    if (
        (not bucket and not existing_bucket)
        or (not kms_alias and not existing_kms_alias)
        or (not database and not existing_database)
    ):
        delete_aws_dataset_resources(
            aws_client=persistent_env1_aws_client,
            env=persistent_env1,
            bucket=bucket,
            kms_alias=kms_alias,
            database=database,
            existing_lf_admins=existing_lf_admins,
        )
        raise Exception('Error creating import dataset AWS resources for persistent_imported_kms_s3_dataset1')

    return get_or_create_persistent_s3_dataset(
        'persistent_imported_kms_s3_dataset1',
        client1,
        group1,
        persistent_env1,
        autoApprovalEnabled=False,
        bucket=resource_name,
        kms_alias=resource_name,
        glue_database=resource_name,
    )


@pytest.fixture(scope='session')
def persistent_s3_dataset1_folders(client1, persistent_s3_dataset1):
    yield create_folders(client1, persistent_s3_dataset1)

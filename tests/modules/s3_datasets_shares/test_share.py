import random
import typing
from datetime import datetime
from unittest.mock import MagicMock

import boto3
import pytest
from assertpy import assert_that

from dataall.base.utils.expiration_util import ExpirationUtils
from dataall.base.utils.naming_convention import NamingConventionPattern, NamingConventionService
from dataall.core.environment.db.environment_models import Environment, EnvironmentGroup, ConsumptionRole
from dataall.core.organizations.db.organization_models import Organization
from dataall.modules.shares_base.services.share_object_service import ShareObjectService
from dataall.modules.shares_base.services.shares_enums import ShareableType, PrincipalType, ShareObjectDataPermission
from dataall.modules.shares_base.services.shares_enums import (
    ShareObjectActions,
    ShareItemActions,
    ShareObjectStatus,
    ShareItemStatus,
    ShareItemHealthStatus,
)
from dataall.modules.shares_base.db.share_object_models import ShareObject, ShareObjectItem
from dataall.modules.shares_base.db.share_object_repositories import ShareObjectRepository
from dataall.modules.shares_base.db.share_state_machines_repositories import ShareStatusRepository
from dataall.modules.shares_base.db.share_object_state_machines import ShareItemSM, ShareObjectSM
from dataall.modules.s3_datasets.db.dataset_models import DatasetTable, S3Dataset


@pytest.fixture(scope='function')
def mock_glue_client(mocker):
    glue_client = MagicMock()
    mocker.patch('dataall.modules.s3_datasets_shares.aws.glue_client.GlueClient', return_value=glue_client)
    glue_client.get_glue_database_from_catalog.return_value = None


def random_table_name():
    def cpltz(l):
        return [item.capitalize() for item in l]

    prefixes = cpltz(['big', 'small', 'shiny', 'fat', 'light', 'fun', 'clean'])
    topics = cpltz(['sales', 'resources', 'receipts', 'orders', 'shipping'])
    formats = cpltz(['csv', 'parquet', 'avro', 'orc', 'txt', 'delta'])

    return f'{random.choice(prefixes)}{random.choice(topics)}{random.choice(formats)}'


@pytest.fixture(scope='module')
def org1(org: typing.Callable, user, group, tenant):
    # user, group and tenant are fixtures defined in conftest
    yield org('testorg', group, user)


@pytest.fixture(scope='module')
def env1(env: typing.Callable, org1: Organization, user, group) -> Environment:
    # user, group and tenant are fixtures defined in conftest
    yield env(
        org=org1,
        account='1' * 12,
        envname='source_environment',
        owner=user.username,
        group=group.name,
        role=f'source-{group.name}',
    )


@pytest.fixture(scope='module')
def env1group(environment_group: typing.Callable, env1, user, group) -> EnvironmentGroup:
    yield environment_group(
        environment=env1,
        group=group.name,
    )


@pytest.fixture(scope='module')
def dataset1(dataset_model: typing.Callable, org1: Organization, env1: Environment) -> S3Dataset:
    yield dataset_model(organization=org1, environment=env1, label='datasettoshare')


@pytest.fixture(scope='module')
def dataset_with_expiration(dataset_model: typing.Callable, org1: Organization, env1: Environment) -> S3Dataset:
    yield dataset_model(
        organization=org1,
        environment=env1,
        label='datasettoshare',
        enableExpiration=True,
        expirySetting='Monthly',
        expiryMinDuration=1,
        expiryMaxDuration=3,
    )


@pytest.fixture(scope='module')
def dataset_with_expiration_3(dataset_model: typing.Callable, org1: Organization, env1: Environment) -> S3Dataset:
    yield dataset_model(
        organization=org1,
        environment=env1,
        label='datasettoshare',
        enableExpiration=True,
        expirySetting='Monthly',
        expiryMinDuration=1,
        expiryMaxDuration=3,
    )


@pytest.fixture(scope='module')
def dataset_with_expiration_2(dataset_model: typing.Callable, org2: Organization, env2: Environment) -> S3Dataset:
    yield dataset_model(
        organization=org2,
        environment=env2,
        label='datasettoshare',
        enableExpiration=True,
        expirySetting='Monthly',
        expiryMinDuration=1,
        expiryMaxDuration=3,
    )


@pytest.fixture(scope='module')
def dataset_with_expiration_with_autoapproval(
    dataset_model: typing.Callable, org2: Organization, env2: Environment
) -> S3Dataset:
    yield dataset_model(
        organization=org2,
        environment=env2,
        label='datasettoshare',
        enableExpiration=True,
        expirySetting='Monthly',
        expiryMinDuration=1,
        expiryMaxDuration=3,
        autoApprovalEnabled=True,
    )


@pytest.fixture(scope='module')
def tables1(table: typing.Callable, dataset1: S3Dataset):
    for i in range(1, 100):
        table(dataset1, name=random_table_name(), username=dataset1.owner)


@pytest.fixture(scope='module', autouse=True)
def table1(table: typing.Callable, dataset1: S3Dataset) -> DatasetTable:
    yield table(dataset=dataset1, name='table1', username='alice')


@pytest.fixture(scope='module', autouse=True)
def table1_1(table: typing.Callable, dataset1: S3Dataset) -> DatasetTable:
    yield table(dataset=dataset1, name='table5', username='alice')


@pytest.fixture(scope='module', autouse=True)
def table1_expiration_dataset(table: typing.Callable, dataset_with_expiration_2: S3Dataset) -> DatasetTable:
    yield table(dataset=dataset_with_expiration_2, name='table5', username='alice')


@pytest.fixture(scope='module', autouse=True)
def table1_expiration_dataset_with_autoapproval(
    table: typing.Callable, dataset_with_expiration_with_autoapproval: S3Dataset
) -> DatasetTable:
    yield table(dataset=dataset_with_expiration_with_autoapproval, name='table5', username='alice')


@pytest.fixture(scope='module')
def org2(org: typing.Callable, group2, user2) -> Organization:
    yield org('org2', group2, user2)


@pytest.fixture(scope='module')
def env2(env: typing.Callable, org2: Organization, user2, group2) -> Environment:
    # user, group and tenant are fixtures defined in conftest
    yield env(
        org=org2,
        account='2' * 12,
        envname='target_environment',
        owner=user2.username,
        group=group2.name,
        role=f'source-{group2.name}',
    )


@pytest.fixture(scope='module')
def dataset2(dataset_model: typing.Callable, org2: Organization, env2: Environment) -> S3Dataset:
    yield dataset_model(organization=org2, environment=env2, label='datasettoshare2')


@pytest.fixture(scope='module')
def tables2(table, dataset2):
    for i in range(1, 100):
        table(dataset2, name=random_table_name(), username=dataset2.owner)


@pytest.fixture(scope='module', autouse=True)
def table2(table: typing.Callable, dataset2: S3Dataset) -> DatasetTable:
    yield table(dataset=dataset2, name='table2', username='bob')


@pytest.fixture(scope='module')
def env2group(environment_group: typing.Callable, env2, user2, group2) -> EnvironmentGroup:
    yield environment_group(
        environment=env2,
        group=group2.name,
    )


@pytest.fixture(scope='module')
def dataset3(dataset_model: typing.Callable, org2: Organization, env2: Environment) -> S3Dataset:
    yield dataset_model(organization=org2, environment=env2, label='datasettoshare3', autoApprovalEnabled=True)


@pytest.fixture(scope='module')
def tables3(table, dataset3):
    for i in range(1, 100):
        table(dataset3, name=random_table_name(), username=dataset3.owner)


@pytest.fixture(scope='module', autouse=True)
def table3(table: typing.Callable, dataset3: S3Dataset) -> DatasetTable:
    yield table(dataset=dataset3, name='table3', username='bob')


@pytest.fixture(scope='module')
def table_data_filter_fixture(db, table_fixture, table_column_data_filter, group, user):
    yield table_column_data_filter(table=table_fixture, name='datafilter1', filterType='COLUMN')


@pytest.fixture(scope='function')
def share1_draft(
    db,
    client,
    user2,
    group2,
    share: typing.Callable,
    dataset1: S3Dataset,
    env2: Environment,
    env2group: EnvironmentGroup,
) -> ShareObject:
    share1 = share(
        dataset=dataset1,
        environment=env2,
        env_group=env2group,
        owner=user2.username,
        status=ShareObjectStatus.Draft.value,
    )

    yield share1

    # Cleanup share
    # First try to direct delete. This fixture should not have any shared items, but just in case
    delete_share_object_response = delete_share_object(
        client=client, user=user2, group=group2, shareUri=share1.shareUri
    )

    if delete_share_object_response.data.deleteShareObject == True:
        return

    # Given share item in shared states
    get_share_object_response = get_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share1.shareUri,
        filter={'isShared': True},
    )
    revoked_items_uris = [
        node.shareItemUri for node in get_share_object_response.data.getShareObject.get('items').nodes
    ]

    # Then delete via revoke items if still items present
    revoke_items_share_object(
        client=client, user=user2, group=group2, shareUri=share1.shareUri, revoked_items_uris=revoked_items_uris
    )

    _successfull_processing_for_share_object(db, share1)

    delete_share_object(client=client, user=user2, group=group2, shareUri=share1.shareUri)


@pytest.fixture(scope='function')
def share_autoapprove_draft(
    db,
    client,
    user2,
    group2,
    share: typing.Callable,
    dataset3: S3Dataset,
    env2: Environment,
    env2group: EnvironmentGroup,
) -> ShareObject:
    share1 = share(
        dataset=dataset3,
        environment=env2,
        env_group=env2group,
        owner=user2.username,
        status=ShareObjectStatus.Draft.value,
    )

    yield share1


@pytest.fixture(scope='function')
def share1_item_pa(share_item: typing.Callable, share1_draft: ShareObject, table1: DatasetTable) -> ShareObjectItem:
    # Cleaned up with share1_draft
    yield share_item(share=share1_draft, table=table1, status=ShareItemStatus.PendingApproval.value)


@pytest.fixture(scope='function')
def share_autoapprove_item_pa(
    share_item: typing.Callable, share_autoapprove_draft: ShareObject, table3: DatasetTable
) -> ShareObjectItem:
    # Cleaned up with share1_draft
    yield share_item(share=share_autoapprove_draft, table=table3, status=ShareItemStatus.PendingApproval.value)


@pytest.fixture(scope='function')
def share2_submitted(
    db,
    client,
    user2,
    group2,
    share: typing.Callable,
    dataset1: S3Dataset,
    env2: Environment,
    env2group: EnvironmentGroup,
) -> ShareObject:
    share2 = share(
        dataset=dataset1,
        environment=env2,
        env_group=env2group,
        owner=user2.username,
        status=ShareObjectStatus.Submitted.value,
    )
    yield share2
    # Cleanup share
    # First try to direct delete
    delete_share_object_response = delete_share_object(
        client=client, user=user2, group=group2, shareUri=share2.shareUri
    )

    if delete_share_object_response.data.deleteShareObject == True:
        return

    # Given share item in shared states
    get_share_object_response = get_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share2.shareUri,
        filter={'isShared': True},
    )
    revoked_items_uris = [
        node.shareItemUri for node in get_share_object_response.data.getShareObject.get('items').nodes
    ]

    # Then delete via revoke items if still items present
    revoke_items_share_object(
        client=client, user=user2, group=group2, shareUri=share2.shareUri, revoked_items_uris=revoked_items_uris
    )
    _successfull_processing_for_share_object(db, share2)

    delete_share_object(client=client, user=user2, group=group2, shareUri=share2.shareUri)


@pytest.fixture(scope='function')
def share2_item_pa(share_item: typing.Callable, share2_submitted: ShareObject, table1: DatasetTable) -> ShareObjectItem:
    # Cleaned up with share2
    yield share_item(share=share2_submitted, table=table1, status=ShareItemStatus.PendingApproval.value)


@pytest.fixture(scope='function')
def share3_processed(
    db,
    client,
    user2,
    group2,
    share: typing.Callable,
    dataset1: S3Dataset,
    env2: Environment,
    env2group: EnvironmentGroup,
) -> ShareObject:
    share3 = share(
        dataset=dataset1,
        environment=env2,
        env_group=env2group,
        owner=user2.username,
        status=ShareObjectStatus.Processed.value,
    )
    yield share3
    # Cleanup share
    # First try to direct delete
    delete_share_object_response = delete_share_object(
        client=client, user=user2, group=group2, shareUri=share3.shareUri
    )

    if delete_share_object_response.data.deleteShareObject == True:
        return

    # Revert healthStatus back to healthy
    with db.scoped_session() as session:
        ShareStatusRepository.update_share_item_health_status_batch(
            session=session,
            share_uri=share3.shareUri,
            old_status=ShareItemHealthStatus.PendingReApply.value,
            new_status=ShareItemHealthStatus.Healthy.value,
        )

    # Given share item in shared states
    get_share_object_response = get_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share3.shareUri,
        filter={'isShared': True},
    )
    revoked_items_uris = [
        node.shareItemUri for node in get_share_object_response.data.getShareObject.get('items').nodes
    ]

    # Then delete via revoke items if still items present
    revoke_items_share_object(
        client=client, user=user2, group=group2, shareUri=share3.shareUri, revoked_items_uris=revoked_items_uris
    )
    _successfull_processing_for_share_object(db, share3)

    delete_share_object(client=client, user=user2, group=group2, shareUri=share3.shareUri)


@pytest.fixture(scope='function')
def share3_item_shared(
    share_item: typing.Callable, share3_processed: ShareObject, table1: DatasetTable
) -> ShareObjectItem:
    # Cleaned up with share3_happy_path
    yield share_item(share=share3_processed, table=table1, status=ShareItemStatus.Share_Succeeded.value)


@pytest.fixture(scope='function')
def share3_with_expiration_processed(
    db,
    client,
    user2,
    group2,
    share: typing.Callable,
    dataset_with_expiration_2: S3Dataset,
    env2: Environment,
    env2group: EnvironmentGroup,
    shareExpirationPeriod=1,
) -> ShareObject:
    share3_processed_with_expiration = share(
        dataset=dataset_with_expiration_2,
        environment=env2,
        env_group=env2group,
        owner=user2.username,
        status=ShareObjectStatus.Processed.value,
        shareExpirationPeriod=shareExpirationPeriod,
    )
    yield share3_processed_with_expiration
    # Cleanup share
    # First try to direct delete
    delete_share_object_response = delete_share_object(
        client=client, user=user2, group=group2, shareUri=share3_processed_with_expiration.shareUri
    )

    if delete_share_object_response.data.deleteShareObject == True:
        return

    # Revert healthStatus back to healthy
    with db.scoped_session() as session:
        ShareStatusRepository.update_share_item_health_status_batch(
            session=session,
            share_uri=share3_processed_with_expiration.shareUri,
            old_status=ShareItemHealthStatus.PendingReApply.value,
            new_status=ShareItemHealthStatus.Healthy.value,
        )

    # Given share item in shared states
    get_share_object_response = get_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share3_processed_with_expiration.shareUri,
        filter={'isShared': True},
    )
    revoked_items_uris = [
        node.shareItemUri for node in get_share_object_response.data.getShareObject.get('items').nodes
    ]

    # Then delete via revoke items if still items present
    revoke_items_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share3_processed_with_expiration.shareUri,
        revoked_items_uris=revoked_items_uris,
    )
    _successfull_processing_for_share_object(db, share3_processed_with_expiration)

    delete_share_object(client=client, user=user2, group=group2, shareUri=share3_processed_with_expiration.shareUri)


@pytest.fixture(scope='function')
def share3_item_expiration_share(
    share_item: typing.Callable, share3_with_expiration_processed: ShareObject, table1_expiration_dataset: DatasetTable
) -> ShareObjectItem:
    # Cleaned up with share3
    yield share_item(
        share=share3_with_expiration_processed,
        table=table1_expiration_dataset,
        status=ShareItemStatus.Share_Succeeded.value,
    )


@pytest.fixture(scope='function')
def share3_with_expiration_processed_with_autoapproval(
    db,
    client,
    user2,
    group2,
    share: typing.Callable,
    dataset_with_expiration_with_autoapproval: S3Dataset,
    env2: Environment,
    env2group: EnvironmentGroup,
    shareExpirationPeriod=1,
) -> ShareObject:
    share3_processed_with_expiration_with_autoapproval = share(
        dataset=dataset_with_expiration_with_autoapproval,
        environment=env2,
        env_group=env2group,
        owner=user2.username,
        status=ShareObjectStatus.Processed.value,
        shareExpirationPeriod=shareExpirationPeriod,
    )
    yield share3_processed_with_expiration_with_autoapproval
    # Cleanup share
    # First try to direct delete
    delete_share_object_response = delete_share_object(
        client=client, user=user2, group=group2, shareUri=share3_processed_with_expiration_with_autoapproval.shareUri
    )

    if delete_share_object_response.data.deleteShareObject == True:
        return

    # Revert healthStatus back to healthy
    with db.scoped_session() as session:
        ShareStatusRepository.update_share_item_health_status_batch(
            session=session,
            share_uri=share3_processed_with_expiration_with_autoapproval.shareUri,
            old_status=ShareItemHealthStatus.PendingReApply.value,
            new_status=ShareItemHealthStatus.Healthy.value,
        )

    # Given share item in shared states
    get_share_object_response = get_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share3_processed_with_expiration_with_autoapproval.shareUri,
        filter={'isShared': True},
    )
    revoked_items_uris = [
        node.shareItemUri for node in get_share_object_response.data.getShareObject.get('items').nodes
    ]

    # Then delete via revoke items if still items present
    revoke_items_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share3_processed_with_expiration_with_autoapproval.shareUri,
        revoked_items_uris=revoked_items_uris,
    )
    _successfull_processing_for_share_object(db, share3_processed_with_expiration_with_autoapproval)

    delete_share_object(
        client=client, user=user2, group=group2, shareUri=share3_processed_with_expiration_with_autoapproval.shareUri
    )


@pytest.fixture(scope='function')
def share3_item_expiration_share_with_autoapproval(
    share_item: typing.Callable,
    share3_with_expiration_processed_with_autoapproval: ShareObject,
    table1_expiration_dataset_with_autoapproval: DatasetTable,
) -> ShareObjectItem:
    # Cleaned up with share3
    yield share_item(
        share=share3_with_expiration_processed_with_autoapproval,
        table=table1_expiration_dataset_with_autoapproval,
        status=ShareItemStatus.Share_Succeeded.value,
    )


@pytest.fixture(scope='function')
def share4_draft(
    user2,
    share: typing.Callable,
    dataset1: S3Dataset,
    env2: Environment,
    env2group: EnvironmentGroup,
) -> ShareObject:
    yield share(
        dataset=dataset1,
        environment=env2,
        env_group=env2group,
        owner=user2.username,
        status=ShareObjectStatus.Draft.value,
    )


@pytest.fixture(scope='function')
def share3_item_shared_unhealthy(
    share_item: typing.Callable, share3_processed: ShareObject, table1_1: DatasetTable
) -> ShareObjectItem:
    # Cleaned up with share3_happy_path
    yield share_item(
        share=share3_processed,
        table=table1_1,
        status=ShareItemStatus.Share_Succeeded.value,
        healthStatus=ShareItemHealthStatus.Unhealthy.value,
    )


def test_init(tables1, tables2):
    assert True


# Queries & mutations
def create_share_object(
    mocker,
    client,
    username,
    group,
    groupUri,
    environmentUri,
    datasetUri,
    itemUri=None,
    attachMissingPolicies=True,
    principalId=None,
    principalType=PrincipalType.Group.value,
    permissions=[ShareObjectDataPermission.Read.value],
    shareExpirationPeriod=None,
    nonExpiring=False,
):
    q = """
      mutation CreateShareObject(
        $datasetUri: String!
        $itemType: String
        $itemUri: String
        $input: NewShareObjectInput!
      ) {
        createShareObject(
          datasetUri: $datasetUri
          itemType: $itemType
          itemUri: $itemUri
          input: $input
        ) {
          shareUri
          created
          status
          userRoleForShareObject
          requestPurpose
          rejectPurpose
          expiryDate
          requestedExpiryDate
          nonExpirable
          lastExtensionDate
          extensionReason
          submittedForExtension
          dataset {
            datasetUri
            datasetName
          }
          
        }
      }
    """
    mocker.patch(
        'dataall.modules.s3_datasets_shares.services.s3_share_managed_policy_service.S3SharePolicyService.create_managed_policy_from_inline_and_delete_inline',
        return_value=True,
    )

    response = client.query(
        q,
        username=username,
        groups=[group.name],
        datasetUri=datasetUri,
        itemType=ShareableType.Table.value if itemUri else None,
        itemUri=itemUri,
        input={
            'environmentUri': environmentUri,
            'groupUri': groupUri,
            'principalId': principalId if principalId else groupUri,
            'principalType': principalType,
            'requestPurpose': 'testShare',
            'attachMissingPolicies': attachMissingPolicies,
            'permissions': permissions,
            'shareExpirationPeriod': shareExpirationPeriod,
            'nonExpirable': nonExpiring,
        },
    )

    # Print response
    print('Create share request response: ', response)
    return response


def get_share_object(client, user, group, shareUri, filter):
    q = """
    query getShareObject($shareUri: String!, $filter: ShareableObjectFilter) {
      getShareObject(shareUri: $shareUri) {
        shareUri
        created
        owner
        status
        requestPurpose
        rejectPurpose
        userRoleForShareObject
        extensionReason
        expiryDate
        requestedExpiryDate
        nonExpirable
        shareExpirationPeriod
        principal {
          principalName
          principalType
          principalId
          principalRoleName
          SamlGroupName
          environmentName
        }
        items(filter: $filter) {
          count
          page
          pages
          hasNext
          hasPrevious
          nodes {
            itemUri
            shareItemUri
            itemType
            itemName
            status
            action
            healthStatus
            healthMessage
            lastVerificationTime
            attachedDataFilterUri
          }
        }
        dataset {
          datasetUri
          datasetName
          SamlAdminGroupName
          environmentName
          exists
        }
      }
    }
    """

    response = client.query(
        q,
        username=user.username,
        groups=[group.name],
        shareUri=shareUri,
        filter=filter,
    )
    # Print response
    print('Get share request response: ', response)
    return response


def get_share_item_data_filters(client, user, group, attachedDataFilterUri):
    q = """
    query getShareItemDataFilters($attachedDataFilterUri: String!) {
      getShareItemDataFilters(attachedDataFilterUri: $attachedDataFilterUri) {
        attachedDataFilterUri
        label
        dataFilterUris
        dataFilterNames
        itemUri
      }
    }
    """

    response = client.query(
        q,
        username=user.username,
        groups=[group.name],
        attachedDataFilterUri=attachedDataFilterUri,
    )
    # Print response
    print('get_share_item_data_filters response: ', response)
    return response


def update_share_request_purpose(client, user, group, shareUri, requestPurpose):
    q = """
    mutation updateShareRequestReason($shareUri: String!,$requestPurpose: String!) {
      updateShareRequestReason(shareUri: $shareUri, requestPurpose: $requestPurpose)
    }
    """

    response = client.query(
        q,
        username=user.username,
        groups=[group.name],
        shareUri=shareUri,
        requestPurpose=requestPurpose,
    )
    # Print response
    print('Update share request purpose response: ', response)
    return response


def update_share_reject_purpose(client, user, group, shareUri, rejectPurpose):
    q = """
        mutation updateShareRejectReason($shareUri: String!, $rejectPurpose: String!) {
          updateShareRejectReason(shareUri: $shareUri, rejectPurpose: $rejectPurpose)
        }
    """

    response = client.query(
        q,
        username=user.username,
        groups=[group.name],
        shareUri=shareUri,
        rejectPurpose=rejectPurpose,
    )
    # Print response
    print('Update share reject purpose response: ', response)
    return response


def get_share_requests_to_me(client, user, group, filter=None):
    q = """
        query getShareRequestsToMe($filter: ShareObjectFilter){
            getShareRequestsToMe(filter: $filter){
                count
                nodes{
                    shareUri
                }
            }
        }
    """
    response = client.query(q, username=user.username, groups=[group.name], filter=filter)
    # Print response
    print('Get share requests to me response: ', response)
    return response


def get_share_requests_from_me(client, user, group):
    q = """
        query getShareRequestsFromMe($filter: ShareObjectFilter){
            getShareRequestsFromMe(filter: $filter){
                count
                nodes{
                    shareUri
                 }
            }
        }
    """
    response = client.query(q, username=user.username, groups=[group.name])
    # Print response
    print('Get share requests from me response: ', response)
    return response


def add_share_item(client, user, group, shareUri, itemUri, itemType):
    q = """
        mutation AddSharedItem($shareUri:String!,$input:AddSharedItemInput){
            addSharedItem(shareUri:$shareUri,input:$input){
                shareUri
                shareItemUri
                itemUri
                status
                action
            }
        }
        """

    response = client.query(
        q,
        username=user.username,
        groups=[group.name],
        shareUri=shareUri,
        input={
            'itemUri': itemUri,
            'itemType': itemType,
        },
    )

    print('Response from addSharedItem: ', response)
    return response


def update_share_item_filter(client, user, group, input):
    q = """
      mutation updateShareItemFilters($input: ModifyFiltersTableShareItemInput!) {
        updateShareItemFilters(input: $input)
      }
        """

    response = client.query(q, username=user.username, groups=[group.name], input=input)

    print('Response from updateShareItemFilters: ', response)
    return response


def remove_share_item_filter(client, user, group, attachedDataFilterUri):
    q = """
      mutation removeShareItemFilter($attachedDataFilterUri: String!) {
        removeShareItemFilter(attachedDataFilterUri: $attachedDataFilterUri)
      }
        """

    response = client.query(
        q,
        username=user.username,
        groups=[group.name],
        attachedDataFilterUri=attachedDataFilterUri,
    )

    print('Response from removeShareItemFilter: ', response)
    return response


def remove_share_item(client, user, group, shareItemUri):
    q = """
    mutation RemoveSharedItem($shareItemUri: String!) {
      removeSharedItem(shareItemUri: $shareItemUri)
    }
    """

    response = client.query(q, username=user.username, groups=[group.name], shareItemUri=shareItemUri)

    print('Response from removeSharedItem: ', response)
    return response


def submit_share_object(client, user, group, shareUri):
    q = """
        mutation submitShareObject($shareUri:String!){
            submitShareObject(shareUri:$shareUri){
                status
                owner
                userRoleForShareObject
                items {
                    count
                    page
                    pages
                    hasNext
                    hasPrevious
                    nodes {
                        itemUri
                        shareItemUri
                        itemType
                        itemName
                        status
                        action
                    }
                }
            }
        }
        """

    response = client.query(
        q,
        username=user.username,
        groups=[group.name],
        shareUri=shareUri,
    )

    print('Response from submitShareObject: ', response)
    return response


def approve_share_object(client, user, group, shareUri):
    q = """
            mutation approveShareObject($shareUri:String!){
                approveShareObject(shareUri:$shareUri){
                    status
                    owner
                    userRoleForShareObject
                }
            }
            """

    response = client.query(
        q,
        username=user.username,
        groups=[group.name],
        shareUri=shareUri,
    )

    print('Response from approveShareObject: ', response)
    return response


def reject_share_object(client, user, group, shareUri):
    q = """
    mutation RejectShareObject($shareUri: String!, $rejectPurpose: String!) {
      rejectShareObject(shareUri: $shareUri, rejectPurpose: $rejectPurpose) {
        shareUri
        status
        rejectPurpose
      }
    }
    """

    response = client.query(
        q, username=user.username, groups=[group.name], shareUri=shareUri, rejectPurpose='testRejectShare'
    )

    print('Response from rejectShareObject: ', response)
    return response


def revoke_items_share_object(client, user, group, shareUri, revoked_items_uris):
    q = """
        mutation revokeItemsShareObject($input: ShareItemSelectorInput) {
            revokeItemsShareObject(input: $input) {
                shareUri
                status
            }
        }
        """

    response = client.query(
        q,
        username=user.username,
        groups=[group.name],
        input={'shareUri': shareUri, 'itemUris': revoked_items_uris},
    )
    print('Response from revokeItemsShareObject: ', response)
    return response


def verify_items_share_object(client, user, group, shareUri, verify_items_uris):
    q = """
        mutation verifyItemsShareObject($input: ShareItemSelectorInput) {
          verifyItemsShareObject(input: $input) {
            shareUri
            status
          }
        }
        """

    response = client.query(
        q,
        username=user.username,
        groups=[group.name],
        input={'shareUri': shareUri, 'itemUris': verify_items_uris},
    )
    print('Response from verifyItemsShareObject: ', response)
    return response


def verify_dataset_share_objects(client, user, group, dataset_uri, share_uris):
    q = """
        mutation verifyDatasetShareObjects($input: ShareObjectSelectorInput) {
          verifyDatasetShareObjects(input: $input)
        }
        """

    response = client.query(
        q,
        username=user.username,
        groups=[group.name],
        input={'datasetUri': dataset_uri, 'shareUris': share_uris},
    )
    print('Response from verifyDatasetShareObjects: ', response)
    return response


def reapply_items_share_object(client, user, group, shareUri, reapply_items_uris):
    q = """
        mutation reApplyItemsShareObject($input: ShareItemSelectorInput) {
          reApplyItemsShareObject(input: $input) {
            shareUri
            status
          }
        }
        """

    response = client.query(
        q,
        username=user.username,
        groups=[group.name],
        input={'shareUri': shareUri, 'itemUris': reapply_items_uris},
    )
    print('Response from reApplyItemsShareObject: ', response)
    return response


def delete_share_object(client, user, group, shareUri):
    q = """
        mutation DeleteShareObject($shareUri: String!){
          deleteShareObject(shareUri:$shareUri)
        }
    """
    response = client.query(
        q,
        username=user,
        groups=[group.name],
        shareUri=shareUri,
    )
    print('Response from deleteShareObject: ', response)
    return response


def list_datasets_published_in_environment(client, user, group, environmentUri):
    q = """
        query searchEnvironmentDataItems(
            $environmentUri:String!, $filter:EnvironmentDataItemFilter
        ){
            searchEnvironmentDataItems(environmentUri:$environmentUri, filter:$filter){
                count
                nodes{
                    shareUri
                    environmentName
                    environmentUri
                    organizationName
                    organizationUri
                    datasetUri
                    datasetName
                    itemType
                    itemName
                    created
                    principalId
                }
            }
        }
    """
    response = client.query(
        q,
        username=user.username,
        groups=[group.name],
        environmentUri=environmentUri,
        filter={},
    )
    print('searchEnvironmentDataItems response: ', response)
    return response


def submit_share_extension(client, user, group, shareUri, expiration, nonExpirable=False):
    q = """
         mutation submitShareExtension(
          $shareUri: String!
          $expiration: Int
          $extensionReason: String
          $nonExpirable: Boolean
        ) {
          submitShareExtension(
            shareUri: $shareUri
            expiration: $expiration
            extensionReason: $extensionReason
            nonExpirable: $nonExpirable
          ) {
            shareUri
            status
          }
        }
        """

    response = client.query(
        q,
        username=user.username,
        groups=[group.name],
        shareUri=shareUri,
        expiration=expiration,
        extensionReason='',
        nonExpirable=nonExpirable,
    )
    return response


def update_share_extension_period(client, user, group, shareUri, expiration, nonExpirable=False):
    q = """
    mutation updateShareExpirationPeriod(
      $shareUri: String!
      $expiration: Int
      $nonExpirable: Boolean
    ) {
      updateShareExpirationPeriod(
        shareUri: $shareUri
        expiration: $expiration
        nonExpirable: $nonExpirable
      )
    }
           """

    response = client.query(
        q,
        username=user.username,
        groups=[group.name],
        shareUri=shareUri,
        expiration=expiration,
        nonExpirable=nonExpirable,
    )
    return response


def update_share_extension_reason(client, user, group, shareUri, expirationPurpose):
    q = """
             mutation updateShareExtensionReason(
              $shareUri: String!
              $extensionPurpose: String!
            ) {
              updateShareExtensionReason(
                shareUri: $shareUri
                extensionPurpose: $extensionPurpose
              )
            }
           """

    response = client.query(
        q,
        username=user.username,
        groups=[group.name],
        shareUri=shareUri,
        extensionPurpose=expirationPurpose,
    )
    return response


def cancel_share_extension(client, user, group, shareUri):
    q = """
    mutation cancelShareExtension($shareUri: String!) {
      cancelShareExtension(shareUri: $shareUri)
    }
           """

    response = client.query(q, username=user.username, groups=[group.name], shareUri=shareUri)
    return response


def approve_share_extension(client, user, group, shareUri):
    q = """
       mutation approveShareExtension($shareUri: String!) {
          approveShareExtension(shareUri: $shareUri) {
            shareUri
            status
          }
       }
    """

    response = client.query(q, username=user.username, groups=[group.name], shareUri=shareUri)
    return response


# Tests
def test_create_share_object_unauthorized(mocker, client, group3, dataset1, env2, env2group):
    # Given
    # Existing dataset, target environment and group
    # When a user that does not belong to environment and group creates request
    create_share_object_response = create_share_object(
        mocker=mocker,
        client=client,
        username='anonymous',
        group=group3,
        groupUri=env2group.groupUri,
        environmentUri=env2.environmentUri,
        datasetUri=dataset1.datasetUri,
    )
    # Then, user gets Unauthorized error
    assert 'Unauthorized' in create_share_object_response.errors[0].message


def test_create_share_object_as_requester(mocker, client, user2, group2, env2group, env2, dataset1):
    # Given
    # Existing dataset, target environment and group
    # SharePolicy exists and is attached
    mocker.patch(
        'dataall.base.aws.iam.IAM.get_role_arn_by_name',
        return_value='role_arn',
    )

    old_policy_exists = False
    mocker.patch(
        'dataall.modules.s3_datasets_shares.services.s3_share_managed_policy_service.S3SharePolicyService.check_if_policy_exists',
        return_value=old_policy_exists,
    )
    mocker.patch(
        'dataall.modules.s3_datasets_shares.services.s3_share_managed_policy_service.S3SharePolicyService.check_if_policy_attached',
        return_value=True,
    )
    mocker.patch('dataall.base.aws.iam.IAM.list_policy_names_by_policy_pattern', return_value=['policy-0'])

    create_share_object_response = create_share_object(
        mocker=mocker,
        client=client,
        username=user2.username,
        group=group2,
        groupUri=env2group.groupUri,
        environmentUri=env2.environmentUri,
        datasetUri=dataset1.datasetUri,
    )
    # Then share object created with status Draft and user is 'Requester'
    assert create_share_object_response.data.createShareObject.shareUri
    assert create_share_object_response.data.createShareObject.status == ShareObjectStatus.Draft.value
    assert create_share_object_response.data.createShareObject.userRoleForShareObject == 'Requesters'
    assert create_share_object_response.data.createShareObject.requestPurpose == 'testShare'


def test_create_share_object_as_approver_and_requester(mocker, client, user, group2, env2group, env2, dataset1):
    # Given
    # Existing dataset, target environment and group
    # SharePolicy exists and is attached
    # When a user that belongs to environment and group creates request
    mocker.patch(
        'dataall.base.aws.iam.IAM.get_role_arn_by_name',
        return_value='role_arn',
    )
    old_policy_exists = False
    mocker.patch(
        'dataall.modules.s3_datasets_shares.services.s3_share_managed_policy_service.S3SharePolicyService.check_if_policy_exists',
        return_value=old_policy_exists,
    )
    mocker.patch(
        'dataall.modules.s3_datasets_shares.services.s3_share_managed_policy_service.S3SharePolicyService.check_if_policy_attached',
        return_value=True,
    )

    mocker.patch('dataall.base.aws.iam.IAM.list_policy_names_by_policy_pattern', return_value=['policy-0'])

    create_share_object_response = create_share_object(
        mocker=mocker,
        client=client,
        username=user.username,
        group=group2,
        groupUri=env2group.groupUri,
        environmentUri=env2.environmentUri,
        datasetUri=dataset1.datasetUri,
    )
    # Then share object created with status Draft and user is 'Requester'
    assert create_share_object_response.data.createShareObject.shareUri
    assert create_share_object_response.data.createShareObject.status == ShareObjectStatus.Draft.value
    assert create_share_object_response.data.createShareObject.userRoleForShareObject == 'ApproversAndRequesters'
    assert create_share_object_response.data.createShareObject.requestPurpose == 'testShare'


def test_create_share_object_invalid_account(mocker, client, user, group2, env2group, env2, dataset1):
    # Given
    # Existing dataset, target environment and group
    # SharePolicy exists and is attached
    # When a user that belongs to environment and group creates request
    mocker.patch(
        'dataall.base.aws.iam.IAM.get_role_arn_by_name',
        return_value='role_arn',
    )
    old_policy_exists = False
    mocker.patch(
        'dataall.modules.s3_datasets_shares.services.s3_share_managed_policy_service.S3SharePolicyService.check_if_policy_exists',
        return_value=old_policy_exists,
    )
    mocker.patch(
        'dataall.modules.s3_datasets_shares.services.s3_share_managed_policy_service.S3SharePolicyService.check_if_policy_attached',
        return_value=True,
    )

    mocker.patch('dataall.base.aws.iam.IAM.list_policy_names_by_policy_pattern', return_value=['policy-0'])

    create_share_object_response = create_share_object(
        mocker=mocker,
        client=client,
        username=user.username,
        group=group2,
        groupUri=env2group.groupUri,
        environmentUri=env2.environmentUri,
        datasetUri=dataset1.datasetUri,
        permissions=[ShareObjectDataPermission.Write.value],
    )
    assert_that(create_share_object_response.errors[0].message).contains(
        'InvalidInput', env2.AwsAccountId, dataset1.AwsAccountId
    )


def test_create_share_object_with_item_authorized(
    mocker, client, user2, group2, env2group, env2, dataset1, table1, mock_glue_client
):
    # Given
    # Existing dataset, table, target environment and group
    # SharePolicy exists and is attached
    # When a user that belongs to environment and group creates request with table in the request
    mocker.patch(
        'dataall.base.aws.iam.IAM.get_role_arn_by_name',
        return_value='role_arn',
    )
    mocker.patch(
        'dataall.modules.s3_datasets_shares.services.s3_share_managed_policy_service.S3SharePolicyService.check_if_policy_exists',
        return_value=False,
    )
    mocker.patch(
        'dataall.modules.s3_datasets_shares.services.s3_share_managed_policy_service.S3SharePolicyService.check_if_policy_attached',
        return_value=True,
    )
    mocker.patch(
        'dataall.modules.s3_datasets_shares.services.s3_share_managed_policy_service.S3SharePolicyService.check_if_policy_attached',
        return_value=True,
    )
    mocker.patch('dataall.base.aws.iam.IAM.list_policy_names_by_policy_pattern', return_value=['policy-0'])

    create_share_object_response = create_share_object(
        mocker=mocker,
        client=client,
        username=user2.username,
        group=group2,
        groupUri=env2group.groupUri,
        environmentUri=env2.environmentUri,
        datasetUri=dataset1.datasetUri,
        itemUri=table1.tableUri,
    )

    # Then share object created with status Draft and user is 'Requester'
    assert create_share_object_response.data.createShareObject.shareUri
    assert create_share_object_response.data.createShareObject.status == ShareObjectStatus.Draft.value
    assert create_share_object_response.data.createShareObject.userRoleForShareObject == 'Requesters'
    assert create_share_object_response.data.createShareObject.requestPurpose == 'testShare'

    # And item has been added to the share request
    get_share_object_response = get_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=create_share_object_response.data.createShareObject.shareUri,
        filter={'isShared': True},
    )

    assert get_share_object_response.data.getShareObject.get('items').nodes[0].itemUri == table1.tableUri
    assert get_share_object_response.data.getShareObject.get('items').nodes[0].itemType == ShareableType.Table.name


def test_create_share_object_share_policy_not_attached_attachMissingPolicies_enabled(
    mocker, client, user2, group2, env2group, env2, dataset1
):
    # Given
    # Existing dataset, target environment and group
    # SharePolicy exists and is NOT attached, attachMissingPolicies=True
    # When a correct user creates request, data.all attaches the policy and the share creates successfully
    mocker.patch(
        'dataall.base.aws.iam.IAM.get_role_arn_by_name',
        return_value='role_arn',
    )
    mocker.patch(
        'dataall.modules.s3_datasets_shares.services.s3_share_managed_policy_service.S3SharePolicyService.check_if_policy_exists',
        return_value=False,
    )
    mocker.patch(
        'dataall.modules.s3_datasets_shares.services.s3_share_managed_policy_service.S3SharePolicyService.get_policies_unattached_to_role',
        return_value='policy-0',
    )
    attach_mocker = mocker.patch(
        'dataall.modules.s3_datasets_shares.services.s3_share_managed_policy_service.S3SharePolicyService.attach_policies',
        return_value=True,
    )
    mocker.patch('dataall.base.aws.iam.IAM.list_policy_names_by_policy_pattern', return_value=['policy-0'])

    create_share_object_response = create_share_object(
        mocker=mocker,
        client=client,
        username=user2.username,
        group=group2,
        groupUri=env2group.groupUri,
        environmentUri=env2.environmentUri,
        datasetUri=dataset1.datasetUri,
        attachMissingPolicies=True,
    )
    # Then share object created with status Draft and user is 'Requester'
    attach_mocker.assert_called_once()
    assert create_share_object_response.data.createShareObject.shareUri
    assert create_share_object_response.data.createShareObject.status == ShareObjectStatus.Draft.value
    assert create_share_object_response.data.createShareObject.userRoleForShareObject == 'Requesters'
    assert create_share_object_response.data.createShareObject.requestPurpose == 'testShare'


def test_create_share_object_share_policy_not_attached_attachMissingPolicies_disabled_dataallManaged(
    mocker, client, user2, group2, env2group, env2, dataset1
):
    # Given
    # Existing dataset, target environment and group
    # SharePolicy exists and is NOT attached, attachMissingPolicies=True but principal=Group so managed=Trye
    # When a correct user creates request, data.all attaches the policy and the share creates successfully
    mocker.patch(
        'dataall.base.aws.iam.IAM.get_role_arn_by_name',
        return_value='role_arn',
    )
    mocker.patch(
        'dataall.modules.s3_datasets_shares.services.s3_share_managed_policy_service.S3SharePolicyService.check_if_policy_exists',
        return_value=False,
    )
    mocker.patch(
        'dataall.modules.s3_datasets_shares.services.s3_share_managed_policy_service.S3SharePolicyService.get_policies_unattached_to_role',
        return_value='policy-0',
    )
    attach_mocker = mocker.patch(
        'dataall.modules.s3_datasets_shares.services.s3_share_managed_policy_service.S3SharePolicyService.attach_policies',
        return_value=True,
    )
    mocker.patch('dataall.base.aws.iam.IAM.list_policy_names_by_policy_pattern', return_value=['policy-0'])

    create_share_object_response = create_share_object(
        mocker=mocker,
        client=client,
        username=user2.username,
        group=group2,
        groupUri=env2group.groupUri,
        environmentUri=env2.environmentUri,
        datasetUri=dataset1.datasetUri,
        attachMissingPolicies=False,
    )
    # Then share object created with status Draft and user is 'Requester'
    attach_mocker.assert_called_once()
    assert create_share_object_response.data.createShareObject.shareUri
    assert create_share_object_response.data.createShareObject.status == ShareObjectStatus.Draft.value
    assert create_share_object_response.data.createShareObject.userRoleForShareObject == 'Requesters'
    assert create_share_object_response.data.createShareObject.requestPurpose == 'testShare'


def test_create_share_object_share_policy_not_attached_attachMissingPolicies_disabled_dataallNotManaged(
    mocker, client, user2, group2, env2group, env2, dataset1
):
    # Given
    # Existing dataset, target environment and group
    # SharePolicy exists and is NOT attached, attachMissingPolicies=True
    # When a correct user creates request, data.all attaches the policy and the share creates successfully
    mocker.patch(
        'dataall.base.aws.iam.IAM.get_role_arn_by_name',
        return_value='role_arn',
    )
    mocker.patch(
        'dataall.modules.s3_datasets_shares.services.s3_share_managed_policy_service.S3SharePolicyService.check_if_policy_exists',
        return_value=False,
    )
    mocker.patch(
        'dataall.modules.s3_datasets_shares.services.s3_share_managed_policy_service.S3SharePolicyService.get_policies_unattached_to_role',
        return_value='policy-0',
    )
    mocker.patch('dataall.base.aws.iam.IAM.list_policy_names_by_policy_pattern', return_value=['policy-0'])

    consumption_role = MagicMock(spec_set=ConsumptionRole)
    consumption_role.IAMRoleName = 'randomName'
    consumption_role.IAMRoleArn = 'randomArn'
    consumption_role.dataallManaged = False
    mocker.patch(
        'dataall.core.environment.services.environment_service.EnvironmentService.get_environment_consumption_role',
        return_value=consumption_role,
    )
    create_share_object_response = create_share_object(
        mocker=mocker,
        client=client,
        username=user2.username,
        group=group2,
        groupUri=env2group.groupUri,
        environmentUri=env2.environmentUri,
        datasetUri=dataset1.datasetUri,
        attachMissingPolicies=False,
        principalId=consumption_role.IAMRoleName,
        principalType=PrincipalType.ConsumptionRole.value,
    )
    # Then share object is not created and an error appears
    assert 'Required customer managed policies' in create_share_object_response.errors[0].message
    assert 'are not attached to role randomName' in create_share_object_response.errors[0].message


def test_create_share_object_with_share_expiration_added(
    mocker, client, user2, group2, env2group, env2, dataset_with_expiration
):
    mocker.patch(
        'dataall.base.aws.iam.IAM.get_role_arn_by_name',
        return_value='role_arn',
    )
    mocker.patch(
        'dataall.modules.s3_datasets_shares.services.s3_share_managed_policy_service.S3SharePolicyService.check_if_policy_exists',
        return_value=False,
    )
    mocker.patch(
        'dataall.modules.s3_datasets_shares.services.s3_share_managed_policy_service.S3SharePolicyService.get_policies_unattached_to_role',
        return_value='policy-0',
    )
    mocker.patch('dataall.base.aws.iam.IAM.list_policy_names_by_policy_pattern', return_value=['policy-0'])
    mocker.patch(
        'dataall.modules.s3_datasets_shares.services.s3_share_managed_policy_service.S3SharePolicyService.attach_policies',
        return_value=True,
    )

    create_share_object_response = create_share_object(
        mocker=mocker,
        client=client,
        username=user2.username,
        group=group2,
        groupUri=env2group.groupUri,
        environmentUri=env2.environmentUri,
        datasetUri=dataset_with_expiration.datasetUri,
        shareExpirationPeriod=2,
    )

    # Then share object created with status Draft and user is 'Requester'
    assert create_share_object_response.data.createShareObject.shareUri
    assert create_share_object_response.data.createShareObject.status == ShareObjectStatus.Draft.value
    assert create_share_object_response.data.createShareObject.nonExpirable == False
    date_format = '%Y-%m-%d %H:%M:%S'
    requested_share_expiration_date = datetime.strptime(
        create_share_object_response.data.createShareObject.requestedExpiryDate, date_format
    )
    assert (
        requested_share_expiration_date.date()
        == ExpirationUtils.calculate_expiry_date(2, dataset_with_expiration.expirySetting).date()
    )


def test_create_share_object_with_non_expiring_share(
    mocker, client, user2, group2, env2group, env2, dataset_with_expiration_3
):
    mocker.patch(
        'dataall.base.aws.iam.IAM.get_role_arn_by_name',
        return_value='role_arn',
    )
    mocker.patch(
        'dataall.modules.s3_datasets_shares.services.s3_share_managed_policy_service.S3SharePolicyService.check_if_policy_exists',
        return_value=False,
    )
    mocker.patch(
        'dataall.modules.s3_datasets_shares.services.s3_share_managed_policy_service.S3SharePolicyService.get_policies_unattached_to_role',
        return_value='policy-0',
    )
    mocker.patch('dataall.base.aws.iam.IAM.list_policy_names_by_policy_pattern', return_value=['policy-0'])
    mocker.patch(
        'dataall.modules.s3_datasets_shares.services.s3_share_managed_policy_service.S3SharePolicyService.attach_policies',
        return_value=True,
    )

    create_share_object_response = create_share_object(
        mocker=mocker,
        client=client,
        username=user2.username,
        group=group2,
        groupUri=env2group.groupUri,
        environmentUri=env2.environmentUri,
        datasetUri=dataset_with_expiration_3.datasetUri,
        shareExpirationPeriod=None,
        nonExpiring=True,
    )

    # Then share object created with status Draft and user is 'Requester'
    assert create_share_object_response.data.createShareObject.shareUri
    assert create_share_object_response.data.createShareObject.status == ShareObjectStatus.Draft.value
    assert create_share_object_response.data.createShareObject.requestedExpiryDate == None
    assert create_share_object_response.data.createShareObject.nonExpirable == True


def test_create_share_object_with_share_expiration_incorrect_share_expiration(
    mocker, client, user2, group2, env2group, env2, dataset_with_expiration
):
    mocker.patch(
        'dataall.base.aws.iam.IAM.get_role_arn_by_name',
        return_value='role_arn',
    )
    mocker.patch(
        'dataall.modules.s3_datasets_shares.services.s3_share_managed_policy_service.S3SharePolicyService.check_if_policy_exists',
        return_value=False,
    )
    mocker.patch(
        'dataall.modules.s3_datasets_shares.services.s3_share_managed_policy_service.S3SharePolicyService.get_policies_unattached_to_role',
        return_value='policy-0',
    )
    mocker.patch('dataall.base.aws.iam.IAM.list_policy_names_by_policy_pattern', return_value=['policy-0'])
    mocker.patch(
        'dataall.modules.s3_datasets_shares.services.s3_share_managed_policy_service.S3SharePolicyService.attach_policies',
        return_value=True,
    )

    create_share_object_response = create_share_object(
        mocker=mocker,
        client=client,
        username=user2.username,
        group=group2,
        groupUri=env2group.groupUri,
        environmentUri=env2.environmentUri,
        datasetUri=dataset_with_expiration.datasetUri,
        shareExpirationPeriod=5,
    )

    assert (
        'Share expiration period is not within the maximum and the minimum expiration duration'
        in create_share_object_response.errors[0].message
    )


def test_get_share_object(client, share1_draft, user, group):
    # Given
    # Existing share object in status Draft (->fixture share1_draft)
    # When a user from the approvers group gets the share object
    get_share_object_response = get_share_object(
        client=client, user=user, group=group, shareUri=share1_draft.shareUri, filter={}
    )
    # Then we get the info about the share
    assert get_share_object_response.data.getShareObject.shareUri == share1_draft.shareUri
    assert get_share_object_response.data.getShareObject.get('principal').principalType == PrincipalType.Group.name
    assert get_share_object_response.data.getShareObject.get('principal').principalRoleName
    assert get_share_object_response.data.getShareObject.get('principal').SamlGroupName


def test_update_share_request_purpose(client, share1_draft, user2, group2):
    # Given
    # Existing share object in status Draft (->fixture share1_draft)
    # When a user from the requesters group updates
    update_share_request_purpose_response = update_share_request_purpose(
        client=client, user=user2, group=group2, shareUri=share1_draft.shareUri, requestPurpose='NewRequestPurpose'
    )

    # Then the requestPurpose of the Share is Updated
    get_share_object_response = get_share_object(
        client=client, user=user2, group=group2, shareUri=share1_draft.shareUri, filter={}
    )

    assert get_share_object_response.data.getShareObject.requestPurpose == 'NewRequestPurpose'
    assert get_share_object_response.data.getShareObject.userRoleForShareObject == 'Requesters'


def test_update_share_request_purpose_unauthorized(client, share1_draft, user, group):
    # Given
    # Existing share object in status Draft (->fixture share1_draft)
    # When a user from the approvers group attempts to update the request purpose
    update_share_request_purpose_response = update_share_request_purpose(
        client=client, user=user, group=group, shareUri=share1_draft.shareUri, requestPurpose='NewRequestPurpose'
    )

    # Then we get an error of the type
    assert 'UnauthorizedOperation' in update_share_request_purpose_response.errors[0].message


def test_update_share_extension_purpose(client, share1_draft, user2, group2):
    update_share_extension_reason(client, user2, group2, share1_draft.shareUri, 'Extension Reason')

    get_share_object_response = get_share_object(
        client=client, user=user2, group=group2, shareUri=share1_draft.shareUri, filter={}
    )

    assert get_share_object_response.data.getShareObject.extensionReason == 'Extension Reason'
    assert get_share_object_response.data.getShareObject.userRoleForShareObject == 'Requesters'


def test_update_share_extension_purpose_unauthorized(client, share1_draft, user, group):
    response_update_share_extension = update_share_extension_reason(
        client, user, group, share1_draft.shareUri, 'Extension Reason'
    )

    get_share_object_response = get_share_object(
        client=client, user=user, group=group, shareUri=share1_draft.shareUri, filter={}
    )

    assert 'UnauthorizedOperation' in response_update_share_extension.errors[0].message


def test_list_shares_to_me_approver(client, user, group, share1_draft):
    # Given
    # Existing share object in status Draft (->fixture share1_draft) + share object (-> fixture share)
    # When a user from the Approvers group lists the share objects sent to him
    get_share_requests_to_me_response = get_share_requests_to_me(client=client, user=user, group=group)
    # Then he sees the 2 shares
    assert get_share_requests_to_me_response.data.getShareRequestsToMe.count == 4


def test_list_shares_to_me_requester(client, user2, group2, share1_draft):
    # Given
    # Existing share object in status Draft (->fixture share1_draft)
    # When a user from the Requesters group lists the share objects sent to him
    get_share_requests_to_me_response = get_share_requests_to_me(client=client, user=user2, group=group2)
    # Then he sees None
    assert get_share_requests_to_me_response.data.getShareRequestsToMe.count == 0


def test_list_shares_from_me_approver(client, user, group, share1_draft):
    # Given
    # Existing share object in status Draft (->fixture share1_draft) + share object (-> fixture share)
    # When a user from the Approvers group lists the share objects sent from him
    get_share_requests_from_me_response = get_share_requests_from_me(client=client, user=user, group=group)
    # Then he sees None
    assert get_share_requests_from_me_response.data.getShareRequestsFromMe.count == 0


def test_list_shares_from_me_requester(client, user2, group2, share1_draft):
    # Given
    # Existing share object in status Draft (->fixture share1_draft) + share object (-> fixture share)
    # When a user from the Requesters group lists the share objects sent from him
    get_share_requests_from_me_response = get_share_requests_from_me(client=client, user=user2, group=group2)
    # Then he sees the 2 shares
    assert get_share_requests_from_me_response.data.getShareRequestsFromMe.count == 4


def test_add_share_item(client, user2, group2, share1_draft, mock_glue_client):
    # Given
    # Existing share object in status Draft (-> fixture share1_draft)
    get_share_object_response = get_share_object(
        client=client, user=user2, group=group2, shareUri=share1_draft.shareUri, filter={'isShared': False}
    )
    # Given existing shareable items (-> fixture)
    shareableItem = get_share_object_response.data.getShareObject.get('items').nodes[0]
    itemUri = shareableItem['itemUri']
    itemType = shareableItem['itemType']
    shareItemUri = shareableItem['shareItemUri']
    assert shareItemUri is None

    # When we add item
    add_share_item_response = add_share_item(
        client=client, user=user2, group=group2, shareUri=share1_draft.shareUri, itemUri=itemUri, itemType=itemType
    )

    # Then shared item was added to share object in status PendingApproval
    assert add_share_item_response.data.addSharedItem.shareUri == share1_draft.shareUri
    assert add_share_item_response.data.addSharedItem.status == ShareItemStatus.PendingApproval.name


# remove_share_item_filter
def test_update_share_item_filter(client, user, group, share1_draft, share1_item_pa, table_data_filter_fixture):
    # # Given
    # # Existing share object in status Draft (-> fixture share1_draft)
    get_share_object_response = get_share_object(
        client=client, user=user, group=group, shareUri=share1_draft.shareUri, filter={'isShared': True}
    )
    # # Given existing shareable items (-> fixture)
    shareItem = get_share_object_response.data.getShareObject.get('items').nodes[0]
    print('\n\n\n\n SHARE ITMES \n\n')
    print(get_share_object_response.data.getShareObject.get('items'))
    assert shareItem.shareItemUri == share1_item_pa.shareItemUri

    # When we update share item filter
    input = {
        'shareItemUri': share1_item_pa.shareItemUri,
        'label': 'test',
        'filterUris': [table_data_filter_fixture.filterUri],
        'filterNames': [table_data_filter_fixture.label],
    }
    update_share_item_filter_response = update_share_item_filter(client=client, user=user, group=group, input=input)

    # Then shared item filter was added to share object item
    assert update_share_item_filter_response.data.updateShareItemFilters == True
    get_share_object_response = get_share_object(
        client=client, user=user, group=group, shareUri=share1_draft.shareUri, filter={'isShared': True}
    )
    shareItem = get_share_object_response.data.getShareObject.get('items').nodes[0]
    assert shareItem.attachedDataFilterUri

    get_share_item_data_filters_response = get_share_item_data_filters(
        client=client, user=user, group=group, attachedDataFilterUri=shareItem.attachedDataFilterUri
    )
    assert get_share_item_data_filters_response.data.getShareItemDataFilters.itemUri == share1_item_pa.itemUri
    assert (
        get_share_item_data_filters_response.data.getShareItemDataFilters.dataFilterUris[0]
        == table_data_filter_fixture.filterUri
    )
    assert (
        get_share_item_data_filters_response.data.getShareItemDataFilters.dataFilterNames[0]
        == table_data_filter_fixture.label
    )

    # When we update share item filter
    input = {
        'shareItemUri': share1_item_pa.shareItemUri,
        'label': 'testnew',
        'filterUris': [table_data_filter_fixture.filterUri],
        'filterNames': [table_data_filter_fixture.label],
    }
    update_share_item_filter_response = update_share_item_filter(client=client, user=user, group=group, input=input)

    # Then shared item filter name was updated
    get_share_item_data_filters_response = get_share_item_data_filters(
        client=client, user=user, group=group, attachedDataFilterUri=shareItem.attachedDataFilterUri
    )
    assert get_share_item_data_filters_response.data.getShareItemDataFilters.label == 'testnew'

    # When we remove the share item filter
    remove_share_item_filter_response = remove_share_item_filter(
        client=client, user=user, group=group, attachedDataFilterUri=shareItem.attachedDataFilterUri
    )

    # Then Share item has not attached filter URI
    get_share_object_response = get_share_object(
        client=client, user=user, group=group, shareUri=share1_draft.shareUri, filter={'isShared': True}
    )
    # # Given existing shareable items (-> fixture)
    shareItem = get_share_object_response.data.getShareObject.get('items').nodes[0]
    assert shareItem.attachedDataFilterUri is None


def test_remove_share_item(client, user2, group2, share1_draft, share1_item_pa):
    # Existing share object in status Draft (-> fixture share1_draft)
    # with existing share item in status Pending Approval (-> fixture share_item_pa)
    get_share_object_response = get_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share1_draft.shareUri,
        filter={'isShared': True},
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Draft.value

    shareItem = get_share_object_response.data.getShareObject.get('items').nodes[0]
    assert shareItem.shareItemUri == share1_item_pa.shareItemUri
    assert shareItem.status == ShareItemStatus.PendingApproval.value
    assert get_share_object_response.data.getShareObject.get('items').count == 1

    # When
    remove_share_item_response = remove_share_item(
        client=client, user=user2, group=group2, shareItemUri=shareItem.shareItemUri
    )

    # Then there are no more shared items added to the request
    get_share_object_response = get_share_object(
        client=client, user=user2, group=group2, shareUri=share1_draft.shareUri, filter={'isShared': True}
    )

    assert get_share_object_response.data.getShareObject.get('items').count == 0


def test_submit_share_request(client, user2, group2, share1_draft, share1_item_pa, mocker):
    # Given
    # Existing share object in status Draft (-> fixture share1_draft)
    # with existing share item in status Pending Approval (-> fixture share1_item_pa)
    get_share_object_response = get_share_object(
        client=client, user=user2, group=group2, shareUri=share1_draft.shareUri, filter={'isShared': True}
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Draft.value

    shareItem = get_share_object_response.data.getShareObject.get('items').nodes[0]
    assert shareItem.shareItemUri == share1_item_pa.shareItemUri
    assert shareItem.status == ShareItemStatus.PendingApproval.value
    assert get_share_object_response.data.getShareObject.get('items').count == 1

    mocker.patch(
        'dataall.base.aws.sts.SessionHelper.remote_session',
        return_value=boto3.Session(),
    )

    # Mock glue and sts calls to create a LF processor
    mocker.patch(
        'dataall.base.aws.sts.SessionHelper.get_account',
        return_value='1111',
    )
    # Mock glue and sts calls to create a LF processor
    mocker.patch(
        'dataall.base.aws.sts.SessionHelper.get_delegation_role_arn',
        return_value='arn',
    )

    mocker.patch(
        'dataall.base.aws.iam.IAM.get_role_arn_by_name',
        return_value='fake_role_arn',
    )
    # When
    # Submit share object
    submit_share_object_response = submit_share_object(
        client=client, user=user2, group=group2, shareUri=share1_draft.shareUri
    )

    # Then share object status is changed to Submitted
    assert submit_share_object_response.data.submitShareObject.status == ShareObjectStatus.Submitted.name
    assert submit_share_object_response.data.submitShareObject.userRoleForShareObject == 'Requesters'

    # and share item status stays in PendingApproval
    get_share_object_response = get_share_object(
        client=client, user=user2, group=group2, shareUri=share1_draft.shareUri, filter={'isShared': True}
    )
    shareItem = get_share_object_response.data.getShareObject.get('items').nodes[0]
    status = shareItem['status']
    assert status == ShareItemStatus.PendingApproval.name


def test_submit_share_extension_request(
    client,
    user2,
    group2,
    share3_item_expiration_share,
    share3_with_expiration_processed,
    mocker,
    dataset_with_expiration_2,
):
    # Given
    # Existing share object in status Processed (-> fixture share3_item_expiration_share)
    # with existing share item in status Share_Succeeded (-> fixture share3_with_expiration_processed)
    get_share_object_response = get_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share3_with_expiration_processed.shareUri,
        filter={'isShared': True},
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Processed.value

    # Submit a share extension request
    submit_share_extension(client, user2, group2, share3_with_expiration_processed.shareUri, 1)

    get_share_object_response = get_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share3_with_expiration_processed.shareUri,
        filter={'isShared': True},
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Submitted_For_Extension.value
    date_format = '%Y-%m-%d %H:%M:%S'
    share_expiration_date = datetime.strptime(
        get_share_object_response.data.getShareObject.requestedExpiryDate, date_format
    )
    assert (
        share_expiration_date.date()
        == ExpirationUtils.calculate_expiry_date(1, dataset_with_expiration_2.expirySetting).date()
    )

    cancel_share_extension(client, user2, group2, share3_with_expiration_processed.shareUri)


def test_submit_share_extension_request_non_expiring_share(
    client,
    user2,
    group2,
    share3_item_expiration_share,
    share3_with_expiration_processed,
    mocker,
    dataset_with_expiration_2,
):
    # Given
    # Existing share object in status Processed (-> fixture share3_item_expiration_share)
    # with existing share item in status Share_Succeeded (-> fixture share3_with_expiration_processed)
    get_share_object_response = get_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share3_with_expiration_processed.shareUri,
        filter={'isShared': True},
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Processed.value

    # Submit a share extension request
    submit_share_extension(client, user2, group2, share3_with_expiration_processed.shareUri, None, True)

    get_share_object_response = get_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share3_with_expiration_processed.shareUri,
        filter={'isShared': True},
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Submitted_For_Extension.value
    assert get_share_object_response.data.getShareObject.requestedExpiryDate == None
    assert get_share_object_response.data.getShareObject.nonExpirable == True

    cancel_share_extension(client, user2, group2, share3_with_expiration_processed.shareUri)


def test_submit_share_request_with_auto_approval(
    client, user2, group2, share_autoapprove_draft, share_autoapprove_item_pa, mocker
):
    # Given
    # Existing share object in status Draft (-> fixture share1_draft)
    # with existing share item in status Pending Approval (-> fixture share1_item_pa)
    get_share_object_response = get_share_object(
        client=client, user=user2, group=group2, shareUri=share_autoapprove_draft.shareUri, filter={'isShared': True}
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Draft.value

    shareItem = get_share_object_response.data.getShareObject.get('items').nodes[0]
    assert shareItem.shareItemUri == share_autoapprove_item_pa.shareItemUri
    assert shareItem.status == ShareItemStatus.PendingApproval.value
    assert get_share_object_response.data.getShareObject.get('items').count == 1

    mocker.patch(
        'dataall.base.aws.sts.SessionHelper.remote_session',
        return_value=boto3.Session(),
    )

    # Mock glue and sts calls to create a LF processor
    mocker.patch(
        'dataall.base.aws.sts.SessionHelper.get_account',
        return_value='1111',
    )
    # Mock glue and sts calls to create a LF processor
    mocker.patch(
        'dataall.base.aws.sts.SessionHelper.get_delegation_role_arn',
        return_value='arn',
    )

    mocker.patch(
        'dataall.base.aws.iam.IAM.get_role_arn_by_name',
        return_value='fake_role_arn',
    )
    # When
    # Submit share object
    submit_share_object_response = submit_share_object(
        client=client, user=user2, group=group2, shareUri=share_autoapprove_draft.shareUri
    )

    # Then share object status is changed to Submitted
    assert submit_share_object_response.data.submitShareObject.status == ShareObjectStatus.Approved.name
    assert submit_share_object_response.data.submitShareObject.userRoleForShareObject == 'ApproversAndRequesters'

    # and share item status stays in PendingApproval
    get_share_object_response = get_share_object(
        client=client, user=user2, group=group2, shareUri=share_autoapprove_draft.shareUri, filter={'isShared': True}
    )
    shareItem = get_share_object_response.data.getShareObject.get('items').nodes[0]
    status = shareItem['status']
    assert status == ShareItemStatus.Share_Approved.name


def test_submit_share_extension_request_with_auto_approval(
    client,
    user2,
    group2,
    share3_item_expiration_share_with_autoapproval,
    share3_with_expiration_processed_with_autoapproval,
    mocker,
    dataset_with_expiration_with_autoapproval,
):
    # Given
    # Existing share object in status Processed (-> fixture share3_item_expiration_share)
    # with existing share item in status Share_Succeeded (-> fixture share3_with_expiration_processed)
    get_share_object_response = get_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share3_with_expiration_processed_with_autoapproval.shareUri,
        filter={'isShared': True},
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Processed.value
    mocker.patch(
        'dataall.base.aws.sts.SessionHelper.remote_session',
        return_value=boto3.Session(),
    )

    # Mock glue and sts calls to create a LF processor
    mocker.patch(
        'dataall.base.aws.sts.SessionHelper.get_account',
        return_value='1111',
    )
    # Mock glue and sts calls to create a LF processor
    mocker.patch(
        'dataall.base.aws.sts.SessionHelper.get_delegation_role_arn',
        return_value='arn',
    )

    mocker.patch(
        'dataall.base.aws.iam.IAM.get_role_arn_by_name',
        return_value='fake_role_arn',
    )
    # Submit a share extension request with a dataset which has auto approval on it
    submit_share_extension(client, user2, group2, share3_with_expiration_processed_with_autoapproval.shareUri, 1)

    get_share_object_response = get_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share3_with_expiration_processed_with_autoapproval.shareUri,
        filter={'isShared': True},
    )

    # share should be auto approved for share extension as well
    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Processed.value
    date_format = '%Y-%m-%d %H:%M:%S'
    share_expiration_date = datetime.strptime(get_share_object_response.data.getShareObject.expiryDate, date_format)
    assert (
        share_expiration_date.date()
        == ExpirationUtils.calculate_expiry_date(1, dataset_with_expiration_with_autoapproval.expirySetting).date()
    )


def test_update_share_reject_purpose(client, share2_submitted, user, group):
    # Given
    # Existing share object in status Submitted (-> fixture share2_submitted)
    # When a user from the approvers group updates the reject purpose
    update_share_reject_purpose_response = update_share_reject_purpose(
        client=client, user=user, group=group, shareUri=share2_submitted.shareUri, rejectPurpose='NewRejectPurpose'
    )

    # Then the rejectPurpose of the Share is Updated
    get_share_object_response = get_share_object(
        client=client, user=user, group=group, shareUri=share2_submitted.shareUri, filter={}
    )

    assert get_share_object_response.data.getShareObject.rejectPurpose == 'NewRejectPurpose'
    assert get_share_object_response.data.getShareObject.userRoleForShareObject == 'Approvers'


def test_update_share_reject_purpose_unauthorized(client, share2_submitted, user2, group2):
    # Given
    # Existing share object in status Submitted (-> fixture share2_submitted)
    # When a user from the requester group attempts to update the reject purpose
    update_share_reject_purpose_response = update_share_reject_purpose(
        client=client, user=user2, group=group2, shareUri=share2_submitted.shareUri, rejectPurpose='NewRejectPurpose'
    )

    # Then we get an error of the type
    assert 'UnauthorizedOperation' in update_share_reject_purpose_response.errors[0].message


def test_approve_share_request(db, client, user, group, share2_submitted, share2_item_pa, mocker):
    # Given
    # Existing share object in status Submitted (-> fixture share2_submitted)
    # with existing share item in status Pending Approval (-> fixture share2_item_pa)
    get_share_object_response = get_share_object(
        client=client, user=user, group=group, shareUri=share2_submitted.shareUri, filter={'isShared': True}
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Submitted.value
    shareItem = get_share_object_response.data.getShareObject.get('items').nodes[0]
    assert shareItem.shareItemUri == share2_item_pa.shareItemUri
    assert shareItem.status == ShareItemStatus.PendingApproval.value
    assert get_share_object_response.data.getShareObject.get('items').count == 1

    mocker.patch(
        'dataall.base.aws.sts.SessionHelper.remote_session',
        return_value=boto3.Session(),
    )

    # Mock glue and sts calls to create a LF processor
    mocker.patch(
        'dataall.base.aws.sts.SessionHelper.get_account',
        return_value='1111',
    )
    # Mock glue and sts calls to create a LF processor
    mocker.patch(
        'dataall.base.aws.sts.SessionHelper.get_delegation_role_arn',
        return_value='arn',
    )

    mocker.patch(
        'dataall.base.aws.iam.IAM.get_role_arn_by_name',
        return_value='fake_role_arn',
    )
    # When we approve the share object
    approve_share_object_response = approve_share_object(
        client=client, user=user, group=group, shareUri=share2_submitted.shareUri
    )

    # UserRole for shareObject is the Approvers in this case (user, group)
    assert approve_share_object_response.data.approveShareObject.userRoleForShareObject == 'Approvers'

    # Then share object status is changed to Approved
    assert approve_share_object_response.data.approveShareObject.status == ShareObjectStatus.Approved.name

    # and share item status is changed to Share_Approved
    get_share_object_response = get_share_object(
        client=client, user=user, group=group, shareUri=share2_submitted.shareUri, filter={'isShared': True}
    )

    shareItem = get_share_object_response.data.getShareObject.get('items').nodes[0]
    assert shareItem.status == ShareItemStatus.Share_Approved.value

    # When approved share object is processed and the shared items successfully shared
    _successfull_processing_for_share_object(db, share2_submitted)

    get_share_object_response = get_share_object(
        client=client, user=user, group=group, shareUri=share2_submitted.shareUri, filter={'isShared': True}
    )

    # Then share object status is changed to Processed
    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Processed.value

    # And share item status is changed to Share_Succeeded
    shareItem = get_share_object_response.data.getShareObject.get('items').nodes[0]
    assert shareItem.status == ShareItemStatus.Share_Succeeded.value


def test_approve_share_extension(
    client,
    user,
    group,
    user2,
    group2,
    share3_item_expiration_share,
    share3_with_expiration_processed,
    mocker,
    dataset_with_expiration_2,
):
    # Given
    # Existing share object in status Processed (-> fixture share3_item_expiration_share)
    # with existing share item in status Share_Succeeded (-> fixture share3_with_expiration_processed)
    get_share_object_response = get_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share3_with_expiration_processed.shareUri,
        filter={'isShared': True},
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Processed.value

    mocker.patch(
        'dataall.base.aws.sts.SessionHelper.remote_session',
        return_value=boto3.Session(),
    )

    # Mock glue and sts calls to create a LF processor
    mocker.patch(
        'dataall.base.aws.sts.SessionHelper.get_account',
        return_value='1111',
    )
    # Mock glue and sts calls to create a LF processor
    mocker.patch(
        'dataall.base.aws.sts.SessionHelper.get_delegation_role_arn',
        return_value='arn',
    )

    mocker.patch(
        'dataall.base.aws.iam.IAM.get_role_arn_by_name',
        return_value='fake_role_arn',
    )

    # Submit a share extension request
    submit_share_extension(client, user2, group2, share3_with_expiration_processed.shareUri, 1)

    get_share_object_response = get_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share3_with_expiration_processed.shareUri,
        filter={'isShared': True},
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Submitted_For_Extension.value
    date_format = '%Y-%m-%d %H:%M:%S'
    share_expiration_date = datetime.strptime(
        get_share_object_response.data.getShareObject.requestedExpiryDate, date_format
    )
    assert (
        share_expiration_date.date()
        == ExpirationUtils.calculate_expiry_date(1, dataset_with_expiration_2.expirySetting).date()
    )
    requested_expiration_date_raw = get_share_object_response.data.getShareObject.requestedExpiryDate

    # Approve Share Extension
    approve_share_extension(client, user2, group2, share3_with_expiration_processed.shareUri)

    get_share_object_response = get_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share3_with_expiration_processed.shareUri,
        filter={'isShared': True},
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Processed.value
    share_item = get_share_object_response.data.getShareObject.get('items').nodes[0]
    assert share_item.shareItemUri == share3_item_expiration_share.shareItemUri
    assert share_item.status == ShareItemStatus.Share_Succeeded.value
    assert get_share_object_response.data.getShareObject.get('items').count == 1
    assert get_share_object_response.data.getShareObject.expiryDate == requested_expiration_date_raw


def test_approve_share_extension_non_expiring(
    client,
    user,
    group,
    user2,
    group2,
    share3_item_expiration_share,
    share3_with_expiration_processed,
    mocker,
    dataset_with_expiration_2,
):
    # Given
    # Existing share object in status Processed (-> fixture share3_item_expiration_share)
    # with existing share item in status Share_Succeeded (-> fixture share3_with_expiration_processed)
    get_share_object_response = get_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share3_with_expiration_processed.shareUri,
        filter={'isShared': True},
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Processed.value

    mocker.patch(
        'dataall.base.aws.sts.SessionHelper.remote_session',
        return_value=boto3.Session(),
    )

    # Mock glue and sts calls to create a LF processor
    mocker.patch(
        'dataall.base.aws.sts.SessionHelper.get_account',
        return_value='1111',
    )
    # Mock glue and sts calls to create a LF processor
    mocker.patch(
        'dataall.base.aws.sts.SessionHelper.get_delegation_role_arn',
        return_value='arn',
    )

    mocker.patch(
        'dataall.base.aws.iam.IAM.get_role_arn_by_name',
        return_value='fake_role_arn',
    )

    # Submit a share extension request
    submit_share_extension(client, user2, group2, share3_with_expiration_processed.shareUri, None, True)

    get_share_object_response = get_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share3_with_expiration_processed.shareUri,
        filter={'isShared': True},
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Submitted_For_Extension.value
    assert get_share_object_response.data.getShareObject.requestedExpiryDate == None
    assert get_share_object_response.data.getShareObject.nonExpirable == True

    # Approve Share Extension
    approve_share_extension(client, user2, group2, share3_with_expiration_processed.shareUri)

    get_share_object_response = get_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share3_with_expiration_processed.shareUri,
        filter={'isShared': True},
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Processed.value
    share_item = get_share_object_response.data.getShareObject.get('items').nodes[0]
    assert get_share_object_response.data.getShareObject.expiryDate == None
    assert share_item.shareItemUri == share3_item_expiration_share.shareItemUri
    assert share_item.status == ShareItemStatus.Share_Succeeded.value
    assert get_share_object_response.data.getShareObject.get('items').count == 1


def test_reject_share_request(client, user, group, share2_submitted, share2_item_pa):
    # Given
    # Existing share object in status Submitted (-> fixture share2_submitted)
    # with existing share item in status Pending Approval (-> fixture share2_item_pa)
    get_share_object_response = get_share_object(
        client=client, user=user, group=group, shareUri=share2_submitted.shareUri, filter={'isShared': True}
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Submitted.value
    shareItem = get_share_object_response.data.getShareObject.get('items').nodes[0]
    assert shareItem.shareItemUri == share2_item_pa.shareItemUri
    assert shareItem.status == ShareItemStatus.PendingApproval.value
    assert get_share_object_response.data.getShareObject.get('items').count == 1

    # When we reject the share object
    reject_share_object_response = reject_share_object(
        client=client, user=user, group=group, shareUri=share2_submitted.shareUri
    )

    # Then share object status is changed to Rejected
    assert reject_share_object_response.data.rejectShareObject.status == ShareObjectStatus.Rejected.name
    assert reject_share_object_response.data.rejectShareObject.rejectPurpose == 'testRejectShare'

    # and share item status is changed to Share_Rejected
    get_share_object_response = get_share_object(
        client=client, user=user, group=group, shareUri=share2_submitted.shareUri, filter={'isShared': True}
    )

    shareItem = get_share_object_response.data.getShareObject.get('items').nodes[0]
    assert shareItem.status == ShareItemStatus.Share_Rejected.value


def test_search_shared_items_in_environment(
    client,
    user2,
    group2,
    share3_processed,
    share3_item_shared,
    env2,
):
    # Given
    # Existing share object in status Processed (-> fixture share3_processed) from env2
    get_share_object_response = get_share_object(
        client=client, user=user2, group=group2, shareUri=share3_processed.shareUri, filter={'isShared': True}
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Processed.value

    list_datasets_published_in_environment_response = list_datasets_published_in_environment(
        client=client, user=user2, group=group2, environmentUri=env2.environmentUri
    )
    # Then we get the share information from the environment2
    assert (
        list_datasets_published_in_environment_response.data.searchEnvironmentDataItems.nodes[0].principalId
        == group2.name
    )


def test_verify_items_share_request(db, client, user2, group2, share3_processed, share3_item_shared):
    # Given
    # Existing share object in status Processed (-> fixture share3_processed)
    # with existing share item in status Share_Succeeded (-> fixture share3_item_shared)
    get_share_object_response = get_share_object(
        client=client, user=user2, group=group2, shareUri=share3_processed.shareUri, filter={'isShared': True}
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Processed.value

    shareItem = get_share_object_response.data.getShareObject.get('items').nodes[0]
    assert shareItem.shareItemUri == share3_item_shared.shareItemUri
    assert shareItem.status == ShareItemStatus.Share_Succeeded.value
    verify_items_uris = [node.shareItemUri for node in get_share_object_response.data.getShareObject.get('items').nodes]

    # When
    # verifying items from share object
    verify_items_share_object_response = verify_items_share_object(
        client=client, user=user2, group=group2, shareUri=share3_processed.shareUri, verify_items_uris=verify_items_uris
    )

    # Then share item health Status changes to PendingVerify
    get_share_object_response = get_share_object(
        client=client, user=user2, group=group2, shareUri=share3_processed.shareUri, filter={'isShared': True}
    )
    print(get_share_object_response.data.getShareObject.get('items').nodes)
    sharedItem = get_share_object_response.data.getShareObject.get('items').nodes[0]
    status = sharedItem['healthStatus']
    assert status == ShareItemHealthStatus.PendingVerify.value


def test_reapply_items_share_request(db, client, user, group, share3_processed, share3_item_shared_unhealthy):
    # Given
    # Existing share object in status Processed (-> fixture share3_processed)
    # with existing share item in status Share_Succeeded (-> fixture share3_item_shared)
    get_share_object_response = get_share_object(
        client=client,
        user=user,
        group=group,
        shareUri=share3_processed.shareUri,
        filter={'isShared': True, 'isHealthy': False},
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Processed.value

    shareItem = get_share_object_response.data.getShareObject.get('items').nodes[0]
    assert shareItem.shareItemUri == share3_item_shared_unhealthy.shareItemUri
    assert shareItem.status == ShareItemStatus.Share_Succeeded.value
    reapply_items_uris = [
        node.shareItemUri for node in get_share_object_response.data.getShareObject.get('items').nodes
    ]

    # When
    # re-applying share items from share object
    reapply_items_share_object(
        client=client, user=user, group=group, shareUri=share3_processed.shareUri, reapply_items_uris=reapply_items_uris
    )

    # Then share item health Status changes to PendingReApply
    get_share_object_response = get_share_object(
        client=client,
        user=user,
        group=group,
        shareUri=share3_processed.shareUri,
        filter={'isShared': True, 'isHealthy': False},
    )
    sharedItem = get_share_object_response.data.getShareObject.get('items').nodes[0]
    status = sharedItem['healthStatus']
    assert status == ShareItemHealthStatus.PendingReApply.value


def test_reapply_items_share_request_unauthorized(
    db, client, user2, group2, share3_processed, share3_item_shared_unhealthy
):
    # Given
    # Existing share object in status Processed (-> fixture share3_processed)
    # with existing share item in status Share_Succeeded (-> fixture share3_item_shared)
    get_share_object_response = get_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share3_processed.shareUri,
        filter={'isShared': True, 'isHealthy': False},
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Processed.value

    shareItem = get_share_object_response.data.getShareObject.get('items').nodes[0]
    assert shareItem.shareItemUri == share3_item_shared_unhealthy.shareItemUri
    assert shareItem.status == ShareItemStatus.Share_Succeeded.value
    reapply_items_uris = [
        node.shareItemUri for node in get_share_object_response.data.getShareObject.get('items').nodes
    ]

    # When
    # re-applying share items from share object
    reapply_share_items_response = reapply_items_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share3_processed.shareUri,
        reapply_items_uris=reapply_items_uris,
    )
    assert 'UnauthorizedOperation' in reapply_share_items_response.errors[0].message


def test_verify_dataset_share_objects_request(db, client, user, group, share3_processed, share3_item_shared, dataset1):
    # Given
    # Existing share objects in dataset1
    list_dataset_shares = get_share_requests_to_me(
        client=client, user=user, group=group, filter={'datasets_uris': [dataset1.datasetUri]}
    )

    assert list_dataset_shares.data.getShareRequestsToMe.count == 2
    shareUris = [share.shareUri for share in list_dataset_shares.data.getShareRequestsToMe.nodes]
    assert len(shareUris)
    assert share3_processed.shareUri in shareUris

    # When
    # verifying all items from all share objects in dataset1
    list_dataset_share_objects_response = verify_dataset_share_objects(
        client=client, user=user, group=group, dataset_uri=dataset1.datasetUri, share_uris=shareUris
    )

    # Then share items of successfully shared items of each shareObject health Status changes to PendingVerify

    for shareUri in shareUris:
        get_share_object_response = get_share_object(
            client=client, user=user, group=group, shareUri=shareUri, filter={'isShared': True, 'isRevokable': True}
        )

        sharedItems = get_share_object_response.data.getShareObject.get('items').nodes
        for sharedItem in sharedItems:
            status = sharedItem['healthStatus']
            assert status == ShareItemHealthStatus.PendingVerify.value


def test_revoke_items_share_request(db, client, user2, group2, share3_processed, share3_item_shared):
    # Given
    # Existing share object in status Processed (-> fixture share3_processed)
    # with existing share item in status Share_Succeeded (-> fixture share3_item_shared)
    get_share_object_response = get_share_object(
        client=client, user=user2, group=group2, shareUri=share3_processed.shareUri, filter={'isShared': True}
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Processed.value

    shareItem = get_share_object_response.data.getShareObject.get('items').nodes[0]
    assert shareItem.shareItemUri == share3_item_shared.shareItemUri
    assert shareItem.status == ShareItemStatus.Share_Succeeded.value
    revoked_items_uris = [
        node.shareItemUri for node in get_share_object_response.data.getShareObject.get('items').nodes
    ]

    # When
    # revoking items from share object
    revoke_items_share_object_response = revoke_items_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share3_processed.shareUri,
        revoked_items_uris=revoked_items_uris,
    )
    # Then share object changes to status Rejected
    assert revoke_items_share_object_response.data.revokeItemsShareObject.status == ShareObjectStatus.Revoked.value

    # And shared item changes to status Revoke_Approved
    get_share_object_response = get_share_object(
        client=client, user=user2, group=group2, shareUri=share3_processed.shareUri, filter={'isShared': True}
    )
    sharedItem = get_share_object_response.data.getShareObject.get('items').nodes[0]
    status = sharedItem['status']
    assert status == ShareItemStatus.Revoke_Approved.value

    # Given the revoked share object is processed and the shared items
    # When approved share object is processed and the shared items successfully revoked (we re-use same function)
    _successfull_processing_for_share_object(db, share3_processed)

    get_share_object_response = get_share_object(
        client=client, user=user2, group=group2, shareUri=share3_processed.shareUri, filter={'isShared': True}
    )

    # Then share object status is changed to Processed
    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Processed.value

    # And share item status is changed to Revoke_Succeeded
    shareItem = get_share_object_response.data.getShareObject.get('items').nodes[0]
    assert shareItem.status == ShareItemStatus.Revoke_Succeeded.value


def test_delete_share_object(client, user2, group2, share4_draft):
    # Given
    # Existing share object in status Draft (-> fixture share4_draft) with no cleanup functions
    get_share_object_response = get_share_object(
        client=client, user=user2, group=group2, shareUri=share4_draft.shareUri, filter={'isShared': True}
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Draft.value

    # When deleting the share object
    delete_share_object_response = delete_share_object(
        client=client, user=user2, group=group2, shareUri=share4_draft.shareUri
    )
    # It is successfully deleted
    assert delete_share_object_response.data.deleteShareObject


def test_delete_share_object_remaining_items_error(
    client,
    user2,
    group2,
    share3_processed,
    share3_item_shared,
):
    # Given
    # Existing share object in status Processed (-> fixture share3_processed)
    # with existing share item in status Share_Succeeded (-> fixture share_item_shared)
    get_share_object_response = get_share_object(
        client=client, user=user2, group=group2, shareUri=share3_processed.shareUri, filter={'isShared': True}
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Processed.value

    shareItem = get_share_object_response.data.getShareObject.get('items').nodes[0]
    assert shareItem.shareItemUri == share3_item_shared.shareItemUri
    assert shareItem.status == ShareItemStatus.Share_Succeeded.value
    assert get_share_object_response.data.getShareObject.get('items').count == 1

    # When deleting the share object
    delete_share_object_response = delete_share_object(
        client=client, user=user2, group=group2, shareUri=share3_processed.shareUri
    )
    # Then we get an error of the type
    assert 'ShareItemsFound' in delete_share_object_response.errors[0].message


def test_cancel_share_extension_request(
    client,
    user2,
    group2,
    share3_item_expiration_share,
    share3_with_expiration_processed,
    mocker,
    dataset_with_expiration_2,
):
    # Given
    # Existing share object in status Processed (-> fixture share3_item_expiration_share)
    # with existing share item in status Share_Succeeded (-> fixture share3_with_expiration_processed)
    get_share_object_response = get_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share3_with_expiration_processed.shareUri,
        filter={'isShared': True},
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Processed.value

    # Submit a share extension request
    submit_share_extension(client, user2, group2, share3_with_expiration_processed.shareUri, 1)

    get_share_object_response = get_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share3_with_expiration_processed.shareUri,
        filter={'isShared': True},
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Submitted_For_Extension.value
    date_format = '%Y-%m-%d %H:%M:%S'
    share_expiration_date = datetime.strptime(
        get_share_object_response.data.getShareObject.requestedExpiryDate, date_format
    )
    assert (
        share_expiration_date.date()
        == ExpirationUtils.calculate_expiry_date(1, dataset_with_expiration_2.expirySetting).date()
    )

    cancel_share_extension(client, user2, group2, share3_with_expiration_processed.shareUri)

    get_share_object_response = get_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share3_with_expiration_processed.shareUri,
        filter={'isShared': True},
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Processed.value
    share_item = get_share_object_response.data.getShareObject.get('items').nodes[0]
    assert share_item.shareItemUri == share3_item_expiration_share.shareItemUri
    assert share_item.status == ShareItemStatus.Share_Succeeded.value
    assert get_share_object_response.data.getShareObject.get('items').count == 1


def test_cancel_share_extension_request_with_non_expiring_share_extension_requested(
    client,
    user2,
    group2,
    share3_item_expiration_share,
    share3_with_expiration_processed,
    mocker,
    dataset_with_expiration_2,
):
    # Given
    # Existing share object in status Processed (-> fixture share3_item_expiration_share)
    # with existing share item in status Share_Succeeded (-> fixture share3_with_expiration_processed)
    get_share_object_response = get_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share3_with_expiration_processed.shareUri,
        filter={'isShared': True},
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Processed.value

    current_expiration_date = get_share_object_response.data.getShareObject.expiryDate

    # Submit a share extension request
    submit_share_extension(client, user2, group2, share3_with_expiration_processed.shareUri, None, True)

    get_share_object_response = get_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share3_with_expiration_processed.shareUri,
        filter={'isShared': True},
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Submitted_For_Extension.value
    assert get_share_object_response.data.getShareObject.requestedExpiryDate == None
    assert get_share_object_response.data.getShareObject.nonExpirable == True

    cancel_share_extension(client, user2, group2, share3_with_expiration_processed.shareUri)

    get_share_object_response = get_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share3_with_expiration_processed.shareUri,
        filter={'isShared': True},
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Processed.value
    share_item = get_share_object_response.data.getShareObject.get('items').nodes[0]
    assert share_item.shareItemUri == share3_item_expiration_share.shareItemUri
    assert get_share_object_response.data.getShareObject.expiryDate == current_expiration_date
    assert get_share_object_response.data.getShareObject.nonExpirable == False
    assert share_item.status == ShareItemStatus.Share_Succeeded.value
    assert get_share_object_response.data.getShareObject.get('items').count == 1


def test_update_share_extension_period(
    client,
    user2,
    group2,
    share3_item_expiration_share,
    share3_with_expiration_processed,
    mocker,
    dataset_with_expiration_2,
):
    # Given
    # Existing share object in status Processed (-> fixture share3_item_expiration_share)
    # with existing share item in status Share_Succeeded (-> fixture share3_with_expiration_processed)
    get_share_object_response = get_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share3_with_expiration_processed.shareUri,
        filter={'isShared': True},
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Processed.value

    current_expiration_date = get_share_object_response.data.getShareObject.expiryDate
    shareExpirationPeriod = get_share_object_response.data.getShareObject.shareExpirationPerioud

    # Submit a share extension request
    submit_share_extension(client, user2, group2, share3_with_expiration_processed.shareUri, 3)
    get_share_object_response = get_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share3_with_expiration_processed.shareUri,
        filter={'isShared': True},
    )

    assert get_share_object_response.data.getShareObject.shareExpirationPeriod == 3

    update_share_extension_period(client, user2, group2, share3_with_expiration_processed.shareUri, 2)

    get_share_object_response = get_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share3_with_expiration_processed.shareUri,
        filter={'isShared': True},
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Submitted_For_Extension.value
    assert get_share_object_response.data.getShareObject.nonExpirable == False
    assert get_share_object_response.data.getShareObject.shareExpirationPeriod == 2

    cancel_share_extension(client, user2, group2, share3_with_expiration_processed.shareUri)


def test_update_share_extension_period_to_make_non_expiring(
    client,
    user2,
    group2,
    share3_item_expiration_share,
    share3_with_expiration_processed,
    mocker,
    dataset_with_expiration_2,
):
    # Given
    # Existing share object in status Processed (-> fixture share3_item_expiration_share)
    # with existing share item in status Share_Succeeded (-> fixture share3_with_expiration_processed)
    get_share_object_response = get_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share3_with_expiration_processed.shareUri,
        filter={'isShared': True},
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Processed.value

    current_expiration_date = get_share_object_response.data.getShareObject.expiryDate
    shareExpirationPeriod = get_share_object_response.data.getShareObject.shareExpirationPerioud

    # Submit a share extension request
    submit_share_extension(client, user2, group2, share3_with_expiration_processed.shareUri, 3)
    get_share_object_response = get_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share3_with_expiration_processed.shareUri,
        filter={'isShared': True},
    )

    assert get_share_object_response.data.getShareObject.shareExpirationPeriod == 3

    update_share_extension_period(client, user2, group2, share3_with_expiration_processed.shareUri, None, True)

    get_share_object_response = get_share_object(
        client=client,
        user=user2,
        group=group2,
        shareUri=share3_with_expiration_processed.shareUri,
        filter={'isShared': True},
    )

    assert get_share_object_response.data.getShareObject.status == ShareObjectStatus.Submitted_For_Extension.value
    assert get_share_object_response.data.getShareObject.nonExpirable == True
    assert get_share_object_response.data.getShareObject.shareExpirationPeriod == None

    cancel_share_extension(client, user2, group2, share3_with_expiration_processed.shareUri)


def _successfull_processing_for_share_object(db, share):
    with db.scoped_session() as session:
        print('Processing share with action ShareObjectActions.Start')
        share = ShareObjectRepository.get_share_by_uri(session, share.shareUri)

        share_items_states = ShareStatusRepository.get_share_items_states(session, share.shareUri)

        Share_SM = ShareObjectSM(share.status)
        new_share_state = Share_SM.run_transition(ShareObjectActions.Start.value)

        for item_state in share_items_states:
            Item_SM = ShareItemSM(item_state)
            new_state = Item_SM.run_transition(ShareObjectActions.Start.value)
            Item_SM.update_state(session, share.shareUri, new_state)

        Share_SM.update_state(session, share, new_share_state)

        print(
            'Processing share with action ShareObjectActions.Finish \
            and ShareItemActions.Success'
        )

        share = ShareObjectRepository.get_share_by_uri(session, share.shareUri)
        share_items_states = ShareStatusRepository.get_share_items_states(session, share.shareUri)

        new_share_state = Share_SM.run_transition(ShareObjectActions.Finish.value)

        for item_state in share_items_states:
            Item_SM = ShareItemSM(item_state)
            new_state = Item_SM.run_transition(ShareItemActions.Success.value)
            Item_SM.update_state(session, share.shareUri, new_state)

        Share_SM.update_state(session, share, new_share_state)

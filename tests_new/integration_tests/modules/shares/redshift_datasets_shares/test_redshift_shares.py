from assertpy import assert_that
import pytest
from integration_tests.errors import GqlError
from integration_tests.modules.shares.utils import check_share_ready
from integration_tests.modules.shares.queries import (
    approve_share_object,
    get_share_object,
    create_share_object,
    revoke_share_items,
)
from integration_tests.modules.shares.redshift_datasets_shares.conftest import (
    REDSHIFT_TEST_ROLE_NAME,
    REDSHIFT_PRINCIPAL_TYPE,
    REDSHIFT_ITEM_TYPE,
)


@pytest.mark.parametrize(
    'share_object_fixture_name',
    [
        'submitted_redshift_share_request_source_serverless',
        'submitted_redshift_share_request_source_cluster',
    ],
)
def test_creation_submission_redshift_share(share_object_fixture_name, request):
    share, share_item_uri = request.getfixturevalue(share_object_fixture_name)
    assert_that(share.status).is_equal_to('Draft')
    assert_that(share.shareUri).is_not_none()
    assert_that(share_item_uri).is_not_none()


@pytest.mark.dependency(name='serverless_share_approved')
def test_approve_redshift_source_serverless(client1, submitted_redshift_share_request_source_serverless):
    share, share_item_uri = submitted_redshift_share_request_source_serverless
    approve_share_object(client=client1, shareUri=share.shareUri)
    # Wait until share is processed
    check_share_ready(client=client1, shareUri=share.shareUri)
    updated_share = get_share_object(client1, share.shareUri, {'isShared': True})
    items = updated_share['items']
    assert_that(updated_share.status).is_equal_to('Processed')
    assert_that(items.count).is_equal_to(1)
    assert_that(items.nodes[0].shareItemUri).is_equal_to(share_item_uri)
    assert_that(items.nodes[0].itemType).is_equal_to(REDSHIFT_ITEM_TYPE)
    assert_that(items.nodes[0].status).is_equal_to('Share_Succeeded')


@pytest.mark.dependency(name='cluster_share_approved')
def test_approve_redshift_source_cluster(client5, submitted_redshift_share_request_source_cluster):
    share, share_item_uri = submitted_redshift_share_request_source_cluster
    approve_share_object(client=client5, shareUri=share.shareUri)
    # Wait until share is processed
    check_share_ready(client=client5, shareUri=share.shareUri)
    updated_share = get_share_object(client5, share.shareUri, {'isShared': True})
    items = updated_share['items']
    assert_that(updated_share.status).is_equal_to('Processed')
    assert_that(items.count).is_equal_to(1)
    assert_that(items.nodes[0].shareItemUri).is_equal_to(share_item_uri)
    assert_that(items.nodes[0].itemType).is_equal_to(REDSHIFT_ITEM_TYPE)
    assert_that(items.nodes[0].status).is_equal_to('Share_Succeeded')


@pytest.mark.dependency(depends=['serverless_share_approved'])
def test_revoke_redshift_source_serverless(client1, submitted_redshift_share_request_source_serverless):
    share, share_item_uri = submitted_redshift_share_request_source_serverless
    revoke_share_items(client=client1, shareUri=share.shareUri, shareItemUris=[share_item_uri])
    # Wait until share is processed
    check_share_ready(client=client1, shareUri=share.shareUri)
    updated_share = get_share_object(client1, share.shareUri, {'isShared': True})
    items = updated_share['items']
    assert_that(updated_share.status).is_equal_to('Processed')
    assert_that(items.count).is_equal_to(1)
    assert_that(items.nodes[0].status).is_equal_to('Revoke_Succeeded')


@pytest.mark.dependency(depends=['cluster_share_approved'])
def test_revoke_redshift_source_cluster(client1, submitted_redshift_share_request_source_cluster):
    share, share_item_uri = submitted_redshift_share_request_source_cluster
    revoke_share_items(client=client1, shareUri=share.shareUri, shareItemUris=[share_item_uri])
    # Wait until share is processed
    check_share_ready(client=client1, shareUri=share.shareUri)
    updated_share = get_share_object(client1, share.shareUri, {'isShared': True})
    items = updated_share['items']
    assert_that(updated_share.status).is_equal_to('Processed')
    assert_that(items.count).is_equal_to(1)
    assert_that(items.nodes[0].status).is_equal_to('Revoke_Succeeded')


def test_create_redshift_share_invalid_target_connection(
    client5, group5, session_cross_acc_env_1, session_connection_cluster_data_user, session_redshift_dataset_serverless
):
    # DATA_USER connections cannot be used as target connection for a share. Even if used by the connection owners.
    assert_that(create_share_object).raises(GqlError).when_called_with(
        client=client5,
        dataset_or_item_params={'datasetUri': session_redshift_dataset_serverless.datasetUri},
        environmentUri=session_cross_acc_env_1.environmentUri,
        groupUri=group5,
        principalRoleName=REDSHIFT_TEST_ROLE_NAME,
        principalId=session_connection_cluster_data_user.connectionUri,
        principalType=REDSHIFT_PRINCIPAL_TYPE,
        requestPurpose='Integration tests - Redshift shares',
        attachMissingPolicies=False,
        permissions=['Read'],
    ).contains(
        'UnauthorizedOperation',
        'CREATE_SHARE_REQUEST_WITH_CONNECTION',
        session_connection_cluster_data_user.connectionUri,
    )


def test_create_redshift_share_unauthorized_target_connection(
    client5, group5, session_env1, session_connection_serverless_admin, session_redshift_dataset_cluster
):
    assert_that(create_share_object).raises(GqlError).when_called_with(
        client=client5,
        dataset_or_item_params={'datasetUri': session_redshift_dataset_cluster.datasetUri},
        environmentUri=session_env1.environmentUri,
        groupUri=group5,
        principalRoleName=REDSHIFT_TEST_ROLE_NAME,
        principalId=session_connection_serverless_admin.connectionUri,
        principalType=REDSHIFT_PRINCIPAL_TYPE,
        requestPurpose='Integration tests - Redshift shares',
        attachMissingPolicies=False,
        permissions=['Read'],
    ).contains(
        'UnauthorizedOperation',
        'CREATE_SHARE_REQUEST_WITH_CONNECTION',
        session_connection_serverless_admin.connectionUri,
    )


def test_create_redshift_share_invalid_clusters():
    pass


def test_create_redshift_share_invalid_source_connection():
    pass


def test_create_redshift_share_invalid_redshift_role(
    client5, group5, session_cross_acc_env_1, session_connection_cluster_admin, session_redshift_dataset_serverless
):
    assert_that(create_share_object).raises(GqlError).when_called_with(
        client=client5,
        dataset_or_item_params={'datasetUri': session_redshift_dataset_serverless.datasetUri},
        environmentUri=session_cross_acc_env_1.environmentUri,
        groupUri=group5,
        principalRoleName='doesnotexist',
        principalId=session_connection_cluster_admin.connectionUri,
        principalType=REDSHIFT_PRINCIPAL_TYPE,
        requestPurpose='Integration tests - Redshift shares',
        attachMissingPolicies=False,
        permissions=['Read'],
    ).contains('PrincipalRoleNotFound', 'doesnotexist', session_connection_cluster_admin.name)


def test_approve_redshift_share_invalid_redshift_role():
    pass

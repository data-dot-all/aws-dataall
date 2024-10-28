from assertpy import assert_that
import pytest

from integration_tests.modules.worksheets.queries import (
    create_worksheet,
    delete_worksheet,
    get_worksheet,
    list_worksheets,
    run_athena_sql_query,
    update_worksheet,
    text_to_sql,
    analyze_text_document,
)
from integration_tests.errors import GqlError
from dataall.base.config import config


def test_create_worksheet(client1, worksheet1):
    assert_that(worksheet1.worksheetUri).is_length(8)
    assert_that(worksheet1.label).is_equal_to('worksheet1')


def test_delete_worksheet(client1, group1, session_id):
    ws = create_worksheet(client1, 'worksheetdelete', group1, tags=[session_id])
    assert_that(ws).contains_entry(label='worksheetdelete')
    response = delete_worksheet(client1, ws.worksheetUri)
    assert_that(response).is_equal_to(True)


def test_delete_worksheet_unauthorized(client2, worksheet1):
    assert_that(delete_worksheet).raises(GqlError).when_called_with(client2, worksheet1.worksheetUri).contains(
        'UnauthorizedOperation', 'DELETE_WORKSHEET'
    )


def test_get_worksheet(client1, group1, worksheet1):
    ws = get_worksheet(client1, worksheet1.worksheetUri)
    assert_that(ws).contains_entry(SamlAdminGroupName=group1, worksheetUri=worksheet1.worksheetUri)


def test_get_worksheet_unauthorized(client2, worksheet1):
    assert_that(get_worksheet).raises(GqlError).when_called_with(client2, worksheet1.worksheetUri).contains(
        'UnauthorizedOperation', 'GET_WORKSHEET'
    )


def test_list_worksheets(client1, worksheet1, session_id):
    response = list_worksheets(client1, term=session_id)
    assert_that(response.count).is_equal_to(1)


def test_list_worksheets_no_admin(client2, worksheet1, session_id):
    response = list_worksheets(client2, term=session_id)
    assert_that(response.count).is_equal_to(0)


def test_update_worksheet(client1, worksheet1):
    ws = update_worksheet(client1, worksheet1.worksheetUri, worksheet1.label, 'updated desc', worksheet1.tags)
    assert_that(ws).contains_entry(description='updated desc')


def test_update_worksheet_unauthorized(client2, worksheet1):
    assert_that(update_worksheet).raises(GqlError).when_called_with(
        client2, worksheet1.worksheetUri, worksheet1.label, 'updated desc', worksheet1.tags
    ).contains('UnauthorizedOperation', 'UPDATE_WORKSHEET')


def test_run_athena_sql_query(client1, worksheet1, persistent_env1):
    sql_query = 'SHOW DATABASES;'
    rows = run_athena_sql_query(
        client=client1,
        query=sql_query,
        environment_uri=persistent_env1.environmentUri,
        worksheet_uri=worksheet1.worksheetUri,
    ).rows
    assert_that(rows).is_not_empty()
    db_names = [r.cells[0].value for r in rows]
    assert_that(db_names).contains('default')


def test_run_athena_sql_query_unauthorized(client2, worksheet1, persistent_env1):
    sql_query = 'SHOW DATABASES;'
    assert_that(run_athena_sql_query).raises(GqlError).when_called_with(
        client2, sql_query, persistent_env1.environmentUri, worksheet1.worksheetUri
    ).contains('UnauthorizedOperation', 'RUN_ATHENA_QUERY')


@pytest.mark.skipif(
    not config.get_property('modules.worksheets.features.nlq.active'), reason='Feature Disabled by Config'
)
def test_text_to_sql(client1, worksheet1, persistent_env1):
    prompt = 'Write me a query to list the databases I have access to in Athena'
    response = text_to_sql(
        client=client1,
        prompt=prompt,
        environment_uri=persistent_env1.environmentUri,
        worksheet_uri=worksheet1.worksheetUri,
        database_name='',
        table_names=[],
    )
    # Results are nondeterministic - just asserting the response is not None
    assert_that(response).is_not_none()


@pytest.mark.skipif(
    not config.get_property('modules.worksheets.features.nlq.active'), reason='Feature Disabled by Config'
)
def test_text_to_sql_unauthorized(client2, worksheet1, persistent_env1):
    prompt = 'Write a query to access data in athena'
    assert_that(text_to_sql).raises(GqlError).when_called_with(
        client2, prompt, persistent_env1.environmentUri, worksheet1.worksheetUri, ''
    ).contains('UnauthorizedOperation', 'RUN_ATHENA_QUERY')


@pytest.mark.skipif(
    not config.get_property('modules.worksheets.features.nlq.active'), reason='Feature Disabled by Config'
)
def test_analyze_text_doc(client1, worksheet1, persistent_env1, persistent_s3_dataset1):
    prompt = 'Give me the first character of the first line of this text document'
    response = analyze_text_document(
        client=client1,
        prompt=prompt,
        environment_uri=persistent_env1.environmentUri,
        worksheet_uri=worksheet1.worksheetUri,
        dataset_uri=persistent_s3_dataset1.datasetUri,
        key='sessionFolderA/txt_sample.txt',
    )
    # Results are nondeterministic - just asserting the response is not None
    assert_that(response).is_not_none()


@pytest.mark.skipif(
    not config.get_property('modules.worksheets.features.nlq.active'), reason='Feature Disabled by Config'
)
def test_analyze_text_doc_invalid_object(client1, worksheet1, persistent_env1, persistent_s3_dataset1):
    prompt = 'Give me a summary of this text document'
    assert_that(analyze_text_document).raises(GqlError).when_called_with(
        client1,
        prompt,
        persistent_env1.environmentUri,
        worksheet1.worksheetUri,
        persistent_s3_dataset1.datasetUri,
        'some_file.js',
    ).contains('S3 Object Key', 'some_file.js', 'InvalidInput')


@pytest.mark.skipif(
    not config.get_property('modules.worksheets.features.nlq.active'), reason='Feature Disabled by Config'
)
def test_analyze_text_doc_unauthorized(client2, worksheet1, persistent_env1, persistent_s3_dataset1):
    prompt = 'Give me a summary of this text document'
    assert_that(analyze_text_document).raises(GqlError).when_called_with(
        client2,
        prompt,
        persistent_env1.environmentUri,
        worksheet1.worksheetUri,
        persistent_s3_dataset1.datasetUri,
        'file.txt',
    ).contains('UnauthorizedOperation', 'RUN_ATHENA_QUERY')

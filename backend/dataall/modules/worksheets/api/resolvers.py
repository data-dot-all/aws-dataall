from dataall.base.db import exceptions
from dataall.modules.worksheets.api.enums import WorksheetRole
from dataall.modules.worksheets.db.worksheet_models import Worksheet
from dataall.modules.worksheets.db.worksheet_repositories import WorksheetRepository
from dataall.modules.worksheets.services.worksheet_service import WorksheetService
from dataall.base.feature_toggle_checker import is_feature_enabled
from dataall.base.api.context import Context


def create_worksheet(context: Context, source, input: dict = None):
    if not input:
        raise exceptions.RequiredParameter(input)
    if not input.get('SamlAdminGroupName'):
        raise exceptions.RequiredParameter('groupUri')
    if not input.get('label'):
        raise exceptions.RequiredParameter('label')

    return WorksheetService.create_worksheet(
        data=input,
    )


def update_worksheet(context: Context, source, worksheetUri: str, input: dict = None):
    return WorksheetService.update_worksheet(uri=worksheetUri, data=input)


def get_worksheet(context: Context, source, worksheetUri: str):
    return WorksheetService.get_worksheet(
        uri=worksheetUri,
    )


def resolve_user_role(context: Context, source: Worksheet):
    if context.username and source.owner == context.username:
        return WorksheetRole.Creator.value
    elif context.groups and source.SamlAdminGroupName in context.groups:
        return WorksheetRole.Admin.value
    return WorksheetRole.NoPermission.value


def list_worksheets(context, source, filter: dict = None):
    if not filter:
        filter = {}
    with context.engine.scoped_session() as session:
        return WorksheetRepository.paginated_user_worksheets(
            session=session,
            username=context.username,
            groups=context.groups,
            uri=None,
            data=filter,
            check_perm=True,
        )


def run_sql_query(context: Context, source, environmentUri: str, worksheetUri: str, sqlQuery: str):
    return WorksheetService.run_sql_query(uri=environmentUri, worksheetUri=worksheetUri, sqlQuery=sqlQuery)


def delete_worksheet(context, source, worksheetUri: str):
    return WorksheetService.delete_worksheet(uri=worksheetUri)


@is_feature_enabled('modules.worksheets.features.nlq.active')
def text_to_sql(
    context: Context,
    source,
    environmentUri: str,
    worksheetUri: str,
    prompt: str,
    databaseName: str,
    tableNames: list,
):
    return WorksheetService.run_nlq(
        uri=environmentUri,
        prompt=prompt,
        worksheetUri=worksheetUri,
        db_name=databaseName,
        table_names=tableNames,
    )


@is_feature_enabled('modules.worksheets.features.nlq.active')
def analyze_text_genai(
    context,
    source,
    worksheetUri: str,
    environmentUri: str,
    prompt: str,
    datasetUri: str,
    key: str,
):
    return WorksheetService.analyze_text_genai(
        uri=environmentUri,
        worksheetUri=worksheetUri,
        prompt=prompt,
        datasetUri=datasetUri,
        key=key,
    )

from dataall.base.api.context import Context
from dataall.modules.catalog.db.glossary_models import TermLink
from dataall.base.db import paginate
from dataall.modules.s3_datasets.services.dataset_column_service import DatasetColumnService
from dataall.modules.s3_datasets.db.dataset_models import DatasetTableColumn, DatasetTable


def list_table_columns(
    context: Context,
    source: DatasetTable,
    tableUri: str = None,
    filter: dict = None,
):
    if source:
        tableUri = source.tableUri
    if not filter:
        filter = {}
    return DatasetColumnService.paginate_active_columns_for_table(uri=tableUri, filter=filter)


def sync_table_columns(context: Context, source, tableUri: str = None):
    if tableUri is None:
        return None
    return DatasetColumnService.sync_table_columns(table_uri=tableUri)


def resolve_terms(context, source: DatasetTableColumn, **kwargs):
    if not source:
        return None
    with context.engine.scoped_session() as session:
        q = session.query(TermLink).filter(TermLink.targetUri == source.columnUri)
    return paginate(q.order_by(TermLink.linkUri), page=1, page_size=15).to_dict()


def update_table_column(context: Context, source, columnUri: str = None, input: dict = None):
    if columnUri is None:
        return None

    if input is None:
        input = {}

    description = input.get('description', 'No description provided')
    return DatasetColumnService.update_table_column_description(column_uri=columnUri, description=description)


def batch_update_table_columns_description(context: Context, source, columns):
    if columns is None:
        return None
    return DatasetColumnService.batch_update_table_columns_description(columns=columns)

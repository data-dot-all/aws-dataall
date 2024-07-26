import logging

from dataall.base.db import exceptions
from dataall.modules.s3_datasets.db.dataset_models import DatasetTableDataFilter
from dataall.modules.s3_datasets.services.dataset_table_data_filter_enums import DataFilterType
from dataall.base.db import paginate

logger = logging.getLogger(__name__)


class DatasetTableDataFilterRepository:
    @staticmethod
    def build_data_filter(session, context, table_uri, data):
        return DatasetTableDataFilter(
            tableUri=table_uri,
            label=data.get('filterName'),
            filterType=data.get('filterType'),
            rowExpression=data.get('rowExpression') if data.get('filterType') == DataFilterType.ROW.value else None,
            includedCols=data.get('includedCols') if data.get('filterType') == DataFilterType.COLUMN.value else None,
            owner=context.username,
        )

    @staticmethod
    def save(session, data_filter: DatasetTableDataFilter):
        session.add(data_filter)
        session.commit()

    @staticmethod
    def delete(session, data_filter: DatasetTableDataFilter):
        session.delete(data_filter)
        return True

    @staticmethod
    def get_data_filter_by_uri(session, filter_uri):
        data_filter: DatasetTableDataFilter = session.query(DatasetTableDataFilter).get(filter_uri)
        if not data_filter:
            raise exceptions.ObjectNotFound('DatasetTableDataFilter', filter_uri)
        return data_filter

    @staticmethod
    def list_data_filters(session, table_uri):
        return session.query(DatasetTableDataFilter).filter(DatasetTableDataFilter.tableUri == table_uri).all()

    @staticmethod
    def paginated_data_filters(session, table_uri, data) -> dict:
        query = (
            session.query(DatasetTableDataFilter)
            .filter(DatasetTableDataFilter.tableUri == table_uri)
            .order_by(DatasetTableDataFilter.created.desc())
        )

        if data and data.get('term'):
            query = query.filter(DatasetTableDataFilter.name.ilike('%' + data.get('term') + '%'))

        return paginate(query=query, page_size=data.get('pageSize', 10), page=data.get('page', 1)).to_dict()

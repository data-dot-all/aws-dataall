import logging
from typing import List
from sqlalchemy import and_, or_
from sqlalchemy.orm import Query
from dataall.base.db import paginate
from dataall.base.db.exceptions import ObjectNotFound
from dataall.core.activity.db.activity_models import Activity
from dataall.modules.datasets_base.db.dataset_models import DatasetBase
from dataall.base.utils.naming_convention import (
    NamingConventionService,
    NamingConventionPattern,
)

logger = logging.getLogger(__name__)


class DatasetBaseRepository:
    """DAO layer for GENERIC Datasets"""

    @staticmethod
    def update_dataset_activity(session, dataset: DatasetBase, username):
        activity = Activity(
            action='dataset:update',
            label='dataset:update',
            owner=username,
            summary=f'{username} updated dataset {dataset.name}',
            targetUri=dataset.datasetUri,
            targetType='dataset',
        )
        session.add(activity)
        session.commit()

    @staticmethod
    def get_dataset_by_uri(session, dataset_uri) -> DatasetBase:
        dataset: DatasetBase = session.query(DatasetBase).get(dataset_uri)
        if not dataset:
            raise ObjectNotFound('Dataset', dataset_uri)
        return dataset


class DatasetListRepository:
    """DAO layer for Listing Datasets in Environments"""

    @staticmethod
    def paginated_all_user_datasets(session, username, groups, all_subqueries: List[Query], data=None) -> dict:
        return paginate(
            query=DatasetListRepository._query_all_user_datasets(session, username, groups, all_subqueries, data),
            page=data.get('page', 1),
            page_size=data.get('pageSize', 10),
        ).to_dict()

    @staticmethod
    def _query_all_user_datasets(session, username, groups, all_subqueries: List[Query], filter: dict = None) -> Query:
        query = session.query(DatasetBase).filter(
            or_(
                DatasetBase.owner == username,
                DatasetBase.SamlAdminGroupName.in_(groups),
                DatasetBase.stewards.in_(groups),
            )
        )
        if query.first() is not None:
            all_subqueries.append(query)
        if len(all_subqueries) == 1:
            query = all_subqueries[0]
        elif len(all_subqueries) > 1:
            query = all_subqueries[0].union(*all_subqueries[1:])

        if filter and filter.get('term'):
            term = filter['term']
            query = query.filter(
                or_(
                    DatasetBase.label.ilike('%' + term + '%'),
                    DatasetBase.description.ilike('%' + term + '%'),
                    DatasetBase.tags.contains(
                        f'{{{NamingConventionService(pattern=NamingConventionPattern.DEFAULT_SEARCH, target_label=term).sanitize()}}}'
                    ),
                )
            )
        return query.order_by(DatasetBase.label).distinct(DatasetBase.datasetUri, DatasetBase.label)

    @staticmethod
    def paginated_user_datasets(session, username, groups, data=None) -> dict:
        return paginate(
            query=DatasetListRepository._query_user_datasets(session, username, groups, data),
            page=data.get('page', 1),
            page_size=data.get('pageSize', 10),
        ).to_dict()

    @staticmethod
    def _query_user_datasets(session, username, groups, filter) -> Query:
        query = session.query(DatasetBase).filter(
            or_(
                DatasetBase.owner == username,
                DatasetBase.SamlAdminGroupName.in_(groups),
                DatasetBase.stewards.in_(groups),
            )
        )
        if filter and filter.get('term'):
            term = filter['term']
            query = query.filter(
                or_(
                    DatasetBase.label.ilike('%' + term + '%'),
                    DatasetBase.description.ilike('%' + term + '%'),
                    DatasetBase.tags.contains(
                        f'{{{NamingConventionService(pattern=NamingConventionPattern.DEFAULT_SEARCH, target_label=term).sanitize()}}}'
                    ),
                )
            )
        return query.order_by(DatasetBase.label).distinct(DatasetBase.datasetUri, DatasetBase.label)

    @staticmethod
    def paginated_environment_datasets(
        session,
        uri,
        data=None,
    ) -> dict:
        return paginate(
            query=DatasetListRepository.query_datasets(session, data, environmentUri=uri),
            page=data.get('page', 1),
            page_size=data.get('pageSize', 10),
        ).to_dict()

    @staticmethod
    def query_datasets(session, filter=None, organizationUri=None, environmentUri=None) -> Query:
        query = session.query(DatasetBase).filter(DatasetBase.deleted.is_(None))
        if organizationUri:
            query = query.filter(DatasetBase.organizationUri == organizationUri)
        if environmentUri:
            query = query.filter(DatasetBase.environmentUri == environmentUri)

        if filter and filter.get('term'):
            term = filter['term']
            query = query.filter(
                or_(
                    DatasetBase.label.ilike('%' + term + '%'),
                    DatasetBase.description.ilike('%' + term + '%'),
                    DatasetBase.tags.contains(
                        f'{{{NamingConventionService(pattern=NamingConventionPattern.DEFAULT_SEARCH, target_label=term).sanitize()}}}'
                    ),
                )
            )
        return query.order_by(DatasetBase.label)

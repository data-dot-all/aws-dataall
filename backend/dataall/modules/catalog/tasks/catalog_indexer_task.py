import logging
import os
import sys
from typing import List

from dataall.modules.catalog.indexers.catalog_indexer import CatalogIndexer
from dataall.modules.catalog.indexers.base_indexer import BaseIndexer
from dataall.base.db import get_engine
from dataall.base.loader import load_modules, ImportMode
from dataall.base.utils.alarm_service import AlarmService
from dataall.modules.notifications.services.admin_notifications import AdminNotificationService

log = logging.getLogger(__name__)


class CatalogIndexerTask:
    """
    This class is responsible for indexing objects in the catalog.
    """

    @classmethod
    def index_objects(cls, engine, with_deletes='False'):
        try:
            indexed_object_uris = []
            with engine.scoped_session() as session:
                for indexer in CatalogIndexer.all():
                    indexed_object_uris += indexer.index(session)

                log.info(f'Successfully indexed {len(indexed_object_uris)} objects')

                if with_deletes == 'True':
                    CatalogIndexerTask._delete_old_objects(indexed_object_uris)
                return len(indexed_object_uris)
        except Exception as e:
            error_log = f'Error occurred while indexing objects during the cataloging task. Exception: {e}'
            log.error(error_log)
            AlarmService().trigger_catalog_indexing_failure_alarm(error=str(e))
            AdminNotificationService().notify_admins_with_error_log(
                process_error='Exception occurred during cataloging task',
                error_logs=[error_log],
                process_name='Catalog Task',
            )
            raise e

    @classmethod
    def _delete_old_objects(cls, indexed_object_uris: List[str]) -> None:
        # Search for documents in opensearch without an ID in the indexed_object_uris list
        query = {'query': {'bool': {'must_not': {'terms': {'_id': indexed_object_uris}}}}}
        # Delete All "Outdated" Objects from Index
        docs = BaseIndexer.search_all(query, sort='_id')
        for doc in docs:
            BaseIndexer.delete_doc(doc_id=doc['_id'])
        log.info(f'Deleted {len(docs)} records')


if __name__ == '__main__':
    load_modules({ImportMode.CATALOG_INDEXER_TASK})
    ENVNAME = os.environ.get('envname', 'local')
    ENGINE = get_engine(envname=ENVNAME)
    with_deletes = os.environ.get('with_deletes', 'False')
    CatalogIndexerTask.index_objects(engine=ENGINE, with_deletes=with_deletes)

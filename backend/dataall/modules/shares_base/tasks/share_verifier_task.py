import logging
import os
import sys
from dataall.modules.shares_base.db.share_object_repositories import ShareObjectRepository
from dataall.modules.shares_base.db.share_object_models import ShareObject
from dataall.modules.shares_base.services.shares_enums import ShareItemStatus
from dataall.modules.shares_base.services.sharing_service import SharingService
from dataall.base.db import get_engine

from dataall.base.loader import load_modules, ImportMode

root = logging.getLogger()
root.setLevel(logging.INFO)
if not root.hasHandlers():
    root.addHandler(logging.StreamHandler(sys.stdout))
log = logging.getLogger(__name__)


def verify_shares(engine):
    """
    A method used by the scheduled ECS Task to run verify_shares() process against ALL shared items in ALL
    active share objects within data.all and update the health status of those shared items.
    """
    with engine.scoped_session() as session:
        processed_share_objects = []
        all_share_objects: [ShareObject] = ShareObjectRepository.list_all_active_share_objects(session)
        log.info(f'Found {len(all_share_objects)} share objects  verify ')
        share_object: ShareObject
        for share_object in all_share_objects:
            log.info(
                f'Verifying Share Items for Share Object with Requestor: {share_object.principalId} on Target Dataset: {share_object.datasetUri}'
            )
            processed_share_objects.append(share_object.shareUri)
            SharingService.verify_share(
                engine, share_uri=share_object.shareUri, status=ShareItemStatus.Share_Succeeded.value, healthStatus=None
            )
        return processed_share_objects


if __name__ == '__main__':
    load_modules(modes={ImportMode.SHARES_TASK})
    ENVNAME = os.environ.get('envname', 'local')
    ENGINE = get_engine(envname=ENVNAME)
    verify_shares(engine=ENGINE)

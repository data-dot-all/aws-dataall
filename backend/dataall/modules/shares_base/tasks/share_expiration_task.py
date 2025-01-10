import logging
import os
import sys
from datetime import datetime
from dataall.base.loader import load_modules, ImportMode
from dataall.base.db import get_engine
from dataall.modules.shares_base.db.share_object_repositories import ShareObjectRepository
from dataall.modules.shares_base.db.share_object_state_machines import ShareObjectSM, ShareItemSM
from dataall.modules.shares_base.db.share_state_machines_repositories import ShareStatusRepository
from dataall.modules.shares_base.services.share_notification_service import ShareNotificationService
from dataall.modules.datasets_base.db.dataset_repositories import DatasetBaseRepository
from dataall.modules.shares_base.services.shares_enums import ShareObjectActions
from dataall.modules.shares_base.services.sharing_service import SharingService

log = logging.getLogger(__name__)


def share_expiration_checker(engine):
    """
    Checks all the share objects which have expiryDate on them and then revokes or notifies users based on if its expired or not
    """
    with engine.scoped_session() as session:
        log.info('Starting share expiration task')
        shares = ShareObjectRepository.get_all_active_shares_with_expiration(session)
        log.info(f'Fetched {len(shares)} active shares with expiration')
        for share in shares:
            try:
                if share.expiryDate.date() < datetime.today().date():
                    log.info(f'Revoking share with uri: {share.shareUri} as it is expired')
                    # If a share is expired, pull all the share items which are in Share_Succeeded state
                    # Update status for each share item to Revoke_Approved and Revoke the share
                    share_items_to_revoke = ShareObjectRepository.get_all_share_items_in_share(
                        session, share.shareUri, ['Share_Succeeded']
                    )

                    # If the share doesn't have any share items in Share_Succeeded state then skip this share
                    if len(share_items_to_revoke) == 0:
                        continue

                    share_sm = ShareObjectSM(share.status)
                    new_share_state = share_sm.run_transition(ShareObjectActions.RevokeItems.value)

                    for item in share_items_to_revoke:
                        item_sm = ShareItemSM(item.status)
                        new_state = item_sm.run_transition(ShareObjectActions.RevokeItems.value)
                        item_sm.update_state_single_item(session, item, new_state)

                    share_sm.update_state(session, share, new_share_state)
                    SharingService.revoke_share(engine=engine, share_uri=share.shareUri)
                else:
                    log.info(f'Share with share uri: {share.shareUri} has not yet expired')
                    dataset = DatasetBaseRepository.get_dataset_by_uri(session, share.datasetUri)
                    if share.submittedForExtension:
                        log.info(
                            f'Sending notifications to the owners: {dataset.SamlAdminGroupName}, {dataset.stewards} as share extension requested for share with uri: {share.shareUri}'
                        )
                        ShareNotificationService(
                            session=session, dataset=dataset, share=share
                        ).notify_share_expiration_to_owners()
                    else:
                        log.info(
                            f'Sending notifications to the requesters with group: {share.groupUri} as share extension is not requested for share with uri: {share.shareUri}'
                        )
                        ShareNotificationService(
                            session=session, dataset=dataset, share=share
                        ).notify_share_expiration_to_requesters()
            except Exception as e:
                log.error(
                    f'Error occured while processing share expiration processing for share with URI: {share.shareUri} due to: {e}'
                )

if __name__ == '__main__':
    load_modules(modes={ImportMode.SHARES_TASK})
    ENVNAME = os.environ.get('envname', 'dkrcompose')
    ENGINE = get_engine(envname=ENVNAME)
    share_expiration_checker(engine=ENGINE)

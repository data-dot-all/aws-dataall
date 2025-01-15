import logging
import os
import sys
from datetime import datetime
from dataall.base.loader import load_modules, ImportMode
from dataall.base.db import get_engine
from dataall.modules.notifications.services.admin_notifications import AdminNotificationService
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
    task_exceptions = []
    try:
        with engine.scoped_session() as session:
            log.info('Starting share expiration task')
            shares = ShareObjectRepository.get_all_active_shares_with_expiration(session)
            log.info(f'Fetched {len(shares)} active shares with expiration')
            for share in shares:
                try:
                    if share.expiryDate.date() < datetime.today().date():
                        log.info(f'Revoking share with uri: {share.shareUri} as it is expired')
                        # Put all share items in revoke state and then revoke
                        share_items_to_revoke = ShareObjectRepository.get_all_share_items_in_share(
                            session, share.shareUri, ['Share_Succeeded']
                        )
                        item_uris = [share_item.shareItemUri for share_item in share_items_to_revoke]
                        revoked_items_states = ShareStatusRepository.get_share_items_states(
                            session, share.shareUri, item_uris
                        )

                        share_sm = ShareObjectSM(share.status)
                        new_share_state = share_sm.run_transition(ShareObjectActions.RevokeItems.value)

                        for item_state in revoked_items_states:
                            item_sm = ShareItemSM(item_state)
                            new_state = item_sm.run_transition(ShareObjectActions.RevokeItems.value)
                            for item in share_items_to_revoke:
                                if item.status == item_state:
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
                        f'Error occurred while processing share expiration processing for share with URI: {share.shareUri} due to: {e}'
                    )
                    task_exceptions.append(
                        f'Error occurred while processing share expiration processing for share with URI: {share.shareUri} due to: {e}'
                    )
    except Exception as e:
        log.error(f'Error occurred while processing share expiration due to : {e}')
        task_exceptions.append(f'Error occurred while processing share expiration due to: {e}')
    finally:
        if len(task_exceptions) > 0:
            AdminNotificationService().notify_admins_with_error_log(
                process_error='Error occurred while processing share expiration task',
                error_logs=task_exceptions,
                process_name='Share Expiration Task',
            )


if __name__ == '__main__':
    load_modules(modes={ImportMode.SHARES_TASK})
    ENVNAME = os.environ.get('envname', 'dkrcompose')
    ENGINE = get_engine(envname=ENVNAME)
    share_expiration_checker(engine=ENGINE)

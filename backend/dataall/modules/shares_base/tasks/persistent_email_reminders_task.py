import logging
import os
import sys
from dataall.base.loader import load_modules, ImportMode
from dataall.modules.notifications.services.admin_notifications import AdminNotificationService
from dataall.modules.shares_base.db.share_object_models import ShareObject
from dataall.base.db import get_engine
from dataall.modules.shares_base.db.share_object_repositories import ShareObjectRepository
from dataall.modules.shares_base.services.share_notification_service import ShareNotificationService
from dataall.modules.datasets_base.db.dataset_repositories import DatasetBaseRepository


log = logging.getLogger(__name__)


def persistent_email_reminders(engine):
    """
    A method used by the scheduled ECS Task to run persistent_email_reminder() process against ALL
    active share objects within data.all and send emails to all pending shares.
    """
    task_exceptions = []
    try:
        with engine.scoped_session() as session:
            log.info('Running Persistent Email Reminders Task')
            pending_shares = ShareObjectRepository.fetch_submitted_shares_with_notifications(session=session)
            log.info(f'Found {len(pending_shares)} pending shares')
            pending_share: ShareObject
            for pending_share in pending_shares:
                log.info(f'Sending Email Reminder for Share: {pending_share.shareUri}')
                share = ShareObjectRepository.get_share_by_uri(session, pending_share.shareUri)
                dataset = DatasetBaseRepository.get_dataset_by_uri(session, share.datasetUri)
                ShareNotificationService(
                    session=session, dataset=dataset, share=share
                ).notify_persistent_email_reminder(email_id=share.owner)
                log.info(f'Email reminder sent for share {share.shareUri}')
            log.info('Completed Persistent Email Reminders Task')
    except Exception as e:
        log.error(f'Error while running persistent email reminder task: {e}')
        task_exceptions.append(f'Error while running persistent email reminder task: {e}')
    finally:
        if len(task_exceptions) > 0:
            AdminNotificationService().notify_admins_with_error_log(
                process_name='Persistent Email Task',
                error_logs=task_exceptions,
                process_error='Error while running persistent email reminder task',
            )


if __name__ == '__main__':
    load_modules(modes={ImportMode.SHARES_TASK})
    ENVNAME = os.environ.get('envname', 'local')
    ENGINE = get_engine(envname=ENVNAME)
    persistent_email_reminders(engine=ENGINE)

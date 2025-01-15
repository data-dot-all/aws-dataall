import logging
import os
import sys

from dataall.modules.notifications.services.admin_notifications import AdminNotificationService
from dataall.modules.shares_base.db.share_object_repositories import ShareObjectRepository
from dataall.modules.shares_base.db.share_object_models import ShareObject
from dataall.modules.shares_base.services.shares_enums import ShareItemStatus
from dataall.modules.shares_base.services.sharing_service import SharingService
from dataall.core.stacks.aws.ecs import Ecs

from dataall.base.db import get_engine

from dataall.base.loader import load_modules, ImportMode

log = logging.getLogger(__name__)


def verify_shares(engine):
    """
    A method used by the scheduled ECS Task to run verify_shares() process against ALL shared items in ALL
    active share objects within data.all and update the health status of those shared items.
    """
    task_exceptions = []
    try:
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
                try:
                    SharingService.verify_share(
                        engine,
                        share_uri=share_object.shareUri,
                        status=ShareItemStatus.Share_Succeeded.value,
                        healthStatus=None,
                    )
                except Exception as e:
                    log.error(f'Error occurred while verifying share with uri: {share_object.shareUri} due to: {e}')
                    task_exceptions.append(
                        f'Error occurred while verifying share with uri: {share_object.shareUri} due to: {e}'
                    )
            return processed_share_objects
    except Exception as e:
        log.error(f'Error occurred while verifying shares task due to: {e}')
        task_exceptions.append(f'Error occurred while verifying shares task due to: {e}')
    finally:
        if len(task_exceptions) > 0:
            AdminNotificationService().notify_admins_with_error_log(
                process_error='Error occurred while verifying shares task',
                error_logs=task_exceptions,
                process_name='Share Verifier',
            )


def trigger_reapply_task():
    Ecs.run_ecs_task(
        task_definition_param='ecs/task_def_arn/share_reapplier',
        container_name_param='ecs/container/share_reapplier',
        context=[],
    )


if __name__ == '__main__':
    load_modules(modes={ImportMode.SHARES_TASK})
    ENVNAME = os.environ.get('envname', 'local')
    ENGINE = get_engine(envname=ENVNAME)
    processed_shares = verify_shares(engine=ENGINE)
    log.info(f'Finished verifying {len(processed_shares)} shares, triggering reapply...')
    trigger_reapply_task()

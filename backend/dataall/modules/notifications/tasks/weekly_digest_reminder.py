import logging
import os
from typing import List, Dict, Any, Tuple

from dataall.base.db import get_engine
from dataall.base.loader import load_modules, ImportMode
from dataall.core.environment.db.environment_models import Environment
from dataall.core.stacks.api.enums import StackStatus
from dataall.core.stacks.db.stack_repositories import StackRepository
from dataall.modules.datasets_base.db.dataset_models import DatasetBase
from dataall.modules.datasets_base.db.dataset_repositories import DatasetBaseRepository
from dataall.modules.notifications.services.admin_notifications import AdminNotificationService
from dataall.modules.notifications.services.ses_email_notification_service import SESEmailNotificationService
from dataall.modules.shares_base.db.share_object_models import ShareObject
from dataall.modules.shares_base.db.share_object_repositories import ShareObjectRepository
from dataall.modules.shares_base.services.shares_enums import ShareItemHealthStatus

log = logging.getLogger(__name__)

"""
A container for holding the resource ( e.g. dataset, share object, environment, etc ), receivers and health status ( resource_status ) for sending notifications
"""


class NotificationResource:
    def __init__(self, resource, resource_type: str, resource_status: str, receivers: List[str] = None):
        self.resource = resource
        self.resource_type = resource_type
        self.resource_status = resource_status
        self.receivers_list = set(receivers)


"""
Notification Bundle - Contains list of notification events for different types of resources ( dataset, shares, environment ) 
"""


class NotificationResourceBundle:
    def __init__(self):
        self.share_object_notifications: List[NotificationResource] = []
        self.dataset_object_notifications: List[NotificationResource] = []
        self.environment_object_notifications: List[NotificationResource] = []


def _get_pending_share_notifications(session):
    pending_shares = ShareObjectRepository.get_shares_with_statuses(session=session, status_list=['Submitted'])
    log.info(f'Found {len(pending_shares)} pending shares with share object status - Submitted')
    share_dataset_map: Dict[ShareObject, DatasetBase] = {
        share: DatasetBaseRepository.get_dataset_by_uri(session=session, dataset_uri=share.datasetUri)
        for share in pending_shares
    }
    return [
        NotificationResource(
            resource=share,
            resource_type='Share Object',
            resource_status=f'{share.status} - Pending Approval',
            receivers=[share_dataset_map[share].SamlAdminGroupName, share_dataset_map[share].stewards],
        )
        for share in share_dataset_map
    ]


def _get_unhealthy_share_notification(session):
    unhealthy_share_objects: List[ShareObject] = ShareObjectRepository.get_share_object_with_health_status(
        session=session, health_status_list=[ShareItemHealthStatus.Unhealthy.value]
    )
    log.info(f'Found {len(unhealthy_share_objects)} unhealthy share objects')
    return [
        NotificationResource(
            resource=share, resource_type='Share Object', resource_status='Unhealthy', receivers=[share.groupUri]
        )
        for share in unhealthy_share_objects
    ]


def _get_unhealthy_stack_by_type(session, target_uri: str, target_type: Any):
    unhealthy_stack_status: List[StackStatus] = [
        StackStatus.CREATE_FAILED.value,
        StackStatus.DELETE_FAILED.value,
        StackStatus.UPDATE_FAILED.value,
        StackStatus.UPDATE_ROLLBACK_FAILED.value,
        StackStatus.ROLLBACK_FAILED.value,
    ]
    resource_objects = session.query(target_type).all()
    unhealthy_stack_notification_resources: List[NotificationResource] = []
    log.info(f'Found {len(unhealthy_stack_notification_resources)} unhealthy {target_type}')

    # Check if stack associated with these datasets / environment exists
    # If yes, create a notification resource
    for resource in resource_objects:
        stack = StackRepository.find_stack_by_target_uri(
            session=session, target_uri=resource.__getattribute__(target_uri), statuses=unhealthy_stack_status
        )
        if stack is not None:
            notification_resource = NotificationResource(
                resource=resource,
                resource_type=target_type.__name__,
                resource_status=stack.status,
                receivers=_get_receivers_for_stack(resource=resource, target_type=target_type),
            )
            unhealthy_stack_notification_resources.append(notification_resource)

    return unhealthy_stack_notification_resources


def _get_receivers_for_stack(resource, target_type):
    if target_type.__name__ == 'Dataset':
        return [resource.SamlAdminGroupName, resource.stewards]
    if target_type.__name__ == 'Environment':
        return [resource.SamlGroupName]


"""
Function to create a map of {group name : resource bundle}, where each resource bundle contains dataset, share and environment notification lists. 
Iterated over all the notification ( NotificationResources ) and then segregate based on the dataset, shares & environment notifications and map the bundle to a team.
"""


def _map_groups_to_resource_bundles(list_of_notifications: List[NotificationResource], resource_bundle_type: str):
    for notification in list_of_notifications:
        # Get all the receivers groups
        notification_receiver_groups = notification.receivers_list
        for receiver_group_name in notification_receiver_groups:
            if receiver_group_name in group_name_to_resource_bundle_map:
                resource_bundle = group_name_to_resource_bundle_map.get(receiver_group_name)
                resource_bundle.__getattribute__(resource_bundle_type).append(notification)
            else:
                resource_bundle = NotificationResourceBundle()
                resource_bundle.__getattribute__(resource_bundle_type).append(notification)
                group_name_to_resource_bundle_map[receiver_group_name] = resource_bundle


def send_reminder_email(engine):
    task_exceptions = []
    resources_type_tuple: List[Tuple] = []
    try:
        with engine.scoped_session() as session:
            # Get all shares in submitted state
            pending_share_notification_resources = _get_pending_share_notifications(session=session)
            resources_type_tuple.append((pending_share_notification_resources, 'share_object_notifications'))
            # Todo : Check if distinct needed for the share object repository
            # Get all shares in unhealthy state
            unhealthy_share_objects_notification_resources = _get_unhealthy_share_notification(session=session)
            resources_type_tuple.append((unhealthy_share_objects_notification_resources, 'share_object_notifications'))
            # Get all the dataset which are in unhealthy state
            unhealthy_datasets_notification_resources = _get_unhealthy_stack_by_type(
                session=session, target_uri='datasetUri', target_type=DatasetBase
            )
            resources_type_tuple.append((unhealthy_datasets_notification_resources, 'dataset_object_notifications'))
            # Get all the environments which are in unhealthy state
            unhealthy_environment_notification_resources = _get_unhealthy_stack_by_type(
                session=session, target_uri='environmentUri', target_type=Environment
            )
            resources_type_tuple.append(
                (unhealthy_environment_notification_resources, 'environment_object_notifications')
            )

            # For each notification resource ( i.e. share notification, dataset notification, etc ),
            # function _map_groups_to_resource_bundles maps each team name : resource bundle
            for notification_resources, resource_bundle_type in resources_type_tuple:
                _map_groups_to_resource_bundles(
                    list_of_notifications=notification_resources, resource_bundle_type=resource_bundle_type
                )

            for group, resource_bundle in group_name_to_resource_bundle_map.items():
                email_body = _construct_email_body(resource_bundle)
                log.debug(email_body)
                subject = 'Attention Required | Data.all weekly digest'
                try:
                    SESEmailNotificationService.create_and_send_email_notifications(
                        subject=subject, msg=email_body, recipient_groups_list=[group]
                    )
                except Exception as e:
                    log.error(f'Error occurred in sending email while weekly reminder task due to: {e}')
                    task_exceptions.append(f'Error occurred in sending email while weekly reminder task due to: {e}')
    except Exception as e:
        log.error(f'Error occurred while running the weekly reminder task: {e}')
        task_exceptions.append(f'Error occurred while running the weekly reminder task: {e}')
    finally:
        if len(task_exceptions) > 0:
            log.info('Sending email notifications to the admin team')
            AdminNotificationService().notify_admins_with_error_log(
                process_error='Error occurred while running the weekly reminder task',
                error_logs=task_exceptions,
                process_name='Weekly reminder task',
            )


def _construct_email_body(resource_bundle: NotificationResourceBundle):
    msg_heading = """
    Dear Team, <br><br>
    
    This email contains data.all resources where you need to take some actions. For resources which are in unhealthy state we request you to take actions ASAP so as to minimize any disruptions.<br><br>
    
    <b>Helpful Tips:</b><br><br>
    For shares which are in unhealthy state, you can re-apply share by clicking on the "Reapply share" button <br>
    For environments and datasets which are in unhealthy state, you can go to the AWS account and check the stack associated with that environment/dataset and check the root cause of the stack. Once you address the root cause issue, you can click on "Update Stack" on the stack page of the data.all resource in the data.all UI <br><br><br> 
    """
    msg_content = """"""
    share_object_table_content = (
        _create_table_for_resource(resource_bundle.share_object_notifications, 'shareUri', '/console/shares/')
        if len(resource_bundle.share_object_notifications) > 0
        else ''
    )
    dataset_object_table_content = (
        _create_table_for_resource(resource_bundle.dataset_object_notifications, 'datasetUri', '/console/s3-datasets/')
        if len(resource_bundle.dataset_object_notifications) > 0
        else ''
    )
    environment_object_table_content = (
        _create_table_for_resource(
            resource_bundle.environment_object_notifications, 'environmentUri', '/console/environments/'
        )
        if len(resource_bundle.environment_object_notifications) > 0
        else ''
    )

    msg_content += (
        share_object_table_content + dataset_object_table_content + environment_object_table_content + '<br><br>'
    )

    msg_footer = """
    In case your stack(s) or share object(s) are still in unhealthy state after applying remedial measures, please contact data.all team. <br><br>
    Regards,<br>
    data.all Team
    """

    return msg_heading + msg_content + msg_footer


def _create_table_for_resource(list_of_resources, uri_attr, link_uri):
    table_heading = """
    <tr>    
        <th align='center'>
            Type
        </th>
         <th align='center'>
            Link
        </th>
        <th align='center'>
            Status
        </th>
    </tr>
    """
    table_body = """"""
    for resource in list_of_resources:
        table_body += f"""
            <tr>
                <td align='center'>
                    {resource.resource_type}
                </td>
                 <td align='center'>
                    {os.environ.get('frontend_domain_url', '') + link_uri + resource.resource.__getattribute__(uri_attr)}
                </td>
                <td align='center'>
                    {resource.resource_status}
                </td>
            </tr>
        """
    table = f"""
    <table border='1' style='border-collapse:collapse'>
        {table_heading}
        {table_body}
    </table>
    <br>
    <br>
    """

    return table


if __name__ == '__main__':
    log.info('Starting weekly reminders task')
    load_modules(modes={ImportMode.SHARES_TASK})
    ENVNAME = os.environ.get('envname', 'dkrcompose')
    ENGINE = get_engine(envname=ENVNAME)
    group_name_to_resource_bundle_map: Dict[str, NotificationResourceBundle] = {}
    send_reminder_email(engine=ENGINE)

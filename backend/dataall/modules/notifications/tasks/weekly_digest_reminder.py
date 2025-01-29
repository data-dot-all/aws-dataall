import logging
import os
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Set

from dataall.base.db import get_engine
from dataall.base.loader import load_modules, ImportMode
from dataall.base.services.service_provider_factory import ServiceProviderFactory
from dataall.core.environment.db.environment_models import Environment
from dataall.core.stacks.api.enums import StackStatus
from dataall.core.stacks.db.stack_repositories import StackRepository
from dataall.modules.datasets_base.db.dataset_models import DatasetBase
from dataall.modules.datasets_base.db.dataset_repositories import DatasetBaseRepository
from dataall.modules.notifications.services.admin_notifications import AdminNotificationService
from dataall.modules.notifications.services.ses_email_notification_service import SESEmailNotificationService
from dataall.modules.notifications.tasks.weekly_notification_enums import ResourceStatus, ResourceType
from dataall.modules.shares_base.db.share_object_models import ShareObject
from dataall.modules.shares_base.db.share_object_repositories import ShareObjectRepository
from dataall.modules.shares_base.services.shares_enums import ShareItemHealthStatus

log = logging.getLogger(__name__)

"""
A container for holding the resource ( e.g. dataset, share object, environment, etc ), receivers and health status ( resource_status ) for sending notifications
"""


@dataclass
class NotificationResource:
    resource: any
    resource_type: ResourceType
    resource_status: ResourceStatus
    receivers: Set[str] = field(default_factory=set)


"""
Notification Bundle - Contains list of notification events for different types of resources ( dataset, shares, environment ) 
"""


@dataclass
class NotificationResourceBundle:
    """
    A collection of notification resources, categorized by object type.
    """

    share_object_notifications: List[NotificationResource] = field(default_factory=list)
    dataset_object_notifications: List[NotificationResource] = field(default_factory=list)
    environment_object_notifications: List[NotificationResource] = field(default_factory=list)


"""
{user_email_id: Notification bundle}
Notification bundle consists of share, dataset & environment notification events ( NotificationResource )
"""
user_email_to_resource_bundle_map: Dict[str, NotificationResourceBundle] = {}


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
            resource_type=ResourceType.SHAREOBJECT,
            resource_status=ResourceStatus.PENDINGAPPROVAL,
            receivers={share_dataset_map[share].SamlAdminGroupName, share_dataset_map[share].stewards},
        )
        for share in share_dataset_map
    ]


def _get_unhealthy_share_notification(session):
    unhealthy_share_objects: List[ShareObject] = ShareObjectRepository.list_share_objects_with_item_health_status(
        session=session, health_status_list=[ShareItemHealthStatus.Unhealthy.value]
    )
    log.info(f'Found {len(unhealthy_share_objects)} unhealthy share objects')
    return [
        NotificationResource(
            resource=share,
            resource_type=ResourceType.SHAREOBJECT,
            resource_status=ResourceStatus.UNHEALTHY,
            receivers={share.groupUri},
        )
        for share in unhealthy_share_objects
    ]


"""
Function to fetch all the unhealthy stacks for a target type
target_uri : any unique uri representing a resource ( datasetUri, environmentUri, etc )
target_type: any db model representing a data.all resource ( e.g. DatasetBase, Environment, etc ) 
"""


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
                resource_type=_get_resource_type_for_stack(target_type),
                resource_status=_get_resource_status_for_stack(stack.status),
                receivers=_get_receivers_for_stack(resource=resource, target_type=target_type),
            )
            unhealthy_stack_notification_resources.append(notification_resource)

    return unhealthy_stack_notification_resources


def _get_receivers_for_stack(resource, target_type):
    """Returns team(s) / group(s) as per the target_type model (DatasetBase, Environment, etc )"""
    if target_type.__name__ == 'Dataset':
        return {resource.SamlAdminGroupName, resource.stewards}
    if target_type.__name__ == 'Environment':
        return {resource.SamlGroupName}


def _get_resource_type_for_stack(target_type):
    """Returns ResourceType as per the target_type model (DatasetBase, Environment, etc )"""
    if target_type.__name__ == 'Dataset':
        return ResourceType.DATASET
    if target_type.__name__ == 'Environment':
        return ResourceType.ENVIRONMENT


def _get_resource_status_for_stack(stack_status):
    """Returns the enum associated with the stack's status.
    Iterates over all enums of ResourceStatus and returns enums with matching values with the stack status
    """

    for resource_status in ResourceStatus:
        if resource_status.value == stack_status:
            return resource_status


"""
Function to create a map of {user_email_id : resource bundle}, where each resource bundle contains dataset, share and environment notification lists. 
Iterated over all the notification ( NotificationResources ) and then segregate based on the dataset, shares & environment notifications and map the bundle to a user.
"""


def _map_email_ids_to_resource_bundles(list_of_notifications: List[NotificationResource], resource_bundle_type: str):
    for notification in list_of_notifications:
        notification_receiver_groups = notification.receivers
        service_provider = ServiceProviderFactory.get_service_provider_instance()

        email_ids: Set = set()
        for group in notification_receiver_groups:
            email_ids.update(service_provider.get_user_emailids_from_group(role_name=group))

        for email_id in email_ids:
            if email_id in user_email_to_resource_bundle_map:
                resource_bundle = user_email_to_resource_bundle_map.get(email_id)
                resource_bundle.__getattribute__(resource_bundle_type).append(notification)
            else:
                resource_bundle = NotificationResourceBundle()
                resource_bundle.__getattribute__(resource_bundle_type).append(notification)
                user_email_to_resource_bundle_map[email_id] = resource_bundle


def send_reminder_email(engine):
    task_exceptions = []
    resources_type_tuple: List[Tuple] = []
    try:
        with engine.scoped_session() as session:
            # Get all shares in submitted state
            pending_share_notification_resources = _get_pending_share_notifications(session=session)
            resources_type_tuple.append((pending_share_notification_resources, 'share_object_notifications'))

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
                _map_email_ids_to_resource_bundles(
                    list_of_notifications=notification_resources, resource_bundle_type=resource_bundle_type
                )

            for email_id, resource_bundle in user_email_to_resource_bundle_map.items():
                email_body = _construct_email_body(resource_bundle)
                log.debug(f'Sending email to user: {email_id} with email content: {email_body}')
                subject = 'Attention Required | Data.all weekly digest'
                try:
                    SESEmailNotificationService.create_and_send_email_notifications(
                        subject=subject, msg=email_body, recipient_email_ids=[email_id]
                    )
                except Exception as e:
                    err_msg = f'Error occurred in sending email while weekly reminder task due to: {e}'
                    log.exception(err_msg)
                    task_exceptions.append(err_msg)
    except Exception as e:
        err_msg = f'Error occurred while running the weekly reminder task: {e}'
        log.error(err_msg)
        task_exceptions.append(err_msg)
        raise e
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
                    {resource.resource_type.value}
                </td>
                 <td align='center'>
                    {os.environ.get('frontend_domain_url', '') + link_uri + resource.resource.__getattribute__(uri_attr)}
                </td>
                <td align='center'>
                    {resource.resource_status.value}
                </td>
            </tr>
        """
    table = f"""
    <table border='1' style='border-collapse:collapse; width: 70%;'>
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
    send_reminder_email(engine=ENGINE)

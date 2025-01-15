import logging
import enum
import os
from typing import List

from dataall.base.config import config
from dataall.core.tasks.db.task_models import Task
from dataall.core.tasks.service_handlers import Worker
from dataall.modules.shares_base.db.share_object_models import ShareObject
from dataall.base.context import get_context
from dataall.modules.shares_base.services.shares_enums import ShareObjectStatus
from dataall.modules.notifications.db.notification_repositories import NotificationRepository
from dataall.modules.notifications.services.ses_email_notification_service import SESEmailNotificationService
from dataall.modules.datasets_base.db.dataset_models import DatasetBase

log = logging.getLogger(__name__)


class DataSharingNotificationType(enum.Enum):
    SHARE_OBJECT_SUBMITTED = 'SHARE_OBJECT_SUBMITTED'
    SHARE_ITEM_REQUEST = 'SHARE_ITEM_REQUEST'
    SHARE_OBJECT_EXTENSION_SUBMITTED = 'SHARE_OBJECT_EXTENSION_SUBMITTED'
    SHARE_OBJECT_APPROVED = 'SHARE_OBJECT_APPROVED'
    SHARE_OBJECT_EXTENDED = 'SHARE_OBJECT_EXTENDED'
    SHARE_OBJECT_EXTENSION_REJECTED = 'SHARE_OBJECT_EXTENSION_REJECTED'
    SHARE_OBJECT_REJECTED = 'SHARE_OBJECT_REJECTED'
    SHARE_OBJECT_PENDING_APPROVAL = 'SHARE_OBJECT_PENDING_APPROVAL'
    SHARE_OBJECT_FAILED = 'SHARE_OBJECT_FAILED'
    SHARE_OBJECT_UNHEALTHY = 'SHARE_OBJECT_UNHEALTHY'
    SHARE_OBJECT_HEALTHY = 'SHARE_OBJECT_HEALTHY'
    DATASET_VERSION = 'DATASET_VERSION'


class ShareNotificationService:
    """
    Notifications sent to:
        - dataset.SamlAdminGroupName
        - dataset.stewards
        - share.groupUri
    Emails sent to:
        - dataset.SamlAdminGroupName
        - dataset.stewards
        - share.owner (person that opened the request) OR share.groupUri (if group_notifications=true)
    """

    def __init__(self, session, dataset: DatasetBase, share: ShareObject):
        self.dataset = dataset
        self.share = share
        self.session = session
        self.notification_target_users = self._get_share_object_targeted_users()

    def notify_share_object_submission(self, email_id: str):
        share_link_text = ''
        if os.environ.get('frontend_domain_url'):
            share_link_text = f'<br><br> Please visit data.all <a href="{os.environ.get("frontend_domain_url")}/console/shares/{self.share.shareUri}">share link </a> to take action or view more details'
        msg = f'User {email_id} SUBMITTED share request for dataset {self.dataset.label} for principal {self.share.principalRoleName}'
        subject = f'Data.all | Share Request Submitted for {self.dataset.label}'
        email_notification_msg = msg + share_link_text

        notifications = self.register_notifications(
            notification_type=DataSharingNotificationType.SHARE_OBJECT_SUBMITTED.value, msg=msg
        )

        self._create_notification_task(subject=subject, msg=email_notification_msg)
        return notifications

    def notify_share_object_extension_submission(self, email_id: str):
        share_link_text = ''
        if os.environ.get('frontend_domain_url'):
            share_link_text = f'<br><br> Please visit data.all <a href="{os.environ.get("frontend_domain_url")}/console/shares/{self.share.shareUri}">share link </a> to take action or view more details'
        msg = f'User {email_id} SUBMITTED share extension request for dataset {self.dataset.label} for principal {self.share.principalRoleName}'
        subject = f'Data.all | Share Extension Request Submitted for {self.dataset.label}'
        email_notification_msg = msg + share_link_text

        notifications = self.register_notifications(
            notification_type=DataSharingNotificationType.SHARE_OBJECT_EXTENSION_SUBMITTED.value, msg=msg
        )

        self._create_notification_task(subject=subject, msg=email_notification_msg)
        return notifications

    def notify_persistent_email_reminder(self, email_id: str):
        share_link_text = ''
        if os.environ.get('frontend_domain_url'):
            share_link_text = (
                f'<br><br>Please visit data.all <a href="{os.environ.get("frontend_domain_url")}'
                f'/console/shares/{self.share.shareUri}">share link</a> '
                f'to review and take appropriate action or view more details.'
            )

        msg_intro = f"""Dear User,
        This is a reminder that a share request for the dataset "{self.dataset.label}" submitted by {email_id} 
        on behalf of principal "{self.share.principalRoleName}" is still pending and has not been addressed.
        """

        msg_end = """Your prompt attention in this matter is greatly appreciated.
        <br><br>Best regards,
        <br>The Data.all Team
        """

        subject = f'URGENT REMINDER: Data.all | Action Required on Pending Share Request for {self.dataset.label}'
        email_notification_msg = msg_intro + share_link_text + msg_end

        notifications = self.register_notifications(
            notification_type=DataSharingNotificationType.SHARE_OBJECT_SUBMITTED.value,
            msg=msg_intro.replace('<br>', '').replace('<b>', '').replace('</b>', ''),
        )

        SESEmailNotificationService.create_and_send_email_notifications(
            subject=subject,
            msg=email_notification_msg,
            recipient_groups_list=[self.dataset.SamlAdminGroupName, self.dataset.stewards],
        )
        return notifications

    def notify_share_object_approval(self, email_id: str):
        share_link_text = ''
        if os.environ.get('frontend_domain_url'):
            share_link_text = (
                f'<br><br> Please visit data.all <a href="{os.environ.get("frontend_domain_url")}'
                f'/console/shares/{self.share.shareUri}">share link </a> '
                f'to take action or view more details'
            )
        msg = (
            f'User {email_id} APPROVED share request for dataset {self.dataset.label} '
            f'for principal {self.share.principalRoleName}'
        )
        subject = f'Data.all | Share Request Approved for {self.dataset.label}'
        email_notification_msg = msg + share_link_text

        notifications = self.register_notifications(
            notification_type=DataSharingNotificationType.SHARE_OBJECT_APPROVED.value, msg=msg
        )

        self._create_notification_task(subject=subject, msg=email_notification_msg)
        return notifications

    def notify_share_object_extension_approval(self, email_id: str):
        share_link_text = ''
        if os.environ.get('frontend_domain_url'):
            share_link_text = (
                f'<br><br> Please visit data.all <a href="{os.environ.get("frontend_domain_url")}'
                f'/console/shares/{self.share.shareUri}">share link </a> '
                f'to take action or view more details'
            )
        msg = (
            f'User {email_id} APPROVED share extension request for dataset {self.dataset.label} '
            f'for principal {self.share.principalRoleName}'
        )
        subject = f'Data.all | Share Extension Request Approved for {self.dataset.label}'
        email_notification_msg = msg + share_link_text

        notifications = self.register_notifications(
            notification_type=DataSharingNotificationType.SHARE_OBJECT_EXTENDED.value, msg=msg
        )

        self._create_notification_task(subject=subject, msg=email_notification_msg)
        return notifications

    def notify_share_object_rejection(self, email_id: str):
        share_link_text = ''
        if os.environ.get('frontend_domain_url'):
            share_link_text = f'<br><br> Please visit data.all <a href="{os.environ.get("frontend_domain_url")}/console/shares/{self.share.shareUri}">share link </a> to take action or view more details'
        if self.share.status == ShareObjectStatus.Rejected.value:
            msg = f'User {email_id} REJECTED share request for dataset {self.dataset.label} for principal {self.share.principalRoleName}'
            subject = f'Data.all | Share Request Rejected for {self.dataset.label}'
        elif self.share.status == ShareObjectStatus.Revoked.value:
            msg = f'User {email_id} REVOKED share request for dataset {self.dataset.label} for principal {self.share.principalRoleName}'
            subject = f'Data.all | Share Request Revoked for {self.dataset.label}'
        else:
            msg = f'User {email_id} REJECTED/REVOKED share request for dataset {self.dataset.label} for principal {self.share.principalRoleName}'
            subject = f'Data.all | Share Request Rejected / Revoked for {self.dataset.label}'
        email_notification_msg = msg + share_link_text

        notifications = self.register_notifications(
            notification_type=DataSharingNotificationType.SHARE_OBJECT_REJECTED.value, msg=msg
        )

        self._create_notification_task(subject=subject, msg=email_notification_msg)
        return notifications

    def notify_share_object_extension_rejection(self, email_id: str):
        share_link_text = ''
        if os.environ.get('frontend_domain_url'):
            share_link_text = f'<br><br> Please visit data.all <a href="{os.environ.get("frontend_domain_url")}/console/shares/{self.share.shareUri}">share link </a> to take action or view more details'
        msg = f'User {email_id} REJECTED share extension request for dataset {self.dataset.label} on principal {self.share.principalRoleName}'
        subject = f'Data.all | Share Extension Request Rejected for {self.dataset.label}'
        email_notification_msg = msg + share_link_text

        notifications = self.register_notifications(
            notification_type=DataSharingNotificationType.SHARE_OBJECT_EXTENSION_REJECTED.value, msg=msg
        )

        self._create_notification_task(subject=subject, msg=email_notification_msg)
        return notifications

    def notify_share_expiration_to_owners(self):
        share_link_text = ''
        if os.environ.get('frontend_domain_url'):
            share_link_text = (
                f'<br><br>Please visit data.all <a href="{os.environ.get("frontend_domain_url")}'
                f'/console/shares/{self.share.shareUri}">share link</a> '
                f'to review and take actions on the share extension request'
            )

        msg_intro = f"""Dear User, <br>
                This is a reminder that there is a <b>pending share extension</b> request on dataset "{self.dataset.label}".
                <br><br><b>Note: If you fail to take action on the share request and if it expires, the share item will be revoked which will result in loss of access for the requesters.</b>
                """

        msg_end = """Your prompt attention in this matter is greatly appreciated.
              <br><br>Best regards,
              <br>The Data.all Team
              """

        subject = (
            f'URGENT REMINDER: Data.all | Action Required on Pending Share Extension Request for {self.dataset.label}'
        )
        email_notification_msg = msg_intro + share_link_text + msg_end

        notifications = self.register_notifications(
            notification_type=DataSharingNotificationType.SHARE_OBJECT_EXTENDED.value,
            msg=msg_intro.replace('<br>', '').replace('<b>', '').replace('</b>', ''),
        )

        SESEmailNotificationService.create_and_send_email_notifications(
            subject=subject,
            msg=email_notification_msg,
            recipient_groups_list=[self.dataset.SamlAdminGroupName, self.dataset.stewards],
        )
        return notifications

    def notify_share_expiration_to_requesters(self):
        share_link_text = ''
        if os.environ.get('frontend_domain_url'):
            share_link_text = (
                f'<br><br>Please visit data.all <a href="{os.environ.get("frontend_domain_url")}'
                f'/console/shares/{self.share.shareUri}">share link</a> '
                f'to review and create a share extension request'
            )

        msg_intro = f"""Dear User, <br>
                   This is a reminder that your share request for the dataset "{self.dataset.label}" will get expired on {self.share.expiryDate.date().strftime("%B %d, %Y")}. Please request a share extension request before it to have continued access to the dataset.
                   <br><br><b>Note: If you fail request for an extension and if it expires, the share item will be revoked which will result in loss of access to the dataset.</b>
                   """

        msg_end = """Your prompt attention in this matter is greatly appreciated.
                 <br><br>Best regards,
                 <br>The Data.all Team
                 """

        subject = 'ACTION REQUIRED: Data.all | Share Expiration Approaching Soon'
        email_notification_msg = msg_intro + share_link_text + msg_end

        notifications = self.register_notifications(
            notification_type=DataSharingNotificationType.SHARE_OBJECT_EXTENDED.value,
            msg=msg_intro.replace('<br>', '').replace('<b>', '').replace('</b>', ''),
        )

        SESEmailNotificationService.create_and_send_email_notifications(
            subject=subject, msg=email_notification_msg, recipient_groups_list=[self.share.groupUri]
        )
        return notifications

    def notify_share_object_failed(self):
        share_link_text = ''
        if os.environ.get('frontend_domain_url'):
            share_link_text = (
                f'<br><br> Please visit data.all <a href="{os.environ.get("frontend_domain_url")}'
                f'/console/shares/{self.share.shareUri}">share link </a> '
                f'to take action or view more details'
            )
        msg = (
            f'Share request made for dataset: <b>{self.dataset.label}</b> with requestor principal: <b>{self.share.principalRoleName}</b> failed. <br><br>'
            f'Please reach out to the data.all team for troubleshooting problems with this share'
        )
        msg_footer = """
        Regards,<br>
        data.all team
        """
        subject = f'Data.all | Attention Required | Share failed for {self.dataset.label}'
        email_notification_msg = msg + share_link_text + '<br><br>' + msg_footer

        notifications = self.register_notifications(
            notification_type=DataSharingNotificationType.SHARE_OBJECT_FAILED.value, msg=msg
        )

        SESEmailNotificationService.create_and_send_email_notifications(
            subject=subject,
            msg=email_notification_msg,
            recipient_groups_list=[self.share.groupUri, self.dataset.SamlAdminGroupName, self.dataset.stewards],
        )

        return notifications

    # Send notification when any of the share item gets into unhealthy state
    def notify_share_object_items_unhealthy(self):
        share_link_text = ''
        if os.environ.get('frontend_domain_url'):
            share_link_text = (
                f'<br><br> Please visit data.all <a href="{os.environ.get("frontend_domain_url")}'
                f'/console/shares/{self.share.shareUri}">share link </a> '
                f'to take action or view more details'
            )
        msg = (
            f'Hello Team, <br>'
            f'Your share with share uri: <b>{self.share.shareUri}</b> has one or more unhealthy share items. <br><br>'
            f"Once you visit your share link you can click on the Reapply button and this should correct your share and get it into an healthy state.<b> If this doesn't get your share in healthy state then please get in touch with data.all admins for your share."
        )
        msg_footer = """
                Regards,<br>
                data.all team
                """
        subject = f'Data.all | Attention Required | Share for {self.dataset.label} dataset in unhealthy state'
        email_notification_msg = msg + share_link_text + '<br><br>' + msg_footer

        notifications = self.register_notifications(
            notification_type=DataSharingNotificationType.SHARE_OBJECT_UNHEALTHY.value,
            msg=msg,
            to_recipients=[self.share.groupUri],
        )

        SESEmailNotificationService.create_and_send_email_notifications(
            subject=subject, msg=email_notification_msg, recipient_groups_list=[self.share.groupUri]
        )

        return notifications

    # Send notifications when a share gets into healthy state.
    # These notifications are sent when a share which was initially unhealthy goes into healthy state
    def notify_share_object_items_healthy(self):
        share_link_text = ''
        if os.environ.get('frontend_domain_url'):
            share_link_text = (
                f'<br><br> Please visit data.all <a href="{os.environ.get("frontend_domain_url")}'
                f'/console/shares/{self.share.shareUri}">share link </a> '
                f'to take action or view more details'
            )
        msg = (
            f'Hello Team, <br>'
            f'Your share with share uri: <b>{self.share.shareUri}</b> is now in healthy state after reapplying the share.<br>'
        )
        msg_footer = """
                Regards,<br>
                data.all team
                """
        subject = f'Data.all | Share for {self.dataset.label} dataset now in healthy state'
        email_notification_msg = msg + share_link_text + '<br><br>' + msg_footer

        notifications = self.register_notifications(
            notification_type=DataSharingNotificationType.SHARE_OBJECT_HEALTHY.value,
            msg=msg,
            to_recipients=[self.share.groupUri],
        )

        SESEmailNotificationService.create_and_send_email_notifications(
            subject=subject, msg=email_notification_msg, recipient_groups_list=[self.share.groupUri]
        )
        return notifications

    def _get_share_object_targeted_users(self):
        targeted_users = list()
        targeted_users.append(self.dataset.SamlAdminGroupName)
        if self.dataset.stewards != self.dataset.SamlAdminGroupName:
            targeted_users.append(self.dataset.stewards)
        targeted_users.append(self.share.groupUri)
        return targeted_users

    def register_notifications(self, notification_type, msg, to_recipients: List[any] = None):
        """
        Notifications sent to:
            if to_recipients is None
            - dataset.SamlAdminGroupName
            - dataset.stewards
            - share.groupUri
            else
            - to_recipients
        """
        if not to_recipients:
            to_recipients = self.notification_target_users
        notifications = []
        for recipient in to_recipients:
            log.info(f'Creating notification for {recipient}, msg {msg}')
            notifications.append(
                NotificationRepository.create_notification(
                    session=self.session,
                    recipient=recipient,
                    notification_type=notification_type,
                    target_uri=f'{self.share.shareUri}|{self.dataset.datasetUri}',
                    message=msg,
                )
            )
        self.session.add_all(notifications)
        return notifications

    def _create_notification_task(self, subject, msg):
        """
        At the moment just for notification_config_type = email, but designed for additional notification types
        Emails sent to:
            - dataset.SamlAdminGroupName
            - dataset.stewards
            - share.owner (person that opened the request) OR share.groupUri (if group_notifications=true)
        """
        share_notification_config = config.get_property(
            'modules.datasets_base.features.share_notifications', default=None
        )
        if share_notification_config:
            for share_notification_config_type in share_notification_config.keys():
                n_config = share_notification_config[share_notification_config_type]
                if n_config.get('active', False) == True:
                    params = n_config.get('parameters', {})
                    notification_recipient_groups_list = [self.dataset.SamlAdminGroupName, self.dataset.stewards]
                    notification_recipient_email_ids = []

                    if share_notification_config_type == 'email':
                        if params.get('group_notifications', False) == True:
                            notification_recipient_groups_list.append(self.share.groupUri)
                        else:
                            notification_recipient_email_ids = [self.share.owner]

                        notification_task: Task = Task(
                            action='notification.service',
                            targetUri=self.share.shareUri,
                            payload={
                                'notificationType': share_notification_config_type,
                                'subject': subject,
                                'message': msg,
                                'recipientGroupsList': notification_recipient_groups_list,
                                'recipientEmailList': notification_recipient_email_ids,
                            },
                        )
                        self.session.add(notification_task)
                        self.session.commit()

                        Worker.queue(engine=get_context().db_engine, task_ids=[notification_task.taskUri])
                else:
                    log.info(f'Notification type : {share_notification_config_type} is not active')
        else:
            log.info('Notifications are not active')

# Email Notification Provider implements the email notification service abstract method
import logging

from dataall.base.aws.cognito import Cognito
from dataall.base.aws.ses import Ses
from dataall.modules.notifications.services.base_email_notification_service import BaseEmailNotificationService

log = logging.getLogger(__name__)


class SESEmailNotificationService(BaseEmailNotificationService):

    def __init__(self, email_client, recipient_group_list, recipient_email_list) -> None:
        super().__init__()
        self.email_client = email_client
        self.recipient_group_list = recipient_group_list
        self.recipient_email_list = recipient_email_list

    # Implementation
    def send_email(self, to, message, subject):
        self.email_client.send_email(to, message, subject)

    @staticmethod
    def get_email_ids_from_groupList(group_list, identity_provider):
        email_list = set()
        for group in group_list:
            email_list.update(identity_provider.get_user_emailids_from_group(group))
        return email_list

    @staticmethod
    def get_email_provider_instance(recipient_groups, recipient_email_ids):
        return SESEmailNotificationService(Ses.get_ses_client(), recipient_groups, recipient_email_ids)

    @staticmethod
    def send_email_task(subject, message, recipient_groups_list, recipient_email_list):
        # Get instance of the email provider
        email_provider = SESEmailNotificationService.get_email_provider_instance(recipient_groups_list, recipient_email_list)
        try:
            identityProvider = Cognito()

            email_ids_to_send_emails = email_provider.get_email_ids_from_groupList(email_provider.recipient_group_list, identityProvider)

            if len(recipient_email_list) > 0:
                email_ids_to_send_emails.update(recipient_email_list)

            SESEmailNotificationService.send_email_to_users(email_ids_to_send_emails, email_provider, message, subject)

        except Exception as e:
            raise e
        else:
            return True

    @staticmethod
    def send_email_to_users(email_list, email_provider, message, subject):
        # Send individual emails to all the email ids. Sending individual emails helps in tracking individual emails via message-ids
        # https://aws.amazon.com/blogs/messaging-and-targeting/how-to-send-messages-to-multiple-recipients-with-amazon-simple-email-service-ses/
        for emailId in email_list:
            email_provider.send_email([emailId], message, subject)

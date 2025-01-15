import logging
from typing import List

from dataall.core.groups.db.constants import DataallGroups
from dataall.modules.notifications.services.ses_email_notification_service import SESEmailNotificationService
from dataall.base.config import config

log = logging.getLogger(__name__)


class AdminNotificationService:
    """
    Send email notifications to Admin Group i.e. DAAdministrators in data.all
    Args -
        1. process_error - string describing in short the error / exception details
        2. error_logs - List of all the exception error logs
        3. process_name - Code where the exception occurred. Example, inside an ECS task like cataloging task, etc or inside a graphql service
    """

    @classmethod
    def notify_admins_with_error_log(cls, process_error: str, error_logs: List[str], process_name: str = ''):
        if (
            config.get_property(
                'modules.datasets_base.features.share_notifications.email.parameters.admin_notifications', default=False
            )
            is False
        ):
            log.info('Admin notifications are switched off')
            return

        subject = f'Data.all alert | Attention Required | Failure in : {process_name}'
        email_message = f"""
            Following error occurred - <br><br> {process_error} <br><br>
        """
        for error_log in error_logs:
            email_message += error_log + '<br><br>'

        email_message += 'Please check the logs in cloudwatch for more details'

        SESEmailNotificationService.create_and_send_email_notifications(
            subject=subject, msg=email_message, recipient_groups_list=[DataallGroups.admin]
        )

from typing import Dict
import logging
from dataall.modules.notifications.services.ses_email_notification_service import SESEmailNotificationService
from dataall.modules.s3_datasets.db.dataset_models import S3Dataset
from dataall.modules.shares_base.db.share_object_repositories import ShareObjectRepository

log = logging.getLogger(__name__)


class DatasetTableNotifications:
    def __init__(self, dataset: S3Dataset):
        self.dataset: S3Dataset = dataset

    """
    Sends email notification on glue table updates to the dataset owners. 
    Also, if there exists shares on that dataset, then send email notifications to the requestors informing updates
    table_status_map - Dictionary of GlueTableName and table status ( InSync, Deleted, etc ) 
    """

    def notify_dataset_table_updates(self, session, table_status_map: Dict[str, str]):
        # Construct and send email reminders for datasets
        self._send_email_reminders_for_dataset(table_status_map)

        # Find all the shares made on this dataset
        shares = ShareObjectRepository.find_dataset_shares(
            session=session, dataset_uri=self.dataset.datasetUri, share_statues=['Processed']
        )
        if shares:
            for share in shares:
                self._send_email_notification_for_share(share, table_status_map)

    def _send_email_notification_for_share(self, share, table_status_map):
        subject = f'Alert: Data.all Update | Glue table updated for dataset: {self.dataset.name}'
        msg_footer = f"""
                    You have an active share with uri: {share.shareUri}. If there is any table requested by you on the dataset: {self.dataset.name} for that share it may have been affected <b>in case if the tables are deleted.</b><br> 
                    <b>Note</b>: Please check with the dataset owner if there is any missing table from your share - as it is likely deleted from the dataset.<br> If the table exists in the dataset and is successfully shared but you are unable to access the table, then please reach out to the data.all team<br><br>
                    Regards,<br>
                    data.all team 
                """
        table_content = self._construct_html_table_from_glue_status_map(table_status_map)
        msg_body = f"""
                Dear Team,<br><br> 
                Following tables have been updated for dataset: <b>{self.dataset.name}</b> <br><br>

                {table_content}<br><br>
                """
        msg = msg_body + msg_footer
        SESEmailNotificationService.create_and_send_email_notifications(
            subject=subject, msg=msg, recipient_groups_list=[share.groupUri]
        )

    def _send_email_reminders_for_dataset(self, table_status_map):
        subject = f'Data.all Update | Glue tables updated for dataset: {self.dataset.name}'
        table_content = self._construct_html_table_from_glue_status_map(table_status_map)
        msg_body = f"""
        Dear Team,<br><br> 
        Following tables have been updated for dataset: <b>{self.dataset.name}</b>. <br><br>
        
        {table_content}<br><br>
        """
        msg_footer = """
        Regards,<br>
        data.all team
        """
        msg = msg_body + msg_footer
        SESEmailNotificationService.create_and_send_email_notifications(
            subject=subject, msg=msg, recipient_groups_list=[self.dataset.SamlAdminGroupName, self.dataset.stewards]
        )

    @classmethod
    def _construct_html_table_from_glue_status_map(cls, table_status_map):
        table_heading = """
        <tr>    
            <th align='center'>Glue Table Name</th>
            <th align='center'>Status</th>
        </tr>
        """
        table_body = """"""
        for table_name, table_status in table_status_map.items():
            table_body += f"""
                <tr>
                    <td align='center'>{table_name}</td>
                    <td align='center'>{table_status}</td>
                </tr>
            """
        table_content = f"""
        <table border='1' style='border-collapse:collapse'>
            {table_heading}
            {table_body}
        </table>
        """
        return table_content

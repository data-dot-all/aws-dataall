import json
import logging

from botocore.exceptions import ClientError

from dataall.aws.handlers.service_handlers import Worker
from dataall.db import models
from dataall.db.api import Environment
from dataall.modules.datasets.aws.sns_dataset_client import SnsDatasetClient
from dataall.modules.datasets.services.dataset_service import DatasetService

logger = logging.getLogger(__name__)


class SnsDatasetHandler:
    def __init__(self):
        pass

    @staticmethod
    @Worker.handler(path='sns.dataset.publish_update')
    def publish_update(engine, task: models.Task):
        with engine.scoped_session() as session:
            dataset = DatasetService.get_dataset_by_uri(session, task.targetUri)
            environment = Environment.get_environment_by_uri(session, dataset.environmentUri)

            message = {
                'prefix': task.payload['s3Prefix'],
                'accountid': environment.AwsAccountId,
                'region': environment.region,
                'bucket_name': dataset.S3BucketName,
            }

            SnsDatasetClient(environment, dataset).publish_dataset_message(message)

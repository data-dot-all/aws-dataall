import json
import logging

from botocore.config import Config
from botocore.exceptions import ClientError

from dataall.base.aws.sts import SessionHelper
from dataall.modules.s3_datasets.db.dataset_models import S3Dataset

log = logging.getLogger(__name__)


class S3DatasetClient:
    def __init__(self, dataset: S3Dataset):
        """
        It first starts a session assuming the pivot role,
        then we define another session assuming the dataset role from the pivot role
        """
        self._pivot_role_session = SessionHelper.remote_session(accountid=dataset.AwsAccountId, region=dataset.region)
        self._client = self._pivot_role_session.client('s3')
        self._dataset = dataset

    def _get_dataset_role_client(self):
        session = SessionHelper.get_session(
            base_session=self._pivot_role_session, role_arn=self._dataset.IAMDatasetAdminRoleArn
        )
        dataset_client = session.client(
            's3',
            region_name=self._dataset.region,
            endpoint_url=f'https://s3.{self._dataset.region}.amazonaws.com',
            config=Config(signature_version='s3v4', s3={'addressing_style': 'virtual'}),
        )
        return dataset_client

    def get_file_upload_presigned_url(self, data):
        dataset = self._dataset
        client = self._get_dataset_role_client()
        try:
            client.get_bucket_acl(Bucket=dataset.S3BucketName, ExpectedBucketOwner=dataset.AwsAccountId)
            response = client.generate_presigned_post(
                Bucket=dataset.S3BucketName,
                Key=data.get('prefix', 'uploads') + '/' + data.get('fileName'),
                ExpiresIn=15 * 60,
            )
            return json.dumps(response)

        except ClientError as e:
            raise e

    def get_bucket_encryption(self) -> (str, str, str):
        dataset = self._dataset
        try:
            response = self._client.get_bucket_encryption(
                Bucket=dataset.S3BucketName, ExpectedBucketOwner=dataset.AwsAccountId
            )
            rule = response['ServerSideEncryptionConfiguration']['Rules'][0]
            encryption = rule['ApplyServerSideEncryptionByDefault']
            s3_encryption = encryption['SSEAlgorithm']
            # Format (using key id): arn:aws:kms:<region>:<account-ID>:key/<key-id>
            # (using alias): arn:aws:kms:<region>:<account-ID>:alias/<alias-name>
            kms_key = encryption.get('KMSMasterKeyID', '')
            kms_id = None
            kms_id_type = None
            if kms_key:
                kms_id = kms_key.split('/')[-1]
                kms_id_type = 'alias' if 'alias' in kms_key else 'key'

            return s3_encryption, kms_id_type, kms_id

        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                raise Exception(
                    f'Data.all Environment Pivot Role does not have s3:GetEncryptionConfiguration Permission for {dataset.S3BucketName} bucket: {e}'
                )
            raise Exception(f'Cannot fetch the bucket encryption configuration for {dataset.S3BucketName}: {e}')

    def list_object_keys(self, bucket_name):
        try:
            response = self._client.list_objects_v2(
                Bucket=bucket_name,
            )

            def txt_or_pdf(s):
                return s.split('.')[-1] in ['pdf', 'txt']

            return [ob['Key'] for ob in response.get('Contents', []) if txt_or_pdf(ob['Key'])]
        except ClientError as e:
            logging.error(f'Failed to list objects in {bucket_name} : {e}')
            raise e

import logging
from retrying import retry
from typing import List

from dataall.base.aws.sts import SessionHelper
from botocore.exceptions import ClientError

from dataall.modules.s3_datasets_shares.aws.share_policy_verifier import SharePolicyVerifier

log = logging.getLogger(__name__)

DATAALL_READ_ONLY_SID = 'DataAll-Bucket-ReadOnly'
DATAALL_WRITE_ONLY_SID = 'DataAll-Bucket-WriteOnly'
DATAALL_MODIFY_ONLY_SID = 'DataAll-Bucket-ModifyOnly'
DATAALL_ALLOW_OWNER_SID = 'AllowAllToAdmin'
DATAALL_DELEGATE_TO_ACCESS_POINT = 'DelegateAccessToAccessPoint'

DATAALL_BUCKET_SIDS = [
    DATAALL_READ_ONLY_SID,
    DATAALL_WRITE_ONLY_SID,
    DATAALL_MODIFY_ONLY_SID,
    DATAALL_ALLOW_OWNER_SID,
    DATAALL_DELEGATE_TO_ACCESS_POINT,
]


class S3ControlClient:
    def __init__(self, account_id: str, region: str):
        session = SessionHelper.remote_session(accountid=account_id, region=region)
        self._client = session.client('s3control', region_name=region)
        self._account_id = account_id

    def get_bucket_access_point_arn(self, access_point_name: str):
        try:
            access_point = self._client.get_access_point(
                AccountId=self._account_id,
                Name=access_point_name,
            )
        except Exception as e:
            log.info(f'Failed to get S3 bucket access point {access_point_name} on {self._account_id} : {e}')
            return None
        else:
            return access_point['AccessPointArn']

    def create_bucket_access_point(self, bucket_name: str, access_point_name: str):
        try:
            self._client.create_access_point(
                AccountId=self._account_id,
                Name=access_point_name,
                Bucket=bucket_name,
            )
        except Exception as e:
            log.error(f'S3 bucket access point creation failed for location {bucket_name} : {e}')
            if 'AccessPointAlreadyOwnedByYou' not in str(e):
                raise e

        return self.try_get_bucket_access_point_arn(bucket_name, access_point_name)

    @retry(retry_on_result=lambda arn: arn is None, stop_max_attempt_number=10, wait_fixed=30000)
    def try_get_bucket_access_point_arn(self, bucket_name: str, access_point_name: str):
        log.info(f'Attempt to get access point arn for bucket {bucket_name} and accesspoint {access_point_name}')
        all_access_points = self._client.list_access_points(
            AccountId=self._account_id, Bucket=bucket_name, MaxResults=1000
        )
        for ap in all_access_points['AccessPointList']:
            if ap['Name'] == access_point_name:
                return ap['AccessPointArn']
        return None

    def delete_bucket_access_point(self, access_point_name: str):
        try:
            self._client.delete_access_point(
                AccountId=self._account_id,
                Name=access_point_name,
            )
        except Exception as e:
            log.error(f'Failed to delete S3 bucket access point {access_point_name}/{self._account_id} : {e}')
            raise e

    def get_access_point_policy(self, access_point_name: str):
        try:
            response = self._client.get_access_point_policy(
                AccountId=self._account_id,
                Name=access_point_name,
            )
        except Exception as e:
            log.info(f'Failed to get policy of access point {access_point_name} on {self._account_id} : {e}')
            return None
        else:
            return response['Policy']

    def attach_access_point_policy(self, access_point_name: str, policy: str):
        try:
            self._client.put_access_point_policy(AccountId=self._account_id, Name=access_point_name, Policy=policy)
        except Exception as e:
            log.error(f'S3 bucket access point policy creation failed : {e}')
            raise e

    @staticmethod
    def generate_access_point_policy_template(
        principal_id: str,
        access_point_arn: str,
        s3_prefix: str,
        actions: List[str],
    ):
        policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': f'{principal_id}0',
                    'Effect': 'Allow',
                    'Principal': {'AWS': '*'},
                    'Action': ['s3:ListBucket'],
                    'Resource': f'{access_point_arn}',
                    'Condition': {'StringLike': {'s3:prefix': [f'{s3_prefix}/*'], 'aws:userId': [f'{principal_id}:*']}},
                },
                {
                    'Sid': f'{principal_id}1',
                    'Effect': 'Allow',
                    'Principal': {'AWS': '*'},
                    'Action': actions,
                    'Resource': [f'{access_point_arn}/object/{s3_prefix}/*'],
                    'Condition': {'StringLike': {'aws:userId': [f'{principal_id}:*']}},
                },
            ],
        }
        return policy

    @staticmethod
    def generate_default_bucket_policy(s3_bucket_name: str):
        policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Deny',
                    'Principal': {'AWS': '*'},
                    'Sid': 'RequiredSecureTransport',
                    'Action': 's3:*',
                    'Resource': [f'arn:aws:s3:::{s3_bucket_name}', f'arn:aws:s3:::{s3_bucket_name}/*'],
                    'Condition': {'Bool': {'aws:SecureTransport': 'false'}},
                },
            ],
        }
        return policy


class S3Client:
    def __init__(self, account_id, region):
        session = SessionHelper.remote_session(accountid=account_id, region=region)
        self._client = session.client('s3', region_name=region)
        self.region = region
        self._account_id = account_id

    # flag second_try indicates, that in case of MalformedPolicy error, we will try to fix it and try again
    def create_bucket_policy(self, bucket_name: str, policy: str, fix_malformed_principals=True):
        try:
            s3cli = self._client
            s3cli.put_bucket_policy(
                Bucket=bucket_name,
                Policy=policy,
                ConfirmRemoveSelfBucketAccess=False,
                ExpectedBucketOwner=self._account_id,
            )
            log.info(f'Created bucket policy of {bucket_name} on {self._account_id} successfully')
        except ClientError as e:
            if e.response['Error']['Code'] == 'MalformedPolicy':
                if fix_malformed_principals:
                    log.info('MalformedPolicy. Lets try again')
                    fixed_policy = SharePolicyVerifier.remove_malformed_principal(
                        policy, DATAALL_BUCKET_SIDS, self._account_id, self.region
                    )
                    self.create_bucket_policy(bucket_name, fixed_policy, False)
                else:
                    log.error(f'Failed to create bucket policy. MalformedPolicy: {policy}')
                    raise e
            else:
                raise e
        except Exception as e:
            log.error(f'Bucket policy created failed on bucket {bucket_name} of {self._account_id} : {e}')
            raise e

    def get_bucket_policy(self, bucket_name: str):
        try:
            s3cli = self._client
            response = s3cli.get_bucket_policy(Bucket=bucket_name, ExpectedBucketOwner=self._account_id)
        except Exception as e:
            log.warning(f'Failed to get bucket policy of {bucket_name} : {e}')
            return None
        else:
            return response['Policy']

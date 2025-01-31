import logging
from botocore.exceptions import ClientError

from .sts import SessionHelper

log = logging.getLogger(__name__)


class ServiceQuota:
    def __init__(self, account_id, region):
        session = SessionHelper.remote_session(accountid=account_id, region=region)
        self.client = session.client('service-quotas')

    def list_services(self):
        try:
            log.info('Fetching services list with service codes in aws account')
            services_list = []
            paginator = self.client.get_paginator('list_services')
            for page in paginator.paginate():
                services_list.extend(page.get('Services'))
            return services_list
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                raise Exception(f'Data.all Environment Pivot Role does not have permissions to do list_services : {e}')
            log.error(f'Failed list services and service codes due to: {e}')
            return []

    def list_service_quota(self, service_code):
        try:
            log.info('Fetching services quota code in aws account')
            service_quota_code_list = []
            paginator = self.client.get_paginator('list_service_quotas')
            for page in paginator.paginate(ServiceCode=service_code):
                service_quota_code_list.extend(page.get('Quotas'))
            log.debug(f'Services quota list: {service_quota_code_list}')
            return service_quota_code_list
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                raise Exception(
                    f'Data.all Environment Pivot Role does not have permissions to do list_service_quota : {e}'
                )
            log.error(f'Failed list quota codes to: {e}')
            return []

    def get_service_quota_value(self, service_code, service_quota_code):
        try:
            log.info(
                f'Getting service quota for service code: {service_code} and service quota code: {service_quota_code}'
            )
            response = self.client.get_service_quota(ServiceCode=service_code, QuotaCode=service_quota_code)
            return response['Quota']['Value']
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                raise Exception(
                    f'Data.all Environment Pivot Role does not have permissions to do get_service_quota: {e}'
                )
            log.error(f'Failed list quota codes to: {e}')
            return None

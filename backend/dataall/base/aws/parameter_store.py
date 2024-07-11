import logging

from botocore.exceptions import ClientError

from .sts import SessionHelper

log = logging.getLogger(__name__)


def ns2d(**kwargs):
    return kwargs


class ParameterStoreManager:
    def __init__(self):
        pass

    @staticmethod
    def client(AwsAccountId=None, region=None, role=None):
        if AwsAccountId:
            log.info(f"SSM Parameter remote session with role:{role if role else 'PivotRole'}")
            session = SessionHelper.remote_session(accountid=AwsAccountId, region=region, role=role)
        else:
            log.info('SSM Parameter session in central account')
            session = SessionHelper.get_session()
        return session.client('ssm', region_name=region)

    @staticmethod
    def get_parameter_value(AwsAccountId=None, region=None, parameter_path=None):
        if not parameter_path:
            raise Exception('Parameter name is None')
        parameter_value = ParameterStoreManager.client(AwsAccountId, region).get_parameter(Name=parameter_path)[
            'Parameter'
        ]['Value']
        return parameter_value

    @staticmethod
    def get_parameters_by_path(AwsAccountId=None, region=None, parameter_path=None):
        if not parameter_path:
            raise Exception('Parameter name is None')
        parameter_values = ParameterStoreManager.client(AwsAccountId, region).get_parameters_by_path(
            Path=parameter_path
        )['Parameters']
        return parameter_values

    @staticmethod
    def update_parameter(AwsAccountId, region, parameter_name, parameter_value, parameter_type='String'):
        if not parameter_name:
            raise Exception('Parameter name is None')
        if not parameter_value:
            raise Exception('Parameter value is None')

        response = ParameterStoreManager.client(AwsAccountId, region).put_parameter(
            Name=parameter_name, Value=parameter_value, Overwrite=True, Type=parameter_type
        )['Version']

        return str(response)

import logging

from dataall.core.resource_threshold.db.resource_threshold_repositories import ResourceThresholdRepository
from dataall.modules.worksheets.aws.glue_client import GlueClient
from dataall.modules.worksheets.aws.s3_client import S3Client
from dataall.modules.worksheets.aws.unstruct_bedrock_client import UnstructuredBedrockClient
from dataall.modules.s3_datasets.db.dataset_repositories import DatasetRepository
from dataall.modules.worksheets.aws.structured_bedrock_client import StructuredBedrockClient
from dataall.core.activity.db.activity_models import Activity
from dataall.core.environment.services.environment_service import EnvironmentService
from dataall.base.db import exceptions
from dataall.core.permissions.services.resource_policy_service import ResourcePolicyService
from dataall.core.permissions.services.tenant_policy_service import TenantPolicyService
from dataall.modules.worksheets.aws.athena_client import AthenaClient
from dataall.modules.worksheets.db.worksheet_models import Worksheet
from dataall.modules.worksheets.db.worksheet_repositories import WorksheetRepository
from dataall.modules.worksheets.services.worksheet_permissions import (
    MANAGE_WORKSHEETS,
    UPDATE_WORKSHEET,
    WORKSHEET_ALL,
    GET_WORKSHEET,
    DELETE_WORKSHEET,
    RUN_ATHENA_QUERY,
)


logger = logging.getLogger(__name__)


class WorksheetService:
    @staticmethod
    def get_worksheet_by_uri(session, uri: str) -> Worksheet:
        if not uri:
            raise exceptions.RequiredParameter(param_name='worksheetUri')
        worksheet = WorksheetRepository.find_worksheet_by_uri(session, uri)
        if not worksheet:
            raise exceptions.ObjectNotFound('Worksheet', uri)
        return worksheet

    @staticmethod
    @TenantPolicyService.has_tenant_permission(MANAGE_WORKSHEETS)
    def create_worksheet(session, username, data=None) -> Worksheet:
        worksheet = Worksheet(
            owner=username,
            label=data.get('label'),
            description=data.get('description', 'No description provided'),
            tags=data.get('tags'),
            chartConfig={'dimensions': [], 'measures': [], 'chartType': 'bar'},
            SamlAdminGroupName=data['SamlAdminGroupName'],
        )

        session.add(worksheet)
        session.commit()

        activity = Activity(
            action='WORKSHEET:CREATE',
            label='WORKSHEET:CREATE',
            owner=username,
            summary=f'{username} created worksheet {worksheet.name} ',
            targetUri=worksheet.worksheetUri,
            targetType='worksheet',
        )
        session.add(activity)

        ResourcePolicyService.attach_resource_policy(
            session=session,
            group=data['SamlAdminGroupName'],
            permissions=WORKSHEET_ALL,
            resource_uri=worksheet.worksheetUri,
            resource_type=Worksheet.__name__,
        )
        return worksheet

    @staticmethod
    @ResourcePolicyService.has_resource_permission(UPDATE_WORKSHEET)
    def update_worksheet(session, username, uri, data=None):
        worksheet = WorksheetService.get_worksheet_by_uri(session, uri)
        for field in data.keys():
            setattr(worksheet, field, data.get(field))
        session.commit()

        activity = Activity(
            action='WORKSHEET:UPDATE',
            label='WORKSHEET:UPDATE',
            owner=username,
            summary=f'{username} updated worksheet {worksheet.name} ',
            targetUri=worksheet.worksheetUri,
            targetType='worksheet',
        )
        session.add(activity)
        return worksheet

    @staticmethod
    @ResourcePolicyService.has_resource_permission(GET_WORKSHEET)
    def get_worksheet(session, uri):
        worksheet = WorksheetService.get_worksheet_by_uri(session, uri)
        return worksheet

    @staticmethod
    @ResourcePolicyService.has_resource_permission(DELETE_WORKSHEET)
    def delete_worksheet(session, uri) -> bool:
        worksheet = WorksheetService.get_worksheet_by_uri(session, uri)
        session.delete(worksheet)
        ResourcePolicyService.delete_resource_policy(
            session=session,
            group=worksheet.SamlAdminGroupName,
            resource_uri=uri,
            resource_type=Worksheet.__name__,
        )
        return True

    @staticmethod
    @ResourcePolicyService.has_resource_permission(RUN_ATHENA_QUERY)
    def run_sql_query(session, uri, worksheetUri, sqlQuery):
        environment = EnvironmentService.get_environment_by_uri(session, uri)
        worksheet = WorksheetService.get_worksheet_by_uri(session, worksheetUri)

        env_group = EnvironmentService.get_environment_group(
            session, worksheet.SamlAdminGroupName, environment.environmentUri
        )

        cursor = AthenaClient.run_athena_query(
            aws_account_id=environment.AwsAccountId,
            env_group=env_group,
            s3_staging_dir=f's3://{environment.EnvironmentDefaultBucketName}/athenaqueries/{env_group.environmentAthenaWorkGroup}/',
            region=environment.region,
            sql=sqlQuery,
        )

        return AthenaClient.convert_query_output(cursor)

    @staticmethod
    @ResourcePolicyService.has_resource_permission(RUN_ATHENA_QUERY)
    @ResourceThresholdRepository.invocation_handler('nlq')
    def run_nlq(session, uri, worksheetUri, prompt, datasetUri, table_names):
        environment = EnvironmentService.get_environment_by_uri(session, uri)
        dataset = DatasetRepository.get_dataset_by_uri(session, datasetUri)
        glue_client = GlueClient(
            account_id=dataset.AwsAccountId, region=dataset.region, database=dataset.GlueDatabaseName
        )

        metadata = []
        if ' ' in table_names:
            table_names = table_names.split(' ')
            for table in table_names:
                metadata.append(glue_client.get_metadata(table))
        else:
            metadata = glue_client.get_metadata(table_names)

        bedrock_client = StructuredBedrockClient(account_id=environment.AwsAccountId, region='us-east-1')

        response = bedrock_client.invoke_model(prompt, metadata)

        return {'error': None, 'response': response}

    @staticmethod
    @ResourceThresholdRepository.invocation_handler('nlq')
    def unstruct_query(session, uri, worksheetUri, prompt, datasetUri, key):
        environment = EnvironmentService.get_environment_by_uri(session, uri)

        worksheet = WorksheetService.get_worksheet_by_uri(session, worksheetUri)

        dataset = DatasetRepository.get_dataset_by_uri(session, datasetUri)


        env_group = EnvironmentService.get_environment_group(
            session, worksheet.SamlAdminGroupName, environment.environmentUri
        )
        s3_client = S3Client(
            account_id=environment.AwsAccountId,
            region=environment.region,
            env_group=env_group,
            aws_account_id=environment.AwsAccountId,
        )

        content = s3_client.get_content(dataset.S3BucketName, key)
        bedrock_client = UnstructuredBedrockClient(account_id=environment.AwsAccountId, region='us-east-1')
        response = bedrock_client.invoke_model(prompt, content)
        return {'error': None, 'response': response}
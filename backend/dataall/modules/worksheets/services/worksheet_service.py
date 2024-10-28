import logging

from dataall.core.resource_threshold.services.resource_threshold_service import ResourceThresholdService
from dataall.modules.worksheets.aws.glue_client import GlueClient
from dataall.modules.worksheets.aws.s3_client import S3Client
from dataall.modules.s3_datasets.db.dataset_repositories import DatasetRepository
from dataall.modules.worksheets.aws.bedrock_client import BedrockClient
from dataall.core.activity.db.activity_models import Activity
from dataall.core.environment.services.environment_service import EnvironmentService
from dataall.base.db import exceptions
from dataall.core.permissions.services.resource_policy_service import ResourcePolicyService
from dataall.core.permissions.services.tenant_policy_service import TenantPolicyService
from dataall.modules.worksheets.aws.athena_client import AthenaClient
from dataall.modules.worksheets.db.worksheet_models import Worksheet
from dataall.modules.worksheets.db.worksheet_repositories import WorksheetRepository
from dataall.base.context import get_context
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
    def _get_worksheet_by_uri(session, uri: str) -> Worksheet:
        if not uri:
            raise exceptions.RequiredParameter(param_name='worksheetUri')
        worksheet = WorksheetRepository.find_worksheet_by_uri(session, uri)
        if not worksheet:
            raise exceptions.ObjectNotFound('Worksheet', uri)
        return worksheet

    @staticmethod
    @TenantPolicyService.has_tenant_permission(MANAGE_WORKSHEETS)
    def create_worksheet(data=None) -> Worksheet:
        context = get_context()
        with context.db_engine.scoped_session() as session:
            worksheet = Worksheet(
                owner=context.username,
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
                owner=context.username,
                summary=f'{context.username} created worksheet {worksheet.name} ',
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
    @TenantPolicyService.has_tenant_permission(MANAGE_WORKSHEETS)
    @ResourcePolicyService.has_resource_permission(UPDATE_WORKSHEET)
    def update_worksheet(uri, data=None):
        context = get_context()
        with context.db_engine.scoped_session() as session:
            worksheet = WorksheetService._get_worksheet_by_uri(session, uri)
            for field in data.keys():
                setattr(worksheet, field, data.get(field))
            session.commit()

            activity = Activity(
                action='WORKSHEET:UPDATE',
                label='WORKSHEET:UPDATE',
                owner=context.username,
                summary=f'{context.username} updated worksheet {worksheet.name} ',
                targetUri=worksheet.worksheetUri,
                targetType='worksheet',
            )
            session.add(activity)
            return worksheet

    @staticmethod
    @ResourcePolicyService.has_resource_permission(GET_WORKSHEET)
    def get_worksheet(uri):
        with get_context().db_engine.scoped_session() as session:
            worksheet = WorksheetService._get_worksheet_by_uri(session, uri)
            return worksheet

    @staticmethod
    def list_worksheets(filter):
        context = get_context()
        with context.db_engine.scoped_session() as session:
            return WorksheetRepository.paginated_user_worksheets(
                session=session,
                username=context.username,
                groups=context.groups,
                uri=None,
                data=filter,
                check_perm=True,
            )

    @staticmethod
    @TenantPolicyService.has_tenant_permission(MANAGE_WORKSHEETS)
    @ResourcePolicyService.has_resource_permission(DELETE_WORKSHEET)
    def delete_worksheet(uri) -> bool:
        with get_context().db_engine.scoped_session() as session:
            worksheet = WorksheetService._get_worksheet_by_uri(session, uri)
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
    def run_sql_query(uri, worksheetUri, sqlQuery):
        with get_context().db_engine.scoped_session() as session:
            environment = EnvironmentService.get_environment_by_uri(session, uri)
            worksheet = WorksheetService._get_worksheet_by_uri(session, worksheetUri)

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
    @ResourceThresholdService.check_invocation_count('nlq', 'modules.worksheets.features.nlq.max_count_per_day')
    def run_nlq(uri, prompt, worksheetUri, db_name, table_names):
        with get_context().db_engine.scoped_session() as session:
            environment = EnvironmentService.get_environment_by_uri(session, uri)
            worksheet = WorksheetService._get_worksheet_by_uri(session, worksheetUri)

            env_group = EnvironmentService.get_environment_group(
                session, worksheet.SamlAdminGroupName, environment.environmentUri
            )

        glue_client = GlueClient(
            account_id=environment.AwsAccountId, region=environment.region, role=env_group.environmentIAMRoleArn
        )

        metadata = []
        for table in table_names:
            metadata.append(glue_client.get_table_metadata(database=db_name, table_name=table))

        return BedrockClient().invoke_model_text_to_sql(prompt, '\n'.join(metadata))

    @staticmethod
    @ResourcePolicyService.has_resource_permission(RUN_ATHENA_QUERY)
    @ResourceThresholdService.check_invocation_count('nlq', 'modules.worksheets.features.nlq.max_count_per_day')
    def analyze_text_genai(uri, worksheetUri, prompt, datasetUri, key):
        with get_context().db_engine.scoped_session() as session:
            environment = EnvironmentService.get_environment_by_uri(session, uri)
            worksheet = WorksheetService._get_worksheet_by_uri(session, worksheetUri)

            env_group = EnvironmentService.get_environment_group(
                session, worksheet.SamlAdminGroupName, environment.environmentUri
            )

            dataset = DatasetRepository.get_dataset_by_uri(session, datasetUri)

        s3_client = S3Client(
            account_id=environment.AwsAccountId,
            region=environment.region,
            role=env_group.environmentIAMRoleArn,
        )

        content = s3_client.get_content(dataset.S3BucketName, key)
        return BedrockClient().invoke_model_process_text(prompt, content)

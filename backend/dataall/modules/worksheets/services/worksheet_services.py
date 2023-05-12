import logging

from dataall import db
from dataall.aws.handlers.sts import SessionHelper
from dataall.core.permission_checker import has_tenant_permission, has_resource_permission
from dataall.db import exceptions
from dataall.db import models
from dataall.db.api import ResourcePolicy
from dataall.modules.worksheets.aws.athena_client import AthenaClient
from dataall.modules.worksheets.db.models import Worksheet
from dataall.modules.worksheets.db.repositories import WorksheetRepository
from dataall.modules.worksheets.services.worksheet_permissions import MANAGE_WORKSHEETS, UPDATE_WORKSHEET, \
    WORKSHEET_ALL, GET_WORKSHEET, DELETE_WORKSHEET, RUN_ATHENA_QUERY


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
    @has_tenant_permission(MANAGE_WORKSHEETS)
    def create_worksheet(
        session, username, groups, uri, data=None, check_perm=None
    ) -> Worksheet:
        if not data:
            raise exceptions.RequiredParameter(data)
        if not data.get('SamlAdminGroupName'):
            raise exceptions.RequiredParameter('groupUri')
        if not data.get('label'):
            raise exceptions.RequiredParameter('label')

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

        activity = models.Activity(
            action='WORKSHEET:CREATE',
            label='WORKSHEET:CREATE',
            owner=username,
            summary=f'{username} created worksheet {worksheet.name} ',
            targetUri=worksheet.worksheetUri,
            targetType='worksheet',
        )
        session.add(activity)

        ResourcePolicy.attach_resource_policy(
            session=session,
            group=data['SamlAdminGroupName'],
            permissions=WORKSHEET_ALL,
            resource_uri=worksheet.worksheetUri,
            resource_type=Worksheet.__name__,
        )
        return worksheet

    @staticmethod
    @has_resource_permission(UPDATE_WORKSHEET)
    def update_worksheet(session, username, groups, uri, data=None, check_perm=None):
        worksheet = WorksheetService.get_worksheet_by_uri(session, uri)
        for field in data.keys():
            setattr(worksheet, field, data.get(field))
        session.commit()

        activity = models.Activity(
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
    @has_resource_permission(GET_WORKSHEET)
    def get_worksheet(session, username, groups, uri, data=None, check_perm=None):
        worksheet = WorksheetService.get_worksheet_by_uri(session, uri)
        return worksheet

    @staticmethod
    @has_resource_permission(DELETE_WORKSHEET)
    def delete_worksheet(
        session, username, groups, uri, data=None, check_perm=None
    ) -> bool:
        worksheet = WorksheetService.get_worksheet_by_uri(session, uri)
        session.delete(worksheet)
        ResourcePolicy.delete_resource_policy(
            session=session,
            group=worksheet.SamlAdminGroupName,
            resource_uri=uri,
            resource_type=Worksheet.__name__,
        )
        return True

    @staticmethod
    @has_resource_permission(RUN_ATHENA_QUERY)
    def run_sql_query(session, username, groups, uri, worksheetUri, sqlQuery):
        environment = db.api.Environment.get_environment_by_uri(session, uri)
        worksheet = WorksheetService.get_worksheet_by_uri(session, worksheetUri)

        env_group = db.api.Environment.get_environment_group(
            session, worksheet.SamlAdminGroupName, environment.environmentUri
        )

        base_session = SessionHelper.remote_session(accountid=environment.AwsAccountId)
        boto3_session = SessionHelper.get_session(base_session=base_session, role_arn=env_group.environmentIAMRoleArn)
        
        cursor = AthenaClient.run_athena_query(
            session=boto3_session,
            work_group=env_group.environmentAthenaWorkGroup,
            s3_staging_dir=f's3://{environment.EnvironmentDefaultBucketName}/athenaqueries/{env_group.environmentAthenaWorkGroup}/',
            region=environment.region,
            sql=sqlQuery
        )

        columns = []
        for f in cursor.description:
            columns.append({'columnName': f[0], 'typeName': 'String'})

        rows = []
        for row in cursor:
            record = {'cells': []}
            for col_position, column in enumerate(columns):
                cell = {}
                cell['columnName'] = column['columnName']
                cell['typeName'] = column['typeName']
                cell['value'] = str(row[col_position])
                record['cells'].append(cell)
            rows.append(record)
        return {
            'error': None,
            'AthenaQueryId': cursor.query_id,
            'ElapsedTime': cursor.total_execution_time_in_millis,
            'rows': rows,
            'columns': columns,
        }

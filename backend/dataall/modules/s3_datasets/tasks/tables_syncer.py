import logging
import os
import sys
from operator import and_

from dataall.base.aws.sts import SessionHelper
from dataall.core.environment.db.environment_models import Environment, EnvironmentGroup
from dataall.core.environment.services.environment_service import EnvironmentService
from dataall.base.db import get_engine
from dataall.modules.notifications.services.admin_notifications import AdminNotificationService
from dataall.modules.s3_datasets.aws.glue_dataset_client import DatasetCrawler
from dataall.modules.s3_datasets.aws.lf_table_client import LakeFormationTableClient
from dataall.modules.s3_datasets.services.dataset_table_notifications import DatasetTableNotifications
from dataall.modules.s3_datasets.services.dataset_table_service import DatasetTableService
from dataall.modules.s3_datasets.db.dataset_repositories import DatasetRepository
from dataall.modules.s3_datasets.db.dataset_models import DatasetTable, S3Dataset
from dataall.modules.s3_datasets.indexers.table_indexer import DatasetTableIndexer
from dataall.modules.s3_datasets.indexers.dataset_indexer import DatasetIndexer
from dataall.modules.s3_datasets.services.dataset_alarm_service import DatasetAlarmService

log = logging.getLogger(__name__)


def sync_tables(engine):
    task_exceptions = []
    try:
        with engine.scoped_session() as session:
            processed_tables = []
            all_datasets: [S3Dataset] = DatasetRepository.list_all_active_datasets(session)
            log.info(f'Found {len(all_datasets)} datasets for tables sync')
            dataset: S3Dataset
            for dataset in all_datasets:
                log.info(f'Synchronizing dataset {dataset.name}|{dataset.datasetUri} tables')
                env: Environment = (
                    session.query(Environment)
                    .filter(
                        and_(
                            Environment.environmentUri == dataset.environmentUri,
                            Environment.deleted.is_(None),
                        )
                    )
                    .first()
                )
                env_group: EnvironmentGroup = EnvironmentService.get_environment_group(
                    session, dataset.SamlAdminGroupName, env.environmentUri
                )
                try:
                    if not env or not is_assumable_pivot_role(env):
                        log.info(f'Dataset {dataset.GlueDatabaseName} has an invalid environment')
                    else:
                        tables = DatasetCrawler(dataset).list_glue_database_tables(dataset.S3BucketName)

                        log.info(f'Found {len(tables)} tables on Glue database {dataset.GlueDatabaseName}')

                        table_status_map = DatasetTableService.sync_existing_tables(
                            session, uri=dataset.datasetUri, glue_tables=tables
                        )

                        if table_status_map:
                            log.info('Sending email notification after dataset table updates were found')
                            try:
                                DatasetTableNotifications(dataset=dataset).notify_dataset_table_updates(
                                    session=session, table_status_map=table_status_map
                                )
                            except Exception as e:
                                error_log = f'Error occurred while sending email to notify about changes to the glue tables for dataset with uri: {dataset.datasetUri} due to: {e}'
                                task_exceptions.append(error_log)

                        tables = session.query(DatasetTable).filter(DatasetTable.datasetUri == dataset.datasetUri).all()

                        log.info('Updating tables permissions on Lake Formation...')

                        for table in tables:
                            LakeFormationTableClient(table).grant_principals_all_table_permissions(
                                principals=[
                                    SessionHelper.get_delegation_role_arn(env.AwsAccountId, env.region),
                                    env_group.environmentIAMRoleArn,
                                ],
                            )

                        processed_tables.extend(tables)

                        DatasetTableIndexer.upsert_all(session, dataset_uri=dataset.datasetUri)
                        DatasetIndexer.upsert(session=session, dataset_uri=dataset.datasetUri)
                except Exception as e:
                    log.error(
                        f'Failed to sync tables for dataset '
                        f'{dataset.AwsAccountId}/{dataset.GlueDatabaseName} '
                        f'due to: {e}'
                    )
                    DatasetAlarmService().trigger_dataset_sync_failure_alarm(dataset, str(e))
                    task_exceptions.append(str(e))
            return processed_tables
    except Exception as e:
        log.error(f'Error while running table syncer task due to: {e}')
        task_exceptions.append(str(e))
    finally:
        if len(task_exceptions) > 0:
            AdminNotificationService().notify_admins_with_error_log(
                process_name='Table Syncer',
                error_logs=task_exceptions,
                process_error='Error while running table syncer task',
            )


def is_assumable_pivot_role(env: Environment):
    aws_session = SessionHelper.remote_session(accountid=env.AwsAccountId, region=env.region)
    if not aws_session:
        log.error(f'Failed to assume dataall pivot role in environment {env.AwsAccountId}')
        return False
    return True


if __name__ == '__main__':
    ENVNAME = os.environ.get('envname', 'local')
    ENGINE = get_engine(envname=ENVNAME)
    sync_tables(engine=ENGINE)

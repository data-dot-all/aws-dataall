import logging
import os
import sys
import datetime

from dataall.core.environment.db.environment_models import Environment
from dataall.base.db import get_engine
from dataall.modules.notifications.services.admin_notifications import AdminNotificationService
from dataall.modules.omics.aws.omics_client import OmicsClient
from dataall.modules.omics.db.omics_models import OmicsWorkflow
from dataall.modules.omics.api.enums import OmicsWorkflowType
from dataall.modules.omics.db.omics_repository import OmicsRepository


log = logging.getLogger(__name__)


def fetch_omics_workflows(engine):
    """List Omics workflows."""
    try:
        log.info('Starting omics workflows fetcher')
        with engine.scoped_session() as session:
            environments = OmicsRepository(session).list_environments_with_omics_enabled()
            # designed for ready2run and private workflows; when private workflow support is
            # introduced, we will need go over all environments
            if len(environments) == 0:
                log.info('No environments found. Nothing to do.')
                return True
            env = environments[0]
            ready_workflows = OmicsClient(awsAccountId=env.AwsAccountId, region=env.region).list_workflows(
                type=OmicsWorkflowType.READY2RUN.value
            )
            # Removing private workflows until fully supported after initial launch
            # private_workflows = OmicsClient.list_workflows(awsAccountId=env.AwsAccountId, region=env.region, type=OmicsWorkflowType.PRIVATE.value)
            workflows = ready_workflows  # + private_workflows
            log.info(f'Found workflows {str(workflows)} in environment {env.environmentUri}')
            for workflow in workflows:
                log.info(f"Processing workflow name={workflow['name']}, id={workflow['id']}...")
                existing_workflow = OmicsRepository(session).get_workflow_by_id(workflow['id'])
                if existing_workflow is not None:
                    log.info(
                        f"Workflow name={workflow['name']}, id={workflow['id']} has already been registered in database. Updating information..."
                    )
                    existing_workflow.name = workflow['name']
                    existing_workflow.label = workflow['name']
                    session.commit()

                else:
                    log.info(
                        f"Workflow name={workflow['name']} , id={workflow['id']} in environment {env.environmentUri} is new. Registering..."
                    )
                    omicsWorkflow = OmicsWorkflow(
                        id=workflow['id'],
                        name=workflow['name'],
                        arn=workflow['arn'],
                        type=workflow['type'],
                        environmentUri=env.environmentUri,
                        label=workflow['name'],
                        owner=env.environmentUri,
                    )
                    OmicsRepository(session).save_omics_workflow(omicsWorkflow)
        return True
    except Exception as e:
        log.error(f'Error occurred while processing omics workflow task due to: {e}')
        AdminNotificationService().notify_admins_with_error_log(
            process_error='Error occurred while processing omics workflow task',
            error_logs=[str(e)],
            process_name='Omics Workflow',
        )


if __name__ == '__main__':
    ENVNAME = os.environ.get('envname', 'local')
    ENGINE = get_engine(envname=ENVNAME)
    fetch_omics_workflows(engine=ENGINE)

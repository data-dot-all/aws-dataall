import logging
import os
import time

import boto3
from botocore.exceptions import ClientError

from .service_handlers import Worker
from ... import db
from ...db import models
from ...utils import Parameter

log = logging.getLogger('aws:ecs')


class Ecs:
    def __init__(self):
        pass

    @staticmethod
    @Worker.handler(path='ecs.cdkproxy.deploy')
    def deploy_stack(engine, task: models.Task):
        with engine.scoped_session() as session:
            stack: models.Stack = db.api.Stack.get_stack_by_uri(
                session, stack_uri=task.targetUri
            )
            envname = os.environ.get('envname', 'local')
            cluster_name = Parameter().get_parameter(
                env=envname, path='ecs/cluster/name'
            )

            while Ecs.is_task_running(cluster_name=cluster_name, started_by=f'awsworker-{task.targetUri}'):
                log.info(
                    f'ECS task for stack stack-{task.targetUri} is running waiting for 30 seconds before retrying...'
                )
                time.sleep(30)

            stack.EcsTaskArn = Ecs.run_cdkproxy_task(stack_uri=task.targetUri)

    @staticmethod
    def run_cdkproxy_task(stack_uri):
        envname = os.environ.get('envname', 'local')
        cdkproxy_task_definition = Parameter().get_parameter(
            env=envname, path='ecs/task_def_arn/cdkproxy'
        )
        container_name = Parameter().get_parameter(
            env=envname, path='ecs/container/cdkproxy'
        )
        cluster_name = Parameter().get_parameter(env=envname, path='ecs/cluster/name')
        subnets = Parameter().get_parameter(env=envname, path='ecs/private_subnets')
        security_groups = Parameter().get_parameter(
            env=envname, path='ecs/security_groups'
        )
        try:
            task_arn = Ecs.run_ecs_task(
                cluster_name=cluster_name,
                task_definition=cdkproxy_task_definition,
                container_name=container_name,
                security_groups=security_groups,
                subnets=subnets,
                environment=[
                    {'name': 'stackUri', 'value': stack_uri},
                    {'name': 'config_location', 'value': '/config.json'},
                    {'name': 'envname', 'value': envname},
                    {
                        'name': 'AWS_REGION',
                        'value': os.getenv('AWS_REGION', 'eu-west-1'),
                    },
                ],
                started_by=f'awsworker-{stack_uri}',
            )
            log.info(f'ECS Task {task_arn} running')
            return task_arn
        except ClientError as e:
            log.error(e)
            raise e

    @staticmethod
    def run_ecs_task(
        cluster_name,
        task_definition,
        container_name,
        security_groups,
        subnets,
        environment,
        started_by='awsworker',
    ):
        response = boto3.client('ecs').run_task(
            cluster=cluster_name,
            taskDefinition=task_definition,
            count=1,
            launchType='FARGATE',
            networkConfiguration={
                'awsvpcConfiguration': {
                    'subnets': subnets.split(','),
                    'securityGroups': security_groups.split(','),
                }
            },
            overrides={
                'containerOverrides': [
                    {
                        'name': container_name,
                        'environment': environment,
                    }
                ]
            },
            startedBy=started_by,
        )
        if response['failures']:
            raise Exception(
                ', '.join(
                    [
                        'fail to run task {0} reason: {1}'.format(
                            failure['arn'], failure['reason']
                        )
                        for failure in response['failures']
                    ]
                )
            )
        task_arn = response.get('tasks', [{'taskArn': None}])[0]['taskArn']
        log.info(f'Task started {task_arn}..')
        return task_arn

    @staticmethod
    def is_task_running(cluster_name, started_by):
        try:
            client = boto3.client('ecs')
            running_tasks = client.list_tasks(
                cluster=cluster_name, startedBy=started_by, desiredStatus='RUNNING'
            )
            if running_tasks and running_tasks.get('taskArns'):
                return True
            return False
        except ClientError as e:
            log.error(e)
            raise e

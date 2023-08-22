"""
A service layer for Omics pipelines
Central part for working with Omics workflow runs
"""
import dataclasses
import logging
from dataclasses import dataclass, field
from typing import List, Dict


from dataall.base.context import get_context
from dataall.core.environment.env_permission_checker import has_group_permission
from dataall.core.environment.services.environment_service import EnvironmentService
from dataall.core.permissions.db.resource_policy import ResourcePolicy
from dataall.core.permissions.permission_checker import has_resource_permission, has_tenant_permission
from dataall.core.stacks.api import stack_helper
from dataall.core.stacks.db.stack import Stack
from dataall.base.db import exceptions
from dataall.modules.omics.db.models import *

from dataall.modules.omics.aws.omics_client import client
from dataall.modules.omics.db.omics_repository import OmicsRepository
from dataall.modules.omics.aws.omics_client import OmicsClient
from dataall.modules.omics.db.models import OmicsRun
from dataall.modules.omics.services.omics_permissions import (
    MANAGE_OMICS_RUNS,
    CREATE_OMICS_RUN,
    GET_OMICS_RUN,
    OMICS_RUN_ALL,
    DELETE_OMICS_RUN
)

logger = logging.getLogger(__name__)


@dataclass
class OmicsRunCreationRequest:
    """A request dataclass for Omics pipeline creation. Adds default values for missed parameters"""
    label: str
    SamlAdminGroupName: str
    environment: Dict = field(default_factory=dict)
    description: str = "No description provided"
    tags: List[str] = field(default_factory=list)
    S3InputBucket: str = "No input bucket provided"
    S3InputPrefix: str = ""
    S3OutputBucket: str = "No output bucket provided"
    S3OutputPrefix: str = ""


    @classmethod
    def from_dict(cls, env):
        """Copies only required fields from the dictionary and creates an instance of class"""
        fields = set([f.name for f in dataclasses.fields(cls)])
        return cls(**{
            k: v for k, v in env.items()
            if k in fields
        })


class OmicsService:
    """
    Encapsulate the logic of interactions with Omics pipelines.
    """

    @staticmethod
    @has_tenant_permission(MANAGE_OMICS_RUNS)
    @has_resource_permission(CREATE_OMICS_RUN)
    @has_group_permission(CREATE_OMICS_RUN)
    def create_omics_run(*, uri: str, admin_group: str, request: OmicsRunCreationRequest) -> OmicsRun:
        """
        Creates an omics_run and attach policies to it
        Throws an exception if omics_run are not enabled for the environment
        """

        with _session() as session:
            environment = EnvironmentService.get_environment_by_uri(session, uri)
            enabled = EnvironmentService.get_boolean_env_param(session, environment, "omicsEnabled")

            if not enabled and enabled.lower() != "true":
                raise exceptions.UnauthorizedOperation(
                    action=CREATE_OMICS_RUN,
                    message=f'OMICS_RUN feature is disabled for the environment {environment.label}',
                )

            omics_run = OmicsRun(
                owner=get_context().username,
                organizationUri=environment.organizationUri,
                environmentUri=environment.environmentUri,
                SamlAdminGroupName=admin_group,
                label=request.label,
                description=request.description,
                tags=request.tags,
                AwsAccountId=environment.AwsAccountId,
                region=environment.region,
                ## TODO: define inputs, based on resolver and on RDS table
            )

            OmicsRepository(session).save_omics_run(omics_run)

            ## TODO: add omics client boto3 API calls


            ResourcePolicy.attach_resource_policy(
                session=session,
                group=request.SamlAdminGroupName,
                permissions=OMICS_RUN_ALL,
                resource_uri=omics_run.runUri,
                resource_type=OmicsRun.__name__,
            )

            if environment.SamlGroupName != admin_group:
                ResourcePolicy.attach_resource_policy(
                    session=session,
                    group=environment.SamlGroupName,
                    permissions=OMICS_RUN_ALL,
                    resource_uri=omics_run.runUri,
                    resource_type=OmicsRun.__name__,
                )
        return omics_run

    @staticmethod
    def _get_omics_run(session, uri):
        omics_run = OmicsRepository(session).find_omics_run(uri)
        if not omics_run:
            raise exceptions.ObjectNotFound("OmicsRun", uri)
        return omics_run

    @staticmethod
    @has_resource_permission(GET_OMICS_RUN)
    def get_omics_run(*, uri: str):
        with _session() as session:
            return OmicsService._get_omics_run(session, uri)


    @staticmethod
    def list_user_omics_runs(*, filter: dict) -> dict:
        """List existed user Omics pipelines. Filters only required omics_runs by the filter param"""
        with _session() as session:
            return OmicsRepository(session).paginated_user_runs(
                username=get_context().username,
                groups=get_context().groups,
                filter=filter
            )
    
    @staticmethod
    def list_omics_workflows1(filter: dict) -> dict:
        """List Omics workflows."""
        with _session() as session:
            return OmicsRepository(session).paginated_omics_workflows(
                filter=filter
            )

    @staticmethod
    def list_omics_workflows(filter: dict) -> dict:
        """List Omics workflows."""
        omicsClient = OmicsClient('545117064741')
        workflows = omicsClient.list_workflows()
        # for workflow in workflows:
        #     omicsWorkflow = OmicsWorkflow(id=workflow['id'], name=workflow['name'], arn=workflow['arn'], status=workflow['status'], type=workflow['type'])
        #     with _session() as session:
        #         OmicsRepository(session).save_omics_workflow(omicsWorkflow)
        return omicsClient.list_workflows()


    @staticmethod
    @has_resource_permission(DELETE_OMICS_RUN)
    def delete_omics_run(*, uri: str):
        ##T TODO: IMPLEMENT IN omics_repository
        """Deletes Omics project from the database and if delete_from_aws is True from AWS as well"""
        with _session() as session:
            omics_run = OmicsService._get_omics_run(session, uri)
            if not omics_run:
                raise exceptions.ObjectNotFound("OmicsRun", uri)
            session.delete(omics_run)

            ResourcePolicy.delete_resource_policy(
                session=session,
                resource_uri=omics_run.runUri,
                group=omics_run.SamlAdminGroupName,
            )




def _session():
    return get_context().db_engine.scoped_session()

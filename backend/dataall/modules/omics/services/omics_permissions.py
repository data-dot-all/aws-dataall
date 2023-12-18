"""
Add module's permissions to the global permissions.
Contains permissions for Omics RUNs
"""

# TODO: THIS HAS NOT BEEN IMPLEMENTED AT ALL AND NEEDS TO BE IMPLEMENTED
from dataall.core.permissions.permissions import (
    ENVIRONMENT_ALL,
    ENVIRONMENT_INVITED,
    RESOURCES_ALL_WITH_DESC,
    RESOURCES_ALL,
    ENVIRONMENT_INVITATION_REQUEST,
    TENANT_ALL,
    TENANT_ALL_WITH_DESC
)

GET_OMICS_RUN = "GET_OMICS_RUN"
UPDATE_OMICS_RUN = "UPDATE_OMICS_RUN"
DELETE_OMICS_RUN = "DELETE_OMICS_RUN"
CREATE_OMICS_RUN = "CREATE_OMICS_RUN"
MANAGE_OMICS_RUNS = "MANAGE_OMICS_RUNS"

OMICS_RUN_ALL = [
    GET_OMICS_RUN,
    DELETE_OMICS_RUN,
    UPDATE_OMICS_RUN,
]

LIST_ENVIRONMENT_OMICS_RUNS = 'LIST_ENVIRONMENT_OMICS_RUNS'

ENVIRONMENT_ALL.append(LIST_ENVIRONMENT_OMICS_RUNS)
ENVIRONMENT_ALL.append(CREATE_OMICS_RUN)
ENVIRONMENT_INVITED.append(LIST_ENVIRONMENT_OMICS_RUNS)
ENVIRONMENT_INVITED.append(CREATE_OMICS_RUN)
ENVIRONMENT_INVITATION_REQUEST.append(LIST_ENVIRONMENT_OMICS_RUNS)
ENVIRONMENT_INVITATION_REQUEST.append(CREATE_OMICS_RUN)

TENANT_ALL.append(MANAGE_OMICS_RUNS)
TENANT_ALL_WITH_DESC[MANAGE_OMICS_RUNS] = "Manage Omics workflow runs"


RESOURCES_ALL.append(CREATE_OMICS_RUN)
RESOURCES_ALL.extend(OMICS_RUN_ALL)
RESOURCES_ALL.append(LIST_ENVIRONMENT_OMICS_RUNS)

RESOURCES_ALL_WITH_DESC[CREATE_OMICS_RUN] = "Create Omics workflow runs on this environment"
RESOURCES_ALL_WITH_DESC[LIST_ENVIRONMENT_OMICS_RUNS] = "List Omics workflow runs on this environment"
RESOURCES_ALL_WITH_DESC[GET_OMICS_RUN] = "General permission to list Omics workflow runs"
RESOURCES_ALL_WITH_DESC[DELETE_OMICS_RUN] = "Permission to delete Omics workflow runs"
RESOURCES_ALL_WITH_DESC[UPDATE_OMICS_RUN] = "Permission to edit Omics workflow runs"

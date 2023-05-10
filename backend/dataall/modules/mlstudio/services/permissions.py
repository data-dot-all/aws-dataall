"""
Add module's permissions to the global permissions.
Contains permissions for sagemaker ML Studio
"""

from dataall.db.permissions import (
    ENVIRONMENT_ALL,
    ENVIRONMENT_INVITED,
    RESOURCES_ALL_WITH_DESC,
    RESOURCES_ALL,
    ENVIRONMENT_INVITATION_REQUEST,
    TENANT_ALL,
    TENANT_ALL_WITH_DESC
)


CREATE_SGMSTUDIO_USER = 'CREATE_SGMSTUDIO_USER'
LIST_ENVIRONMENT_SGMSTUDIO_USERS = 'LIST_ENVIRONMENT_SGMSTUDIO_USERS'

MANAGE_SGMSTUDIO_USERS = 'MANAGE_SGMSTUDIO_USERS'

GET_SGMSTUDIO_USER = 'GET_SGMSTUDIO_USER'
UPDATE_SGMSTUDIO_USER = 'UPDATE_SGMSTUDIO_USER'
DELETE_SGMSTUDIO_USER = 'DELETE_SGMSTUDIO_USER'
SGMSTUDIO_USER_URL = 'SGMSTUDIO_USER_URL'

SGMSTUDIO_USER_ALL = [
    GET_SGMSTUDIO_USER,
    UPDATE_SGMSTUDIO_USER,
    DELETE_SGMSTUDIO_USER,
    SGMSTUDIO_USER_URL,
]

ENVIRONMENT_ALL.append(CREATE_SGMSTUDIO_USER)
ENVIRONMENT_ALL.append(LIST_ENVIRONMENT_SGMSTUDIO_USERS)
ENVIRONMENT_INVITED.append(CREATE_SGMSTUDIO_USER)
ENVIRONMENT_INVITED.append(LIST_ENVIRONMENT_SGMSTUDIO_USERS)
ENVIRONMENT_INVITATION_REQUEST.append(CREATE_SGMSTUDIO_USER)

TENANT_ALL.append(MANAGE_SGMSTUDIO_USERS)
TENANT_ALL_WITH_DESC[MANAGE_SGMSTUDIO_USERS] = 'Manage SageMaker Studio users'

RESOURCES_ALL.append(SGMSTUDIO_USER_ALL)
RESOURCES_ALL_WITH_DESC[CREATE_SGMSTUDIO_USER] = 'Create SageMaker Studio users on this environment'

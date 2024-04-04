from dataall.core.permissions.services.permissions_constants.resources_permissions import (
    RESOURCES_ALL,
    RESOURCES_ALL_WITH_DESC,
)
from dataall.core.permissions.services.permissions_constants.environment_permissions import (
    ENVIRONMENT_INVITED,
    ENVIRONMENT_INVITATION_REQUEST,
    ENVIRONMENT_ALL,
)

from dataall.core.permissions.services.permissions_constants.tenant_permissions import TENANT_ALL, TENANT_ALL_WITH_DESC

MANAGE_WORKSHEETS = 'MANAGE_WORKSHEETS'

TENANT_ALL.append(MANAGE_WORKSHEETS)
TENANT_ALL_WITH_DESC[MANAGE_WORKSHEETS] = 'Manage worksheets'

"""
WORKSHEETS
"""
GET_WORKSHEET = 'GET_WORKSHEET'
UPDATE_WORKSHEET = 'UPDATE_WORKSHEET'
DELETE_WORKSHEET = 'DELETE_WORKSHEET'
RUN_WORKSHEET_QUERY = 'RUN_WORKSHEET_QUERY'
WORKSHEET_ALL = [
    GET_WORKSHEET,
    UPDATE_WORKSHEET,
    DELETE_WORKSHEET,
    RUN_WORKSHEET_QUERY,
]

RESOURCES_ALL.extend(WORKSHEET_ALL)

for perm in WORKSHEET_ALL:
    RESOURCES_ALL_WITH_DESC[perm] = perm

"""
RUN ATHENA QUERY
"""
RUN_ATHENA_QUERY = 'RUN_ATHENA_QUERY'

ENVIRONMENT_INVITED.append(RUN_ATHENA_QUERY)

ENVIRONMENT_INVITATION_REQUEST.append(RUN_ATHENA_QUERY)

ENVIRONMENT_ALL.append(RUN_ATHENA_QUERY)

RESOURCES_ALL.append(RUN_ATHENA_QUERY)
RESOURCES_ALL_WITH_DESC[RUN_ATHENA_QUERY] = 'Run Worksheet Athena queries on this environment'

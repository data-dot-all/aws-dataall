from itertools import chain
from dataall.core.permissions.services.tenant_permissions import TENANT_ALL, TENANT_ALL_WITH_DESC
from dataall.core.permissions.services.environment_permissions import (
    ENVIRONMENT_INVITED,
    ENVIRONMENT_INVITATION_REQUEST,
    ENVIRONMENT_INVITED_DEFAULT,
    ENVIRONMENT_ALL,
)
from dataall.core.permissions.services.resources_permissions import (
    RESOURCES_ALL,
    RESOURCES_ALL_WITH_DESC,
)

"""
REDSHIFT CONNECTION TENANT PERMISSIONS
"""

MANAGE_REDSHIFT_CONNECTIONS = 'MANAGE_REDSHIFT_CONNECTIONS'

TENANT_ALL.append(MANAGE_REDSHIFT_CONNECTIONS)
TENANT_ALL_WITH_DESC[MANAGE_REDSHIFT_CONNECTIONS] = 'Manage Redshift connections'

"""
REDSHIFT CONNECTION PERMISSIONS
"""
GET_REDSHIFT_CONNECTION = 'GET_REDSHIFT_CONNECTION'
REDSHIFT_CONNECTION_READ = [GET_REDSHIFT_CONNECTION]

DELETE_REDSHIFT_CONNECTION = 'DELETE_REDSHIFT_CONNECTION'
EDIT_REDSHIFT_CONNECTION_PERMISSIONS = 'EDIT_REDSHIFT_CONNECTION_PERMISSIONS'
REDSHIFT_CONNECTION_WRITE = [DELETE_REDSHIFT_CONNECTION, EDIT_REDSHIFT_CONNECTION_PERMISSIONS]

CREATE_SHARE_REQUEST_WITH_CONNECTION = 'CREATE_SHARE_REQUEST_WITH_CONNECTION'
REDSHIFT_GRANTABLE_PERMISSIONS = [CREATE_SHARE_REQUEST_WITH_CONNECTION]

REDSHIFT_CONNECTION_ALL = list(set(REDSHIFT_CONNECTION_WRITE + REDSHIFT_CONNECTION_READ))
RESOURCES_ALL.extend(REDSHIFT_CONNECTION_ALL)

for perm in chain(REDSHIFT_CONNECTION_ALL):
    RESOURCES_ALL_WITH_DESC[perm] = perm

RESOURCES_ALL_WITH_DESC[CREATE_SHARE_REQUEST_WITH_CONNECTION] = 'Use Connection in share request'

"""
REDSHIFT CONNECTION PERMISSIONS FOR ENVIRONMENT
"""

LIST_ENVIRONMENT_REDSHIFT_CONNECTIONS = 'LIST_ENVIRONMENT_REDSHIFT_CONNECTIONS'
CREATE_REDSHIFT_CONNECTION = 'CREATE_REDSHIFT_CONNECTION'

ENVIRONMENT_INVITED.append(LIST_ENVIRONMENT_REDSHIFT_CONNECTIONS)
ENVIRONMENT_INVITED.append(CREATE_REDSHIFT_CONNECTION)

ENVIRONMENT_INVITATION_REQUEST.append(CREATE_REDSHIFT_CONNECTION)  # Selectable in invitation toogle
ENVIRONMENT_INVITED_DEFAULT.append(LIST_ENVIRONMENT_REDSHIFT_CONNECTIONS)  # Granted by default


ENVIRONMENT_ALL.append(LIST_ENVIRONMENT_REDSHIFT_CONNECTIONS)
ENVIRONMENT_ALL.append(CREATE_REDSHIFT_CONNECTION)

RESOURCES_ALL.append(LIST_ENVIRONMENT_REDSHIFT_CONNECTIONS)
RESOURCES_ALL.append(CREATE_REDSHIFT_CONNECTION)
RESOURCES_ALL_WITH_DESC[LIST_ENVIRONMENT_REDSHIFT_CONNECTIONS] = 'LIST_ENVIRONMENT_REDSHIFT_CONNECTIONS'
RESOURCES_ALL_WITH_DESC[CREATE_REDSHIFT_CONNECTION] = 'Create Redshift Connection in this environment'

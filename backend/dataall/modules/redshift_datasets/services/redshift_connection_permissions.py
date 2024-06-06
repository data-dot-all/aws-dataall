from itertools import chain
from dataall.core.permissions.services.environment_permissions import (
    ENVIRONMENT_INVITED,
    ENVIRONMENT_INVITED_DEFAULT,
    ENVIRONMENT_ALL,
)
from dataall.core.permissions.services.resources_permissions import (
    RESOURCES_ALL,
    RESOURCES_ALL_WITH_DESC,
)

# No tenant permissions because it is already covered with MANAGE_REDSHIFT_DATASETS

"""
REDSHIFT CONNECTION PERMISSIONS
"""
GET_REDSHIFT_CONNECTION = 'GET_REDSHIFT_CONNECTION'

REDSHIFT_CONNECTION_READ = [GET_REDSHIFT_CONNECTION]

UPDATE_REDSHIFT_CONNECTION = 'UPDATE_REDSHIFT_CONNECTION'
DELETE_REDSHIFT_CONNECTION = 'DELETE_REDSHIFT_CONNECTION'
USE_REDSHIFT_CONNECTION = 'USE_REDSHIFT_CONNECTION'

REDSHIFT_CONNECTION_WRITE = [
    UPDATE_REDSHIFT_CONNECTION,
    DELETE_REDSHIFT_CONNECTION,
    USE_REDSHIFT_CONNECTION,
]
REDSHIFT_CONNECTION_ALL = list(set(REDSHIFT_CONNECTION_WRITE + REDSHIFT_CONNECTION_READ))
RESOURCES_ALL.extend(REDSHIFT_CONNECTION_ALL)

for perm in chain(REDSHIFT_CONNECTION_ALL):
    RESOURCES_ALL_WITH_DESC[perm] = perm


"""
CONNECTION PERMISSIONS FOR ENVIRONMENT
"""

LIST_ENVIRONMENT_REDSHIFT_CONNECTIONS = 'LIST_ENVIRONMENT_REDSHIFT_CONNECTIONS'

ENVIRONMENT_INVITED.append(LIST_ENVIRONMENT_REDSHIFT_CONNECTIONS)
ENVIRONMENT_INVITED_DEFAULT.append(LIST_ENVIRONMENT_REDSHIFT_CONNECTIONS)
ENVIRONMENT_ALL.append(LIST_ENVIRONMENT_REDSHIFT_CONNECTIONS)

RESOURCES_ALL.append(LIST_ENVIRONMENT_REDSHIFT_CONNECTIONS)
RESOURCES_ALL_WITH_DESC[LIST_ENVIRONMENT_REDSHIFT_CONNECTIONS] = 'LIST_ENVIRONMENT_REDSHIFT_CONNECTIONS'

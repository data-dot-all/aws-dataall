from itertools import chain

from dataall.core.permissions.services.environment_permissions import (
    ENVIRONMENT_INVITED,
    ENVIRONMENT_INVITATION_REQUEST,
    ENVIRONMENT_ALL,
)
from dataall.core.permissions.services.tenant_permissions import TENANT_ALL, TENANT_ALL_WITH_DESC
from dataall.core.permissions.services.resources_permissions import (
    RESOURCES_ALL,
    RESOURCES_ALL_WITH_DESC,
)

MANAGE_REDSHIFT_DATASETS = 'MANAGE_REDSHIFT_DATASETS'

TENANT_ALL.append(MANAGE_REDSHIFT_DATASETS)
TENANT_ALL_WITH_DESC[MANAGE_REDSHIFT_DATASETS] = 'Manage datasets'

"""
REDSHIFT DATASET PERMISSIONS
"""

GET_REDSHIFT_DATASET = 'GET_REDSHIFT_DATASET'

REDSHIFT_DATASET_READ = [GET_REDSHIFT_DATASET]

DELETE_REDSHIFT_DATASET = 'DELETE_REDSHIFT_DATASET'

REDSHIFT_DATASET_WRITE = [
    DELETE_REDSHIFT_DATASET,
]

REDSHIFT_DATASET_ALL = list(set(REDSHIFT_DATASET_WRITE + REDSHIFT_DATASET_READ))
RESOURCES_ALL.extend(REDSHIFT_DATASET_ALL)


"""
DATASET PERMISSIONS FOR ENVIRONMENT
"""

IMPORT_REDSHIFT_DATASET = 'IMPORT_REDSHIFT_DATASET'

ENVIRONMENT_INVITED.append(IMPORT_REDSHIFT_DATASET)

ENVIRONMENT_INVITATION_REQUEST.append(IMPORT_REDSHIFT_DATASET)

ENVIRONMENT_ALL.append(IMPORT_REDSHIFT_DATASET)

RESOURCES_ALL.append(IMPORT_REDSHIFT_DATASET)

for perm in chain(REDSHIFT_DATASET_ALL):
    RESOURCES_ALL_WITH_DESC[perm] = perm

RESOURCES_ALL_WITH_DESC[IMPORT_REDSHIFT_DATASET] = 'Import redshift datasets on this environment'

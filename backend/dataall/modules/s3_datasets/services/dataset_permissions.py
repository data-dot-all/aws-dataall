from itertools import chain

from dataall.core.permissions.services.environment_permissions import (
    ENVIRONMENT_INVITED,
    ENVIRONMENT_INVITATION_REQUEST,
    ENVIRONMENT_INVITED_DEFAULT,
    ENVIRONMENT_ALL,
)
from dataall.core.permissions.services.tenant_permissions import TENANT_ALL, TENANT_ALL_WITH_DESC
from dataall.core.permissions.services.resources_permissions import (
    RESOURCES_ALL,
    RESOURCES_ALL_WITH_DESC,
)

MANAGE_DATASETS = 'MANAGE_DATASETS'

TENANT_ALL.append(MANAGE_DATASETS)
TENANT_ALL_WITH_DESC[MANAGE_DATASETS] = 'Manage datasets'

"""
DATASET PERMISSIONS
"""

GET_DATASET = 'GET_DATASET'
LIST_DATASET_FOLDERS = 'LIST_DATASET_FOLDERS'
CREDENTIALS_DATASET = 'CREDENTIALS_DATASET'

DATASET_READ = [
    GET_DATASET,
    LIST_DATASET_FOLDERS,
    CREDENTIALS_DATASET,
]

UPDATE_DATASET = 'UPDATE_DATASET'
SYNC_DATASET = 'SYNC_DATASET'
CRAWL_DATASET = 'CRAWL_DATASET'
DELETE_DATASET = 'DELETE_DATASET'
IMPORT_DATASET = 'IMPORT_DATASET'
DELETE_DATASET_TABLE = 'DELETE_DATASET_TABLE'
UPDATE_DATASET_TABLE = 'UPDATE_DATASET_TABLE'
PROFILE_DATASET_TABLE = 'PROFILE_DATASET_TABLE'
CREATE_DATASET_FOLDER = 'CREATE_DATASET_FOLDER'
DELETE_DATASET_FOLDER = 'DELETE_DATASET_FOLDER'
UPDATE_DATASET_FOLDER = 'UPDATE_DATASET_FOLDER'

DATASET_WRITE = [
    UPDATE_DATASET,
    SYNC_DATASET,
    IMPORT_DATASET,
    CREDENTIALS_DATASET,
    CRAWL_DATASET,
    DELETE_DATASET,
    UPDATE_DATASET_TABLE,
    DELETE_DATASET_TABLE,
    PROFILE_DATASET_TABLE,
    CREATE_DATASET_FOLDER,
    DELETE_DATASET_FOLDER,
    UPDATE_DATASET_FOLDER,
    LIST_DATASET_FOLDERS,
]

DATASET_ALL = list(set(DATASET_WRITE + DATASET_READ))
RESOURCES_ALL.extend(DATASET_ALL)

"""
DATASET TABLE PERMISSIONS
"""

GET_DATASET_TABLE = 'GET_DATASET_TABLE'
PREVIEW_DATASET_TABLE = 'PREVIEW_DATASET_TABLE'

DATASET_TABLE_READ = [GET_DATASET_TABLE, PREVIEW_DATASET_TABLE]

"""
DATASET FOLDER PERMISSIONS
"""
GET_DATASET_FOLDER = 'GET_DATASET_FOLDER'

DATASET_FOLDER_READ = [GET_DATASET_FOLDER]


RESOURCES_ALL.extend(DATASET_TABLE_READ)
RESOURCES_ALL.extend(DATASET_FOLDER_READ)

"""
DATASET PERMISSIONS FOR ENVIRONMENT
"""

CREATE_DATASET = 'CREATE_DATASET'

ENVIRONMENT_INVITED.append(CREATE_DATASET)

ENVIRONMENT_INVITATION_REQUEST.append(CREATE_DATASET)

ENVIRONMENT_ALL.append(CREATE_DATASET)

RESOURCES_ALL.append(CREATE_DATASET)

for perm in chain(DATASET_ALL, DATASET_TABLE_READ, DATASET_FOLDER_READ):
    RESOURCES_ALL_WITH_DESC[perm] = perm

RESOURCES_ALL_WITH_DESC[CREATE_DATASET] = 'Create datasets on this environment'

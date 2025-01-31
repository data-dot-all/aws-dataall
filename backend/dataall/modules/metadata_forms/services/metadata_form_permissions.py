from dataall.core.permissions.services.environment_permissions import ENVIRONMENT_INVITED, ENVIRONMENT_ALL
from dataall.core.permissions.services.organization_permissions import (
    ORGANIZATION_ALL,
    ORGANIZATION_INVITED_DESCRIPTIONS,
)
from dataall.core.permissions.services.tenant_permissions import TENANT_ALL, TENANT_ALL_WITH_DESC
from dataall.core.permissions.services.resources_permissions import RESOURCES_ALL, RESOURCES_ALL_WITH_DESC
from dataall.modules.s3_datasets.services.dataset_permissions import DATASET_WRITE, DATASET_ALL

# ------------------------TENANT-----------------------------------
MANAGE_METADATA_FORMS = 'MANAGE_METADATA_FORMS'
TENANT_ALL.append(MANAGE_METADATA_FORMS)
TENANT_ALL_WITH_DESC[MANAGE_METADATA_FORMS] = 'Manage metadata forms'

# ------------------------RESOURCE---------------------------------
# permissions to attach MF to the entity, ot make the entity the visibility base for MF
# these permissions are attached to Organizations, Environments, Datasets etc.
ATTACH_METADATA_FORM = 'ATTACH_METADATA_FORM'
CREATE_METADATA_FORM = 'CREATE_METADATA_FORM'
ENFORCE_METADATA_FORM = 'ENFORCE_METADATA_FORM'
ALL_METADATA_FORMS_ENTITY_PERMISSIONS = [ENFORCE_METADATA_FORM, ATTACH_METADATA_FORM, CREATE_METADATA_FORM]
RESOURCES_ALL.extend(ALL_METADATA_FORMS_ENTITY_PERMISSIONS)
RESOURCES_ALL_WITH_DESC[CREATE_METADATA_FORM] = 'Create metadata form within this visibility scope'
RESOURCES_ALL_WITH_DESC[ENFORCE_METADATA_FORM] = 'Enforce metadata form within this visibility scope'
RESOURCES_ALL_WITH_DESC[ATTACH_METADATA_FORM] = 'Attach metadata form'

ORGANIZATION_ALL.extend(ALL_METADATA_FORMS_ENTITY_PERMISSIONS)
ORGANIZATION_INVITED_DESCRIPTIONS[CREATE_METADATA_FORM] = 'Create metadata form within this organization'
ORGANIZATION_INVITED_DESCRIPTIONS[ENFORCE_METADATA_FORM] = 'Enforce metadata form within this organization'
ORGANIZATION_INVITED_DESCRIPTIONS[ATTACH_METADATA_FORM] = 'Attach metadata form'

ENVIRONMENT_INVITED.extend(ALL_METADATA_FORMS_ENTITY_PERMISSIONS)
ENVIRONMENT_ALL.extend(ALL_METADATA_FORMS_ENTITY_PERMISSIONS)

DATASET_WRITE.extend(ALL_METADATA_FORMS_ENTITY_PERMISSIONS)
DATASET_ALL.extend(ALL_METADATA_FORMS_ENTITY_PERMISSIONS)
# ------------------------METADATA FORM----------------------------
# permissions to change and delete metadata forms
# these permissions are attached to MFs
UPDATE_METADATA_FORM_FIELD = 'UPDATE_METADATA_FORM_FIELD'
DELETE_METADATA_FORM_FIELD = 'DELETE_METADATA_FORM_FIELD'
DELETE_METADATA_FORM = 'DELETE_METADATA_FORM'
EDIT_METADATA_FORM = 'EDIT_METADATA_FORM'

METADATA_FORM_PERMISSIONS_ALL = [
    UPDATE_METADATA_FORM_FIELD,
    DELETE_METADATA_FORM_FIELD,
    DELETE_METADATA_FORM,
    EDIT_METADATA_FORM,
]

METADATA_FORM_EDIT_PERMISSIONS = [
    EDIT_METADATA_FORM,
    UPDATE_METADATA_FORM_FIELD,
    DELETE_METADATA_FORM_FIELD,
]

RESOURCES_ALL.extend(METADATA_FORM_PERMISSIONS_ALL)

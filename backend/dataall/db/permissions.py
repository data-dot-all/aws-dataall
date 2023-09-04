"""
ORGANIZATION PERMISSIONS
"""
CREATE_ORGANIZATION = 'CREATE_ORGANIZATION'
UPDATE_ORGANIZATION = 'UPDATE_ORGANIZATION'
DELETE_ORGANIZATION = 'DELETE_ORGANIZATION'
GET_ORGANIZATION = 'GET_ORGANIZATION'
LINK_ENVIRONMENT = 'LINK_ENVIRONMENT'
INVITE_ORGANIZATION_GROUP = 'INVITE_ORGANIZATION_GROUP'
REMOVE_ORGANIZATION_GROUP = 'REMOVE_ORGANIZATION_GROUP'
ORGANIZATION_ALL = [
    CREATE_ORGANIZATION,
    UPDATE_ORGANIZATION,
    DELETE_ORGANIZATION,
    LINK_ENVIRONMENT,
    GET_ORGANIZATION,
    INVITE_ORGANIZATION_GROUP,
    REMOVE_ORGANIZATION_GROUP,
]
ORGANIZATION_INVITED = [LINK_ENVIRONMENT, GET_ORGANIZATION]

"""
TENANT PERMISSIONS
"""
MANAGE_DATASETS = 'MANAGE_DATASETS'
MANAGE_REDSHIFT_CLUSTERS = 'MANAGE_REDSHIFT_CLUSTERS'
MANAGE_DASHBOARDS = 'MANAGE_DASHBOARDS'
MANAGE_NOTEBOOKS = 'MANAGE_NOTEBOOKS'
MANAGE_PIPELINES = 'MANAGE_PIPELINES'
MANAGE_GROUPS = 'MANAGE_GROUPS'
MANAGE_ENVIRONMENT = 'MANAGE_ENVIRONMENT'
MANAGE_WORKSHEETS = 'MANAGE_WORKSHEETS'
MANAGE_GLOSSARIES = 'MANAGE_GLOSSARIES'
MANAGE_ENVIRONMENTS = 'MANAGE_ENVIRONMENTS'
MANAGE_ORGANIZATIONS = 'MANAGE_ORGANIZATIONS'

"""
ENVIRONMENT
"""
UPDATE_ENVIRONMENT = 'UPDATE_ENVIRONMENT'
GET_ENVIRONMENT = 'GET_ENVIRONMENT'
DELETE_ENVIRONMENT = 'DELETE_ENVIRONMENT'
INVITE_ENVIRONMENT_GROUP = 'INVITE_ENVIRONMENT_GROUP'
REMOVE_ENVIRONMENT_GROUP = 'REMOVE_ENVIRONMENT_GROUP'
UPDATE_ENVIRONMENT_GROUP = 'UPDATE_ENVIRONMENT_GROUP'
ADD_ENVIRONMENT_CONSUMPTION_ROLES = 'ADD_ENVIRONMENT_CONSUMPTION_ROLES'
LIST_ENVIRONMENT_CONSUMPTION_ROLES = 'LIST_ENVIRONMENT_CONSUMPTION_ROLES'
LIST_ENVIRONMENT_GROUP_PERMISSIONS = 'LIST_ENVIRONMENT_GROUP_PERMISSIONS'
LIST_ENVIRONMENT_DATASETS = 'LIST_ENVIRONMENT_DATASETS'
LIST_ENVIRONMENT_GROUPS = 'LIST_ENVIRONMENT_GROUPS'
CREDENTIALS_ENVIRONMENT = 'CREDENTIALS_ENVIRONMENT'
ENABLE_ENVIRONMENT_SUBSCRIPTIONS = 'ENABLE_ENVIRONMENT_SUBSCRIPTIONS'
DISABLE_ENVIRONMENT_SUBSCRIPTIONS = 'DISABLE_ENVIRONMENT_SUBSCRIPTIONS'
RUN_ATHENA_QUERY = 'RUN_ATHENA_QUERY'
CREATE_DATASET = 'CREATE_DATASET'
CREATE_SHARE_OBJECT = 'CREATE_SHARE_OBJECT'
LIST_ENVIRONMENT_SHARED_WITH_OBJECTS = 'LIST_ENVIRONMENT_SHARED_WITH_OBJECTS'
CREATE_REDSHIFT_CLUSTER = 'CREATE_REDSHIFT_CLUSTER'
LIST_ENVIRONMENT_REDSHIFT_CLUSTERS = 'LIST_ENVIRONMENT_REDSHIFT_CLUSTERS'
CREATE_NOTEBOOK = 'CREATE_NOTEBOOK'
LIST_ENVIRONMENT_NOTEBOOKS = 'LIST_ENVIRONMENT_NOTEBOOKS'
CREATE_SGMSTUDIO_NOTEBOOK = 'CREATE_SGMSTUDIO_NOTEBOOK'
LIST_ENVIRONMENT_SGMSTUDIO_NOTEBOOKS = 'LIST_ENVIRONMENT_SGMSTUDIO_NOTEBOOKS'
CREATE_DASHBOARD = 'CREATE_DASHBOARD'
LIST_ENVIRONMENT_DASHBOARDS = 'LIST_ENVIRONMENT_DASHBOARDS'
CREATE_PIPELINE = 'CREATE_PIPELINE'
LIST_PIPELINES = 'LIST_PIPELINES'
CREATE_NETWORK = 'CREATE_NETWORK'
LIST_ENVIRONMENT_NETWORKS = 'LIST_ENVIRONMENT_NETWORKS'


ENVIRONMENT_INVITED = [
    CREATE_DATASET,
    LIST_ENVIRONMENT_GROUP_PERMISSIONS,
    GET_ENVIRONMENT,
    LIST_ENVIRONMENT_DATASETS,
    LIST_ENVIRONMENT_GROUPS,
    LIST_ENVIRONMENT_CONSUMPTION_ROLES,
    CREATE_SHARE_OBJECT,
    LIST_ENVIRONMENT_SHARED_WITH_OBJECTS,
    RUN_ATHENA_QUERY,
    CREATE_REDSHIFT_CLUSTER,
    LIST_ENVIRONMENT_REDSHIFT_CLUSTERS,
    CREATE_NOTEBOOK,
    LIST_ENVIRONMENT_NOTEBOOKS,
    CREATE_SGMSTUDIO_NOTEBOOK,
    LIST_ENVIRONMENT_SGMSTUDIO_NOTEBOOKS,
    CREATE_DASHBOARD,
    LIST_ENVIRONMENT_DASHBOARDS,
    INVITE_ENVIRONMENT_GROUP,
    ADD_ENVIRONMENT_CONSUMPTION_ROLES,
    CREATE_PIPELINE,
    LIST_PIPELINES,
    CREATE_NETWORK,
    LIST_ENVIRONMENT_NETWORKS,
]
ENVIRONMENT_INVITATION_REQUEST = [
    INVITE_ENVIRONMENT_GROUP,
    ADD_ENVIRONMENT_CONSUMPTION_ROLES,
    CREATE_DATASET,
    CREATE_SHARE_OBJECT,
    CREATE_REDSHIFT_CLUSTER,
    CREATE_SGMSTUDIO_NOTEBOOK,
    CREATE_NOTEBOOK,
    CREATE_DASHBOARD,
    CREATE_PIPELINE,
    CREATE_NETWORK,
]
ENVIRONMENT_ALL = [
    UPDATE_ENVIRONMENT,
    GET_ENVIRONMENT,
    DELETE_ENVIRONMENT,
    INVITE_ENVIRONMENT_GROUP,
    REMOVE_ENVIRONMENT_GROUP,
    UPDATE_ENVIRONMENT_GROUP,
    LIST_ENVIRONMENT_GROUP_PERMISSIONS,
    ADD_ENVIRONMENT_CONSUMPTION_ROLES,
    LIST_ENVIRONMENT_CONSUMPTION_ROLES,
    LIST_ENVIRONMENT_DATASETS,
    LIST_ENVIRONMENT_GROUPS,
    CREDENTIALS_ENVIRONMENT,
    ENABLE_ENVIRONMENT_SUBSCRIPTIONS,
    DISABLE_ENVIRONMENT_SUBSCRIPTIONS,
    RUN_ATHENA_QUERY,
    CREATE_DATASET,
    CREATE_SHARE_OBJECT,
    CREATE_REDSHIFT_CLUSTER,
    LIST_ENVIRONMENT_REDSHIFT_CLUSTERS,
    CREATE_NOTEBOOK,
    LIST_ENVIRONMENT_NOTEBOOKS,
    LIST_ENVIRONMENT_SHARED_WITH_OBJECTS,
    CREATE_SGMSTUDIO_NOTEBOOK,
    LIST_ENVIRONMENT_SGMSTUDIO_NOTEBOOKS,
    CREATE_DASHBOARD,
    LIST_ENVIRONMENT_DASHBOARDS,
    CREATE_PIPELINE,
    LIST_PIPELINES,
    CREATE_NETWORK,
    LIST_ENVIRONMENT_NETWORKS,
]
"""
CONSUMPTION_ROLE
"""
REMOVE_ENVIRONMENT_CONSUMPTION_ROLE = 'REMOVE_ENVIRONMENT_CONSUMPTION_ROLE'
CONSUMPTION_ENVIRONMENT_ROLE_ALL = [
    LIST_ENVIRONMENT_CONSUMPTION_ROLES,
    ADD_ENVIRONMENT_CONSUMPTION_ROLES
]
CONSUMPTION_ROLE_ALL = [
    REMOVE_ENVIRONMENT_CONSUMPTION_ROLE
]

"""
SHARE OBJECT
"""
ADD_ITEM = 'ADD_ITEM'
REMOVE_ITEM = 'REMOVE_ITEM'
SUBMIT_SHARE_OBJECT = 'SUBMIT_SHARE_OBJECT'
APPROVE_SHARE_OBJECT = 'APPROVE_SHARE_OBJECT'
REJECT_SHARE_OBJECT = 'REJECT_SHARE_OBJECT'
DELETE_SHARE_OBJECT = 'DELETE_SHARE_OBJECT'
GET_SHARE_OBJECT = 'GET_SHARE_OBJECT'
LIST_SHARED_ITEMS = 'LIST_SHARED_ITEMS'
SHARE_OBJECT_REQUESTER = [
    ADD_ITEM,
    REMOVE_ITEM,
    SUBMIT_SHARE_OBJECT,
    GET_SHARE_OBJECT,
    LIST_SHARED_ITEMS,
    DELETE_SHARE_OBJECT,
]
SHARE_OBJECT_APPROVER = [
    ADD_ITEM,
    REMOVE_ITEM,
    APPROVE_SHARE_OBJECT,
    REJECT_SHARE_OBJECT,
    DELETE_SHARE_OBJECT,
    GET_SHARE_OBJECT,
    LIST_SHARED_ITEMS,
]
SHARE_OBJECT_ALL = [
    ADD_ITEM,
    REMOVE_ITEM,
    SUBMIT_SHARE_OBJECT,
    APPROVE_SHARE_OBJECT,
    REJECT_SHARE_OBJECT,
    DELETE_SHARE_OBJECT,
    GET_SHARE_OBJECT,
    LIST_SHARED_ITEMS,
]
"""
DATASET PERMISSIONS
"""
GET_DATASET = 'GET_DATASET'
UPDATE_DATASET = 'UPDATE_DATASET'
SYNC_DATASET = 'SYNC_DATASET'
SUMMARY_DATASET = 'SUMMARY_DATASET'
IMPORT_DATASET = 'IMPORT_DATASET'
UPLOAD_DATASET = 'UPLOAD_DATASET'
LIST_DATASETS = 'LIST_DATASETS'
CREDENTIALS_DATASET = 'CREDENTIALS_DATASET'
URL_DATASET = 'URL_DATASET'
CRAWL_DATASET = 'CRAWL_DATASET'
DELETE_DATASET = 'DELETE_DATASET'
STACK_DATASET = 'STACK_DATASET'
SUBSCRIPTIONS_DATASET = 'SUBSCRIPTIONS_DATASET'
CREATE_DATASET_TABLE = 'CREATE_DATASET_TABLE'
DELETE_DATASET_TABLE = 'DELETE_DATASET_TABLE'
UPDATE_DATASET_TABLE = 'UPDATE_DATASET_TABLE'
PROFILE_DATASET_TABLE = 'PROFILE_DATASET_TABLE'
LIST_DATASET_TABLES = 'LIST_DATASET_TABLES'
LIST_DATASET_SHARES = 'LIST_DATASET_SHARES'
CREATE_DATASET_FOLDER = 'CREATE_DATASET_FOLDER'
DELETE_DATASET_FOLDER = 'DELETE_DATASET_FOLDER'
GET_DATASET_FOLDER = 'DELETE_DATASET_FOLDER'
LIST_DATASET_FOLDERS = 'LIST_DATASET_FOLDERS'
UPDATE_DATASET_FOLDER = 'UPDATE_DATASET_FOLDER'
DATASET_WRITE = [
    UPDATE_DATASET,
    SYNC_DATASET,
    SUMMARY_DATASET,
    IMPORT_DATASET,
    UPLOAD_DATASET,
    CREDENTIALS_DATASET,
    URL_DATASET,
    CRAWL_DATASET,
    DELETE_DATASET,
    STACK_DATASET,
    SUBSCRIPTIONS_DATASET,
    UPDATE_DATASET_TABLE,
    DELETE_DATASET_TABLE,
    CREATE_DATASET_TABLE,
    PROFILE_DATASET_TABLE,
    LIST_DATASET_SHARES,
    CREATE_DATASET_FOLDER,
    DELETE_DATASET_FOLDER,
    UPDATE_DATASET_FOLDER,
    LIST_DATASET_FOLDERS,
]

DATASET_READ = [
    GET_DATASET,
    LIST_DATASETS,
    LIST_DATASET_TABLES,
    LIST_DATASET_SHARES,
    LIST_DATASET_FOLDERS,
    CREDENTIALS_DATASET,
]

DATASET_ALL = list(set(DATASET_WRITE + DATASET_READ))

"""
DATASET TABLE PERMISSIONS
"""
GET_DATASET_TABLE = 'GET_DATASET_TABLE'
PREVIEW_DATASET_TABLE = 'PREVIEW_DATASET_TABLE'

DATASET_TABLE_READ = [
    GET_DATASET_TABLE,
    PREVIEW_DATASET_TABLE
]

"""
GLOSSARIES
"""
CREATE_CATEGORY = 'CREATE_CATEGORY'
CREATE_TERM = 'CREATE_TERM'
UPDATE_NODE = 'UPDATE_NODE'
DELETE_GLOSSARY = 'DELETE_GLOSSARY'
APPROVE_ASSOCIATION = 'APPROVE_ASSOCIATION'
GLOSSARY_ALL = [
    CREATE_CATEGORY,
    CREATE_TERM,
    UPDATE_NODE,
    DELETE_GLOSSARY,
    APPROVE_ASSOCIATION,
]
"""
TENANT ALL
"""

TENANT_ALL = [
    MANAGE_DATASETS,
    MANAGE_REDSHIFT_CLUSTERS,
    MANAGE_DASHBOARDS,
    MANAGE_NOTEBOOKS,
    MANAGE_PIPELINES,
    MANAGE_WORKSHEETS,
    MANAGE_GLOSSARIES,
    MANAGE_GROUPS,
    MANAGE_ENVIRONMENTS,
    MANAGE_ORGANIZATIONS,
]

TENANT_ALL_WITH_DESC = {k: k for k in TENANT_ALL}
TENANT_ALL_WITH_DESC[MANAGE_DASHBOARDS] = 'Manage dashboards'
TENANT_ALL_WITH_DESC[MANAGE_DATASETS] = 'Manage datasets'
TENANT_ALL_WITH_DESC[MANAGE_NOTEBOOKS] = 'Manage notebooks'
TENANT_ALL_WITH_DESC[MANAGE_REDSHIFT_CLUSTERS] = 'Manage Redshift clusters'
TENANT_ALL_WITH_DESC[MANAGE_GLOSSARIES] = 'Manage glossaries'
TENANT_ALL_WITH_DESC[MANAGE_WORKSHEETS] = 'Manage worksheets'
TENANT_ALL_WITH_DESC[MANAGE_ENVIRONMENTS] = 'Manage environments'
TENANT_ALL_WITH_DESC[MANAGE_GROUPS] = 'Manage teams'
TENANT_ALL_WITH_DESC[MANAGE_PIPELINES] = 'Manage pipelines'
TENANT_ALL_WITH_DESC[MANAGE_ORGANIZATIONS] = 'Manage organizations'

"""
REDSHIFT CLUSTER
"""
GET_REDSHIFT_CLUSTER = 'GET_REDSHIFT_CLUSTER'
SHARE_REDSHIFT_CLUSTER = 'SHARE_REDSHIFT_CLUSTER'
DELETE_REDSHIFT_CLUSTER = 'DELETE_REDSHIFT_CLUSTER'
REBOOT_REDSHIFT_CLUSTER = 'REBOOT_REDSHIFT_CLUSTER'
RESUME_REDSHIFT_CLUSTER = 'RESUME_REDSHIFT_CLUSTER'
PAUSE_REDSHIFT_CLUSTER = 'PAUSE_REDSHIFT_CLUSTER'
ADD_DATASET_TO_REDSHIFT_CLUSTER = 'ADD_DATASET_TO_REDSHIFT_CLUSTER'
LIST_REDSHIFT_CLUSTER_DATASETS = 'LIST_REDSHIFT_CLUSTER_DATASETS'
REMOVE_DATASET_FROM_REDSHIFT_CLUSTER = 'REMOVE_DATASET_FROM_REDSHIFT_CLUSTER'
ENABLE_REDSHIFT_TABLE_COPY = 'ENABLE_REDSHIFT_TABLE_COPY'
DISABLE_REDSHIFT_TABLE_COPY = 'DISABLE_REDSHIFT_TABLE_COPY'
GET_REDSHIFT_CLUSTER_CREDENTIALS = 'GET_REDSHIFT_CLUSTER_CREDENTIALS'
REDSHIFT_CLUSTER_ALL = [
    GET_REDSHIFT_CLUSTER,
    SHARE_REDSHIFT_CLUSTER,
    DELETE_REDSHIFT_CLUSTER,
    REBOOT_REDSHIFT_CLUSTER,
    RESUME_REDSHIFT_CLUSTER,
    PAUSE_REDSHIFT_CLUSTER,
    ADD_DATASET_TO_REDSHIFT_CLUSTER,
    LIST_REDSHIFT_CLUSTER_DATASETS,
    REMOVE_DATASET_FROM_REDSHIFT_CLUSTER,
    ENABLE_REDSHIFT_TABLE_COPY,
    DISABLE_REDSHIFT_TABLE_COPY,
    GET_REDSHIFT_CLUSTER_CREDENTIALS,
]

"""
NOTEBOOKS
"""
GET_NOTEBOOK = 'GET_NOTEBOOK'
UPDATE_NOTEBOOK = 'UPDATE_NOTEBOOK'
DELETE_NOTEBOOK = 'DELETE_NOTEBOOK'
NOTEBOOK_ALL = [
    GET_NOTEBOOK,
    DELETE_NOTEBOOK,
    UPDATE_NOTEBOOK,
]

"""
SAGEMAKER STUDIO NOTEBOOKS
"""
GET_SGMSTUDIO_NOTEBOOK = 'GET_SGMSTUDIO_NOTEBOOK'
UPDATE_SGMSTUDIO_NOTEBOOK = 'UPDATE_SGMSTUDIO_NOTEBOOK'
DELETE_SGMSTUDIO_NOTEBOOK = 'DELETE_SGMSTUDIO_NOTEBOOK'
SGMSTUDIO_NOTEBOOK_URL = 'SGMSTUDIO_NOTEBOOK_URL'
SGMSTUDIO_NOTEBOOK_ALL = [
    GET_SGMSTUDIO_NOTEBOOK,
    UPDATE_SGMSTUDIO_NOTEBOOK,
    DELETE_SGMSTUDIO_NOTEBOOK,
    SGMSTUDIO_NOTEBOOK_URL,
]

"""
DASHBOARDS
"""
GET_DASHBOARD = 'GET_DASHBOARD'
UPDATE_DASHBOARD = 'UPDATE_DASHBOARD'
DELETE_DASHBOARD = 'DELETE_DASHBOARD'
DASHBOARD_URL = 'DASHBOARD_URL'
SHARE_DASHBOARD = 'SHARE_DASHBOARD'
DASHBOARD_ALL = [
    GET_DASHBOARD,
    UPDATE_DASHBOARD,
    DELETE_DASHBOARD,
    DASHBOARD_URL,
    SHARE_DASHBOARD,
]

"""
PIPELINES
"""
GET_PIPELINE = 'GET_PIPELINE'
UPDATE_PIPELINE = 'UPDATE_PIPELINE'
DELETE_PIPELINE = 'DELETE_PIPELINE'
CREDENTIALS_PIPELINE = 'CREDENTIALS_PIPELINE'
START_PIPELINE = 'START_PIPELINE'
PIPELINE_ALL = [
    CREATE_PIPELINE,
    GET_PIPELINE,
    UPDATE_PIPELINE,
    DELETE_PIPELINE,
    CREDENTIALS_PIPELINE,
    START_PIPELINE,
    LIST_PIPELINES,
]

"""
WORKSHEETS
"""
GET_WORKSHEET = 'GET_WORKSHEET'
UPDATE_WORKSHEET = 'UPDATE_WORKSHEET'
DELETE_WORKSHEET = 'DELETE_WORKSHEET'
SHARE_WORKSHEET = 'SHARE_WORKSHEET'
RUN_WORKSHEET_QUERY = 'RUN_WORKSHEET_QUERY'
WORKSHEET_ALL = [
    GET_WORKSHEET,
    UPDATE_WORKSHEET,
    DELETE_WORKSHEET,
    SHARE_WORKSHEET,
    RUN_WORKSHEET_QUERY,
]
WORKSHEET_SHARED = [GET_WORKSHEET, UPDATE_WORKSHEET, RUN_WORKSHEET_QUERY]

"""
NETWORKS
"""
GET_NETWORK = 'GET_NETWORK'
UPDATE_NETWORK = 'UPDATE_NETWORK'
DELETE_NETWORK = 'DELETE_NETWORK'
NETWORK_ALL = [GET_NETWORK, UPDATE_NETWORK, DELETE_NETWORK]

"""
RESOURCES_ALL
"""

RESOURCES_ALL = (
    DATASET_ALL
    + DATASET_TABLE_READ
    + ORGANIZATION_ALL
    + ENVIRONMENT_ALL
    + CONSUMPTION_ROLE_ALL
    + SHARE_OBJECT_ALL
    + REDSHIFT_CLUSTER_ALL
    + NOTEBOOK_ALL
    + GLOSSARY_ALL
    + SGMSTUDIO_NOTEBOOK_ALL
    + DASHBOARD_ALL
    + WORKSHEET_ALL
    + PIPELINE_ALL
    + NETWORK_ALL
)

RESOURCES_ALL_WITH_DESC = {k: k for k in RESOURCES_ALL}
RESOURCES_ALL_WITH_DESC[CREATE_DATASET] = 'Create datasets on this environment'
RESOURCES_ALL_WITH_DESC[CREATE_DASHBOARD] = 'Create dashboards on this environment'
RESOURCES_ALL_WITH_DESC[CREATE_NOTEBOOK] = 'Create notebooks on this environment'
RESOURCES_ALL_WITH_DESC[CREATE_REDSHIFT_CLUSTER] = 'Create Redshift clusters on this environment'
RESOURCES_ALL_WITH_DESC[CREATE_SGMSTUDIO_NOTEBOOK] = 'Create ML Studio profiles on this environment'
RESOURCES_ALL_WITH_DESC[INVITE_ENVIRONMENT_GROUP] = 'Invite other teams to this environment'
RESOURCES_ALL_WITH_DESC[ADD_ENVIRONMENT_CONSUMPTION_ROLES] = 'Add IAM consumption roles to this environment'
RESOURCES_ALL_WITH_DESC[CREATE_SHARE_OBJECT] = 'Request datasets access for this environment'
RESOURCES_ALL_WITH_DESC[CREATE_PIPELINE] = 'Create pipelines on this environment'
RESOURCES_ALL_WITH_DESC[CREATE_NETWORK] = 'Create networks on this environment'

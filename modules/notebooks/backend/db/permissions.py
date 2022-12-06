
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
    MANAGE_ENVIRONMENTS,
    MANAGE_ORGANIZATIONS,
    MANAGE_PIPELINES,
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
RESOURCES_ALL
"""

RESOURCES_ALL = (
    DATASET_ALL
    + ORGANIZATION_ALL
    + ENVIRONMENT_ALL
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
RESOURCES_ALL_WITH_DESC[CREATE_SHARE_OBJECT] = 'Request datasets access for this environment'
RESOURCES_ALL_WITH_DESC[CREATE_PIPELINE] = 'Create pipelines on this environment'
RESOURCES_ALL_WITH_DESC[CREATE_NETWORK] = 'Create networks on this environment'

from dataall.db.permissions import ENVIRONMENT_INVITED, ENVIRONMENT_INVITATION_REQUEST, ENVIRONMENT_ALL, TENANT_ALL, \
    TENANT_ALL_WITH_DESC, RESOURCES_ALL, RESOURCES_ALL_WITH_DESC

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

RESOURCES_ALL.extend(DASHBOARD_ALL)
for perm in DASHBOARD_ALL:
    RESOURCES_ALL_WITH_DESC[perm] = perm

"""
TENANT PERMISSIONS
"""
MANAGE_DASHBOARDS = 'MANAGE_DASHBOARDS'

TENANT_ALL.append(MANAGE_DASHBOARDS)
TENANT_ALL_WITH_DESC[MANAGE_DASHBOARDS] = 'Manage dashboards'


"""
ENVIRONMENT PERMISSIONS
"""
CREATE_DASHBOARD = 'CREATE_DASHBOARD'


ENVIRONMENT_INVITED.append(CREATE_DASHBOARD)
ENVIRONMENT_INVITATION_REQUEST.append(CREATE_DASHBOARD)
ENVIRONMENT_ALL.append(CREATE_DASHBOARD)
RESOURCES_ALL.append(CREATE_DASHBOARD)
RESOURCES_ALL_WITH_DESC[CREATE_DASHBOARD] = 'Create dashboards on this environment'

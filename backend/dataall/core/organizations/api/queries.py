from dataall.base.api import gql
from .input_types import OrganizationFilter
from .resolvers import (
    get_organization,
    list_organization_groups,
    list_organizations,
    list_organization_read_only_groups,
)
from .types import (
    Organization,
    OrganizationSearchResult,
)

getOrganization = gql.QueryField(
    name='getOrganization',
    args=[gql.Argument(name='organizationUri', type=gql.NonNullableType(gql.String))],
    type=gql.Thunk(lambda: Organization),
    resolver=get_organization,
    test_scope='Organization',
)


listOrganizations = gql.QueryField(
    name='listOrganizations',
    args=[gql.Argument('filter', OrganizationFilter)],
    type=OrganizationSearchResult,
    resolver=list_organizations,
    test_scope='Organization',
)


listOrganizationGroups = gql.QueryField(
    name='listOrganizationGroups',
    type=gql.Ref('GroupSearchResult'),
    args=[
        gql.Argument(name='organizationUri', type=gql.NonNullableType(gql.String)),
        gql.Argument(name='filter', type=gql.Ref('GroupFilter')),
    ],
    resolver=list_organization_groups,
)

listOrganizationReadOnlyGroups = gql.QueryField(
    name='listOrganizationReadOnlyGroups',
    type=gql.Ref('GroupSearchResult'),
    args=[
        gql.Argument(name='organizationUri', type=gql.NonNullableType(gql.String)),
        gql.Argument(name='filter', type=gql.Ref('GroupFilter')),
    ],
    resolver=list_organization_read_only_groups,
)

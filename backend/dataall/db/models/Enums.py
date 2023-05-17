from enum import Enum


class OrganisationUserRole(Enum):
    Owner = '999'
    Admin = '900'
    Member = '100'
    NotMember = '000'
    Invited = '800'


class GroupMemberRole(Enum):
    Owner = 'Owner'
    Admin = 'Admin'
    Member = 'Member'
    NotMember = 'NotMember'


class EnvironmentPermission(Enum):
    Owner = '999'
    Admin = '900'
    DatasetCreator = '800'
    Invited = '200'
    ProjectAccess = '050'
    NotInvited = '000'


class EnvironmentType(Enum):
    Data = 'Data'
    Compute = 'Compute'


class ProjectMemberRole(Enum):
    ProjectCreator = '999'
    Admin = '900'
    NotContributor = '000'


class DashboardRole(Enum):
    Creator = '999'
    Admin = '900'
    Shared = '800'
    NoPermission = '000'


class DataPipelineRole(Enum):
    Creator = '999'
    Admin = '900'
    NoPermission = '000'


class RedshiftClusterRole(Enum):
    Creator = '950'
    Admin = '900'
    Shared = '300'
    NoPermission = '000'


class ScheduledQueryRole(Enum):
    Creator = '950'
    Admin = '900'
    Shared = '300'
    NoPermission = '000'


class SagemakerStudioRole(Enum):
    Creator = '950'
    Admin = '900'
    Shared = '300'
    NoPermission = '000'


class AirflowClusterRole(Enum):
    Creator = '950'
    Admin = '900'
    Shared = '300'
    NoPermission = '000'


class SortDirection(Enum):
    asc = 'asc'
    desc = 'desc'


class PrincipalType(Enum):
    Any = 'Any'
    Organization = 'Organization'
    Environment = 'Environment'
    User = 'User'
    Project = 'Project'
    Public = 'Public'
    Group = 'Group'
    ConsumptionRole = 'ConsumptionRole'


class Language(Enum):
    English = 'English'
    French = 'French'
    German = 'German'


class Topic(Enum):
    Finances = 'Finances'
    HumanResources = 'HumanResources'
    Products = 'Products'
    Services = 'Services'
    Operations = 'Operations'
    Research = 'Research'
    Sales = 'Sales'
    Orders = 'Orders'
    Sites = 'Sites'
    Energy = 'Energy'
    Customers = 'Customers'
    Misc = 'Misc'

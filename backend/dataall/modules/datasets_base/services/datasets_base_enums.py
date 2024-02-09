from dataall.base.api.constants import GraphQLEnumMapper
from dataall.base.config import config
custom_confidentiality_mapping = config.get_property('modules.datasets.features.custom_confidentiality_mapping', {})


class DatasetRole(GraphQLEnumMapper):
    # Permissions on a dataset
    BusinessOwner = '999'
    DataSteward = '998'
    Creator = '950'
    Admin = '900'
    Shared = '300'
    NoPermission = '000'


class DatasetSortField(GraphQLEnumMapper):
    label = 'label'
    created = 'created'
    updated = 'updated'


class ConfidentialityClassification(GraphQLEnumMapper):
    Unclassified = 'Unclassified'
    Official = 'Official'
    Secret = 'Secret'

    @staticmethod
    def get_confidentiality_level(confidentiality, context):
        if context.db_engine.dbconfig.schema == 'pytest':
            return confidentiality
        return confidentiality if not custom_confidentiality_mapping else custom_confidentiality_mapping.get(
            confidentiality, None)


class Language(GraphQLEnumMapper):
    English = 'English'
    French = 'French'
    German = 'German'


class Topic(GraphQLEnumMapper):
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

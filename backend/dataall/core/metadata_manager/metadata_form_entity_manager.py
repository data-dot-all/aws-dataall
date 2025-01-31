from abc import ABC
from typing import Dict

from dataall.base.api import GraphQLEnumMapper


class MetadataFormEntityTypes(GraphQLEnumMapper):
    Organizations = 'Organization'
    OrganizationTeams = 'Organization Team'
    Environments = 'Environment'
    EnvironmentTeams = 'Environment Team'
    S3Datasets = 'S3-Dataset'
    RDDatasets = 'Redshift-Dataset'
    Worksheets = 'Worksheets'
    Dashboards = 'Dashboard'
    ConsumptionRoles = 'Consumption Role'
    Notebooks = 'Notebook'
    MLStudioEntities = 'ML Studio Entity'
    Pipelines = 'Pipeline'
    Tables = 'Table'
    Folder = 'Folder'
    Bucket = 'Bucket'
    Share = 'Share'


class MetadataFormEntity(ABC):
    def get_owner(self):
        pass

    def get_entity_name(self):
        pass

    def get_uri(self):
        pass


class MetadataFormEntityManager:
    """
    API for managing entities, to which MF can be attached.
    """

    _resources: Dict[str, MetadataFormEntity] = {}

    @classmethod
    def register(cls, resource: MetadataFormEntity, resource_key):
        cls._resources[resource_key] = resource

    @classmethod
    def get_resource(cls, resource_key):
        if resource_key not in cls._resources:
            raise NotImplementedError(f'Entity {resource_key} is not registered')
        return cls._resources[resource_key]

    @classmethod
    def is_registered(cls, resource_key):
        return resource_key in cls._resources

    @classmethod
    def all_registered_keys(cls):
        return cls._resources.keys()

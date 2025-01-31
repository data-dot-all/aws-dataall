"""The package contains the database models that are related to the environment"""

import datetime

from sqlalchemy import Boolean, Column, DateTime, String, ForeignKey
from sqlalchemy.orm import query_expression
from dataall.base.db import Resource, Base, utils

from dataall.core.environment.api.enums import EnvironmentPermission, EnvironmentType
from dataall.core.metadata_manager import MetadataFormEntityManager, MetadataFormEntity, MetadataFormEntityTypes


class Environment(Resource, Base):
    __metaclass__ = MetadataFormEntity
    __tablename__ = 'environment'
    organizationUri = Column(String, nullable=False)
    environmentUri = Column(String, primary_key=True, default=utils.uuid('environment'))
    AwsAccountId = Column(String, nullable=False)
    region = Column(String, nullable=False, default='eu-west-1')
    cognitoGroupName = Column(String, nullable=True)
    resourcePrefix = Column(String, nullable=False, default='dataall')

    validated = Column(Boolean, default=False)
    environmentType = Column(String, nullable=False, default=EnvironmentType.Data.value)
    isOrganizationDefaultEnvironment = Column(Boolean, default=False)
    EnvironmentDefaultIAMRoleName = Column(String, nullable=False)
    EnvironmentDefaultIAMRoleImported = Column(Boolean, default=False)
    EnvironmentDefaultIAMRoleArn = Column(String, nullable=False)
    EnvironmentDefaultBucketName = Column(String)
    EnvironmentLogsBucketName = Column(String)
    EnvironmentDefaultAthenaWorkGroup = Column(String)
    roleCreated = Column(Boolean, nullable=False, default=False)

    userRoleInEnvironment = query_expression()

    SamlGroupName = Column(String, nullable=True)
    CDKRoleArn = Column(String, nullable=False)

    subscriptionsEnabled = Column(Boolean, default=False)
    subscriptionsProducersTopicName = Column(String)
    subscriptionsProducersTopicImported = Column(Boolean, default=False)
    subscriptionsConsumersTopicName = Column(String)
    subscriptionsConsumersTopicImported = Column(Boolean, default=False)

    def get_uri(self):
        return self.environmentUri

    def get_owner(self):
        return self.SamlGroupName

    def get_entity_name(self):
        return self.label


class EnvironmentGroup(Base):
    __metaclass__ = MetadataFormEntity
    __tablename__ = 'environment_group_permission'
    groupUri = Column(String, primary_key=True)
    environmentUri = Column(String, primary_key=True)
    invitedBy = Column(String, nullable=True)
    environmentIAMRoleArn = Column(String, nullable=True)
    environmentIAMRoleName = Column(String, nullable=True)
    environmentIAMRoleImported = Column(Boolean, default=False)
    environmentAthenaWorkGroup = Column(String, nullable=True)
    description = Column(String, default='No description provided')
    created = Column(DateTime, default=datetime.datetime.now)
    updated = Column(DateTime, onupdate=datetime.datetime.now)
    deleted = Column(DateTime)

    # environmentRole is the role of the entity (group or user) in the Environment
    groupRoleInEnvironment = Column(String, nullable=False, default=EnvironmentPermission.Invited.value)

    def get_uri(self):
        return f'{self.groupUri}-{self.environmentUri}'

    def get_owner(self):
        return self.invitedBy

    def get_entity_name(self):
        return f'{self.groupUri}-{self.environmentUri}'


class EnvironmentParameter(Base):
    """Represent the parameter of the environment"""

    __tablename__ = 'environment_parameters'
    environmentUri = Column(String, ForeignKey('environment.environmentUri'), primary_key=True)
    key = Column('paramKey', String, primary_key=True)
    value = Column('paramValue', String, nullable=False)

    def __init__(self, env_uri, key, value):
        super().__init__()
        self.environmentUri = env_uri
        self.key = key
        self.value = value

    def __repr__(self):
        return f'EnvironmentParameter(paramKey={self.key}, paramValue={self.value})'


class ConsumptionRole(Base):
    __metaclass__ = MetadataFormEntity
    __tablename__ = 'consumptionrole'
    consumptionRoleUri = Column(String, primary_key=True, default=utils.uuid('group'))
    consumptionRoleName = Column(String, nullable=False)
    environmentUri = Column(String, nullable=False)
    groupUri = Column(String, nullable=False)
    IAMRoleName = Column(String, nullable=False)
    IAMRoleArn = Column(String, nullable=False)
    dataallManaged = Column(Boolean, nullable=False, default=True)
    created = Column(DateTime, default=datetime.datetime.now)
    updated = Column(DateTime, onupdate=datetime.datetime.now)
    deleted = Column(DateTime)

    def get_uri(self):
        return self.consumptionRoleUri

    def get_owner(self):
        return self.groupUri

    def get_entity_name(self):
        return f'{self.consumptionRoleName}-{self.environmentUri}'


MetadataFormEntityManager.register(Environment, MetadataFormEntityTypes.Environments.value)
MetadataFormEntityManager.register(ConsumptionRole, MetadataFormEntityTypes.ConsumptionRoles.value)
MetadataFormEntityManager.register(EnvironmentGroup, MetadataFormEntityTypes.EnvironmentTeams.value)

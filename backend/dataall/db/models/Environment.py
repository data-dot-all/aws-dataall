from sqlalchemy import Boolean, Column, String
from sqlalchemy.orm import query_expression, relationship

from .. import Base
from .. import Resource, utils


class Environment(Resource, Base):
    __tablename__ = 'environment'
    organizationUri = Column(String, nullable=False)
    environmentUri = Column(String, primary_key=True, default=utils.uuid('environment'))
    AwsAccountId = Column(String, nullable=False)
    region = Column(String, nullable=False, default='eu-west-1')
    cognitoGroupName = Column(String, nullable=True)
    resourcePrefix = Column(String, nullable=False, default='dataall')

    validated = Column(Boolean, default=False)
    environmentType = Column(String, nullable=False, default='Data')
    isOrganizationDefaultEnvironment = Column(Boolean, default=False)
    EnvironmentDefaultIAMRoleName = Column(String, nullable=False)
    EnvironmentDefaultIAMRoleImported = Column(Boolean, default=False)
    EnvironmentDefaultIAMRoleArn = Column(String, nullable=False)
    EnvironmentDefaultBucketName = Column(String)
    EnvironmentDefaultAthenaWorkGroup = Column(String)
    roleCreated = Column(Boolean, nullable=False, default=False)

    dashboardsEnabled = Column(Boolean, default=False)
    mlStudiosEnabled = Column(Boolean, default=True)
    pipelinesEnabled = Column(Boolean, default=True)
    warehousesEnabled = Column(Boolean, default=True)

    userRoleInEnvironment = query_expression()

    SamlGroupName = Column(String, nullable=True)
    CDKRoleArn = Column(String, nullable=False)

    subscriptionsEnabled = Column(Boolean, default=False)
    subscriptionsProducersTopicName = Column(String)
    subscriptionsProducersTopicImported = Column(Boolean, default=False)
    subscriptionsConsumersTopicName = Column(String)
    subscriptionsConsumersTopicImported = Column(Boolean, default=False)

    # Eager loading of the parameters, deletes the params automatically that are not associated with environment
    parameters = relationship(
        "EnvironmentParameter",
        primaryjoin="Environment.environmentUri==EnvironmentParameter.environmentUri",
        cascade="all, delete-orphan",
        lazy="joined"
    )

    def get_param(self, key, default=None):
        for param in self.parameters:
            if param.key == key:
                return param.value
        return default

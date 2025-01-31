from enum import Enum

from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import query_expression

from dataall.base.db import Base, Resource, utils
from dataall.core.metadata_manager import MetadataFormEntity


class DashboardShareStatus(Enum):
    REQUESTED = 'REQUESTED'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'


class DashboardShare(Base):
    __tablename__ = 'dashboardshare'
    shareUri = Column(String, nullable=False, primary_key=True, default=utils.uuid('shareddashboard'))
    dashboardUri = Column(String, nullable=False, default=utils.uuid('dashboard'))
    SamlGroupName = Column(String, nullable=False)
    owner = Column(String, nullable=True)
    status = Column(String, nullable=False, default=DashboardShareStatus.REQUESTED.value)


class Dashboard(Resource, Base):
    __metaclass__ = MetadataFormEntity
    __tablename__ = 'dashboard'
    environmentUri = Column(String, ForeignKey('environment.environmentUri'), nullable=False)
    organizationUri = Column(String, nullable=False)
    dashboardUri = Column(String, nullable=False, primary_key=True, default=utils.uuid('dashboard'))
    region = Column(String, default='eu-west-1')
    AwsAccountId = Column(String, nullable=False)
    namespace = Column(String, nullable=False)
    DashboardId = Column(String, nullable=False)
    SamlGroupName = Column(String, nullable=False)

    userRoleForDashboard = query_expression()

    @classmethod
    def uri(cls):
        return cls.dashboardUri

    def get_owner(self):
        return self.SamlGroupName

    def get_entity_name(self):
        return self.label

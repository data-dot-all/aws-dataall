"""ORM models for sagemaker studio"""

from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import query_expression
from sqlalchemy.dialects.postgresql import ARRAY

from dataall.base.db import Base
from dataall.base.db import Resource, utils


class SagemakerStudioDomain(Resource, Base):
    """Describes ORM model for sagemaker ML Studio domain"""
    __tablename__ = 'sagemaker_studio_domain'
    environmentUri = Column(String, ForeignKey("environment.environmentUri"))
    sagemakerStudioUri = Column(
        String, primary_key=True, default=utils.uuid('sagemakerstudio')
    )
    sagemakerStudioDomainID = Column(String, nullable=False)
    SagemakerStudioStatus = Column(String, nullable=True)
    sagemakerStudioDomainName = Column(String, nullable=False)
    AWSAccountId = Column(String, nullable=False)
    DefaultDomainRoleName = Column(String, nullable=False)
    region = Column(String, default='eu-west-1')
    vpcType = Column(String, nullable=True)
    vpcId = Column(String, nullable=True)
    subnetIds = Column(ARRAY(String), nullable=True)


class SagemakerStudioUser(Resource, Base):
    """Describes ORM model for sagemaker ML Studio user"""
    __tablename__ = 'sagemaker_studio_user_profile'
    environmentUri = Column(String, ForeignKey("environment.environmentUri"), nullable=False)
    sagemakerStudioUserUri = Column(
        String, primary_key=True, default=utils.uuid('sagemakerstudiouserprofile')
    )
    sagemakerStudioUserStatus = Column(String, nullable=False)
    sagemakerStudioUserName = Column(String, nullable=False)
    sagemakerStudioUserNameSlugify = Column(
        String, nullable=False, default=utils.slugifier('label')
    )
    sagemakerStudioDomainID = Column(String, nullable=False)
    AWSAccountId = Column(String, nullable=False)
    RoleArn = Column(String, nullable=False)
    region = Column(String, default='eu-west-1')
    SamlAdminGroupName = Column(String, nullable=True)
    userRoleForSagemakerStudioUser = query_expression()

from sqlalchemy import Column, String, ForeignKey, Integer
from sqlalchemy.orm import query_expression
from sqlalchemy.dialects import postgresql

from dataall.base.db import Base, Resource, utils


class DataPipeline(Resource, Base):
    __tablename__ = 'datapipeline'
    environmentUri = Column(String, ForeignKey("environment.environmentUri"), nullable=False)
    DataPipelineUri = Column(
        String, nullable=False, primary_key=True, default=utils.uuid('DataPipelineUri')
    )
    region = Column(String, default='eu-west-1')
    AwsAccountId = Column(String, nullable=False)
    SamlGroupName = Column(String, nullable=False)
    repo = Column(String, nullable=False)
    devStrategy = Column(String, nullable=False)
    template = Column(String, nullable=True, default="")
    userRoleForPipeline = query_expression()


class DataPipelineEnvironment(Base, Resource):
    __tablename__ = 'datapipelineenvironments'
    envPipelineUri = Column(String, nullable=False, primary_key=True)
    environmentUri = Column(String, nullable=False)
    environmentLabel = Column(String, nullable=False)
    pipelineUri = Column(String, nullable=False)
    pipelineLabel = Column(String, nullable=False)
    stage = Column(String, nullable=False)
    order = Column(Integer, nullable=False)
    region = Column(String, default='eu-west-1', nullable=False)
    AwsAccountId = Column(String, nullable=False)
    samlGroupName = Column(String, nullable=False)

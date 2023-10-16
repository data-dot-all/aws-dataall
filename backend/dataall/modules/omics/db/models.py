import enum

from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import query_expression, relationship

from dataall.base.db import Base
from dataall.base.db import Resource, utils


class OmicsWorkflowType(enum.Enum):
    PRIVATE = "PRIVATE"
    READY2RUN = "READY2RUN"

class OmicsWorkflow(Resource, Base):
    __tablename__ = "omics_workflow"
    arn = Column(String, nullable=False)
    id = Column(String, nullable=False, primary_key=True, default=utils.uuid("omicsWorkflowUri"))
    label = Column(String, nullable=False, default=utils.uuid("omicsWorkflowUri"))
    owner = Column(String, nullable=False, default=utils.uuid("omicsWorkflowUri"))
    name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    type = Column(String, nullable=False)
    description = Column(String, nullable=True)
    environmentUri = Column(String, nullable=False)

class OmicsRun(Resource, Base):
    __tablename__ = "omics_run"
    runUri = Column(String, nullable=False, primary_key=True, default=utils.uuid("runUri"))
    organizationUri = Column(String, nullable=False)
    environmentUri = Column(String, ForeignKey("environment.environmentUri", ondelete="cascade"), nullable=False)
    region = Column(String, default="eu-west-1")
    AwsAccountId = Column(String, nullable=False)
    SamlAdminGroupName = Column(String, nullable=False)
    workflowId = Column(String, nullable=False)
    parameterTemplate = Column(String, nullable=False)
    outputUri = Column(String, nullable=True)

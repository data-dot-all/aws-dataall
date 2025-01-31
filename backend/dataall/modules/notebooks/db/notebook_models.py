"""ORM models for sagemaker notebooks"""

from sqlalchemy import Column, String, Integer, ForeignKey

from dataall.base.db import Base
from dataall.base.db import Resource, utils

from dataall.core.metadata_manager.metadata_form_entity_manager import MetadataFormEntity


class SagemakerNotebook(Resource, Base):
    """Describes ORM model for sagemaker notebooks"""

    __metaclass__ = MetadataFormEntity
    __tablename__ = 'sagemaker_notebook'
    environmentUri = Column(String, ForeignKey('environment.environmentUri'), nullable=False)
    notebookUri = Column(String, primary_key=True, default=utils.uuid('notebook'))
    NotebookInstanceName = Column(String, nullable=False, default=utils.slugifier('label'))
    NotebookInstanceStatus = Column(String, nullable=False)
    AWSAccountId = Column(String, nullable=False)
    RoleArn = Column(String, nullable=False)
    region = Column(String, default='eu-west-1')
    SamlAdminGroupName = Column(String, nullable=True)
    VpcId = Column(String, nullable=True)
    SubnetId = Column(String, nullable=True)
    VolumeSizeInGB = Column(Integer, nullable=True)
    InstanceType = Column(String, nullable=True)

    def get_owner(self):
        return self.SamlAdminGroupName

    def get_entity_name(self):
        return self.NotebookInstanceName

    def get_uri(self):
        return self.notebookUri

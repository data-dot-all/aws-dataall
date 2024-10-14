from dataall.base.db import Base, utils
from sqlalchemy import String, Integer, Column, Date, func
import uuid


class ResourceThreshold(Base):
    __tablename__ = 'resource_threshold'
    actionId = Column(String(64), primary_key=True, default=lambda: utils.uuid('resource_threshold'))
    username = Column(String(64), nullable=False)
    actionType = Column(String(64), nullable=False)
    date = Column(Date, default=func.current_date(), nullable=False)
    count = Column(Integer, default=1, nullable=False)

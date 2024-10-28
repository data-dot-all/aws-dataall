from dataall.base.db import Base, utils
from sqlalchemy import String, Integer, Column, Date
from datetime import date


class ResourceThreshold(Base):
    __tablename__ = 'resource_threshold'
    actionUri = Column(String(64), primary_key=True, default=utils.uuid('resource_threshold'))
    username = Column(String(64), nullable=False)
    actionType = Column(String(64), nullable=False)
    date = Column(Date, default=date.today, nullable=False)
    count = Column(Integer, default=1, nullable=False)

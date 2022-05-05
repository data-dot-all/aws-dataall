import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from .. import Base
from . import Permission, TenantPolicy


class TenantPolicyPermission(Base):
    __tablename__ = 'tenant_policy_permission'

    sid = Column(String, ForeignKey(TenantPolicy.sid), primary_key=True)
    permissionUri = Column(
        String, ForeignKey(Permission.permissionUri), primary_key=True
    )
    permission = relationship('Permission')
    created = Column(DateTime, default=datetime.datetime.now)
    updated = Column(DateTime, onupdate=datetime.datetime.now)

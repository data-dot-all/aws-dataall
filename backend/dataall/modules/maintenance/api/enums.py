"""Contains the enums GraphQL mapping for SageMaker notebooks"""
from enum import Enum


class MaintenanceModes(Enum):
    """Describes the Maintenance Modes"""
    READONLY = 'READ-ONLY'
    NOACCESS = 'NO-ACCESS'

class MaintenanceStatus():
    """Describe the various statuses for maintenance"""

    PENDING = 'PENDING'
    INACTIVE = 'INACTIVE'
    ACTIVE = 'ACTIVE'

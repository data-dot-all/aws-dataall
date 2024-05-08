from dataall.base.api.context import Context
from dataall.core.permissions.services.tenant_policy_service import TenantPolicyValidationService
from dataall.modules.maintenance.api.enums import MaintenanceModes
from dataall.modules.maintenance.api.types import Maintenance
from dataall.modules.maintenance.services.maintenance_service import MaintenanceService


def start_maintenance_window(context: Context, source: Maintenance, mode: str):
    """Starts the maintenance window"""
    if mode not in [item.value for item in list(MaintenanceModes)]:
        raise Exception('Mode is not conforming to the MaintenanceModes enum')
    return MaintenanceService.start_maintenance_window(engine=context.engine, mode=mode, groups=context.groups)


def stop_maintenance_window(context: Context, source: Maintenance):
    return MaintenanceService.stop_maintenance_window(engine=context.engine, groups=context.groups)


def get_maintenance_window_status(context: Context, source: Maintenance):
    return MaintenanceService.get_maintenance_window_status(engine=context.engine)

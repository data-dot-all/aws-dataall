"""
The handler of this module will be called once upon every deployment
"""

import os

from alembic import command
from alembic.config import Config

from dataall.base.db import get_engine
from dataall.base.loader import load_modules, ImportMode
from dataall.core.permissions.services.tenant_policy_service import TenantPolicyService


def db_migrations(event, context) -> None:
    alembic_cfg = Config('alembic.ini')
    alembic_cfg.set_main_option('script_location', './migrations')
    command.upgrade(alembic_cfg, 'head')


def save_permissions(event, context):
    load_modules(modes={ImportMode.API})
    envname = os.getenv('envname', 'local')
    engine = get_engine(envname=envname)
    TenantPolicyService.save_permissions_with_tenant(engine)

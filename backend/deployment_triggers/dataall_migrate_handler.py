import logging
import os
from migrations.dataall_migrations.migrationmanager import MigrationManager
from dataall.base.db import get_engine

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

ENVNAME = os.environ.get('envname', 'local')
ENGINE = get_engine(envname=ENVNAME)
PARAM_KEY = f'/dataall/{ENVNAME}/dataall-migration/revision'


def get_current_revision():
    with ENGINE.scoped_session() as session:
        row = session.query('revision from dataall_migrations').first()
        return row[0] if row else row


def put_latest_revision(old_revision, new_revision):
    with ENGINE.scoped_session() as session:
        if old_revision:
            sql_params = "UPDATE dataall_migrations SET revision='{}' WHERE revision='{}';".format(
                new_revision, old_revision
            )
        else:
            sql_params = "INSERT INTO dataall_migrations VALUES('{}');".format(new_revision)
        session.execute(sql_params)


def handler(event, context) -> None:
    revision = get_current_revision()
    current_key = revision or '0'
    manager = MigrationManager(current_key)
    new_version = manager.upgrade()
    if not new_version:
        raise Exception('Data.all migration failed.')
    put_latest_revision(revision, new_version)

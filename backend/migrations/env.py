from __future__ import with_statement
from alembic import context
from logging.config import fileConfig
import re


# DO NOT DELETE
# these models are not used directly in env.py, but these imports are important for alembic
# import additional models here

# disable ruff-format, because this unused imports are important
# fmt: off
from dataall.modules.catalog.db.glossary_models import GlossaryNode, TermLink
from dataall.modules.dashboards.db.dashboard_models import DashboardShare, Dashboard
from dataall.modules.datapipelines.db.datapipelines_models import DataPipeline, DataPipelineEnvironment
from dataall.modules.feed.db.feed_models import FeedMessage
from dataall.modules.notifications.db.notification_models import Notification
from dataall.modules.vote.db.vote_models import Vote
from dataall.modules.worksheets.db.worksheet_models import WorksheetQueryResult, Worksheet
from dataall.modules.omics.db.omics_models import OmicsWorkflow, OmicsRun
from dataall.modules.metadata_forms.db.metadata_form_models import *
from dataall.modules.redshift_datasets.db.redshift_models import RedshiftDataset, RedshiftTable, RedshiftConnection
from dataall.core.resource_threshold.db.resource_threshold_models import ResourceThreshold
# fmt: on
# enable ruff-format back

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
from dataall.base.db.base import Base
from dataall.base.db.connection import ENVNAME, get_engine

config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


exclude_tables = config.get_section('alembic:exclude').get('tables', '').split(',')


def include_object(object, name, type_, *args, **kwargs):
    return not (type_ == 'table' and name in exclude_tables)


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    if ENVNAME in ['local', 'pytest', 'dkrcompose']:
        url = config.get_main_option('sqlalchemy.url')
    else:
        url = get_engine(ENVNAME).dbconfig.url

    context.configure(
        url=url,
        target_metadata=target_metadata,
        version_table_schema=ENVNAME,
        literal_binds=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    with get_engine(ENVNAME).engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, include_object=include_object)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

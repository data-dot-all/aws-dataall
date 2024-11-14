"""add_env_logs_bucket

Revision ID: 49c6b18ed814
Revises: b21f86882012
Create Date: 2024-11-13 19:16:18.030415

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import orm, Column, String
from sqlalchemy.ext.declarative import declarative_base

from dataall.base.db import Resource, utils
from dataall.base.utils.naming_convention import (
    NamingConventionService,
    NamingConventionPattern,
)

# revision identifiers, used by Alembic.
revision = '49c6b18ed814'
down_revision = 'b21f86882012'
branch_labels = None
depends_on = None

Base = declarative_base()


class Environment(Resource, Base):
    __tablename__ = 'environment'
    environmentUri = Column(String, primary_key=True, default=utils.uuid('environment'))
    resourcePrefix = Column(String, nullable=False, default='dataall')
    EnvironmentLogsBucketName = Column(String, nullable=True)


def upgrade():
    op.add_column('environment', sa.Column('EnvironmentLogsBucketName', sa.String(), nullable=True))
    bind = op.get_bind()
    session = orm.Session(bind=bind)
    environments = session.query(Environment).all()
    for env in environments:
        env.EnvironmentLogsBucketName = NamingConventionService(
            target_uri=env.environmentUri,
            target_label='env-access-logs',
            pattern=NamingConventionPattern.S3,
            resource_prefix=env.resourcePrefix,
        ).build_compliant_name()
        session.commit()
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('environment', 'EnvironmentLogsBucketName')
    # ### end Alembic commands ###

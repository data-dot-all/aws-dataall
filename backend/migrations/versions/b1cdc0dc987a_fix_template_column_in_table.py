"""fix template column in table datapipeline

Revision ID: b1cdc0dc987a
Revises: 4392a0c9747f
Create Date: 2022-09-22 18:25:35.980288

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import orm, Column, String
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.declarative import declarative_base

# revision identifiers, used by Alembic.
revision = 'b1cdc0dc987a'
down_revision = '4392a0c9747f'
branch_labels = None
depends_on = None

Base = declarative_base()


class DataPipeline(Base):
    __tablename__ = 'datapipeline'
    DataPipelineUri = Column(String, nullable=False, primary_key=True)
    devStrategy = Column(String, nullable=True)
    devStages = Column(postgresql.ARRAY(String), nullable=True)


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    # Modify column types
    print('Upgrade devStages and devStrategy column types. Updating nullable to True...')
    op.add_column('datapipeline', sa.Column('template', sa.String(), nullable=True))
    op.alter_column('datapipeline', 'devStages', existing_type=postgresql.ARRAY(sa.VARCHAR()), nullable=True)
    op.alter_column('datapipeline', 'devStrategy', existing_type=sa.VARCHAR(), nullable=True)
    print('Backfilling values for devStages and devStrategy...')
    # Backfill values
    bind = op.get_bind()
    session = orm.Session(bind=bind)
    session.query(DataPipeline).filter(DataPipeline.devStrategy is None).update(
        {DataPipeline.devStrategy: 'gitflowBlueprint'}, synchronize_session=False
    )

    session.query(DataPipeline).filter(DataPipeline.devStages is None).update(
        {DataPipeline.devStages: ['dev', 'test', 'prod']}, synchronize_session=False
    )
    session.commit()

    print('Backfilling values for devStages and devStrategy is done. Updating nullable to False...')
    # Force nullable = False
    op.alter_column('datapipeline', 'devStages', existing_type=postgresql.ARRAY(sa.VARCHAR()), nullable=False)
    op.alter_column('datapipeline', 'devStrategy', existing_type=sa.VARCHAR(), nullable=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('datapipeline', 'devStrategy', existing_type=sa.VARCHAR(), nullable=True)
    op.alter_column('datapipeline', 'devStages', existing_type=postgresql.ARRAY(sa.VARCHAR()), nullable=True)
    op.drop_column('datapipeline', 'template')
    # ### end Alembic commands ###

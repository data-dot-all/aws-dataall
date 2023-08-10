"""fix template column in table datapipeline

Revision ID: b1cdc0dc987a
Revises: 4392a0c9747f
Create Date: 2022-09-22 18:25:35.980288

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b1cdc0dc987a'
down_revision = '4392a0c9747f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    # Modify column types
    op.add_column(
        'datapipeline',
        sa.Column('template', sa.String(), nullable=True)
    )
    op.alter_column(
        'datapipeline',
        'devStages',
        existing_type=postgresql.ARRAY(sa.VARCHAR()),
        nullable=True
    )
    op.alter_column(
        'datapipeline',
        'devStrategy',
        existing_type=sa.VARCHAR(),
        nullable=True
    )
    # Backfill values
    table = sa.table('datapipeline', sa.column('devStrategy'), sa.VARCHAR(), sa.column('devStages'), postgresql.ARRAY(sa.VARCHAR()))
    op.execute(
        table.update()
        .where(table.c.devStrategy is None)
        .values(devStrategy='gitflowBlueprint')
    )
    op.execute(
        table.update()
        .where(table.c.devStages is None)
        .values(devStages=['dev', 'test', 'prod'])
    )
    # Force nullable = False
    op.alter_column(
        'datapipeline',
        'devStages',
        existing_type=postgresql.ARRAY(sa.VARCHAR()),
        nullable=False
    )
    op.alter_column(
        'datapipeline',
        'devStrategy',
        existing_type=sa.VARCHAR(),
        nullable=False
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        'datapipeline',
        'devStrategy',
        existing_type=sa.VARCHAR(),
        nullable=True
    )
    op.alter_column(
        'datapipeline', 'devStages',
        existing_type=postgresql.ARRAY(sa.VARCHAR()),
        nullable=True
    )
    op.drop_column(
        'datapipeline',
        'template'
    )
    # ### end Alembic commands ###

"""dataset column type

Revision ID: be22468d7342
Revises: 5d5102986ce5
Create Date: 2021-07-02 07:39:46.442637

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'be22468d7342'
down_revision = '5d5102986ce5'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        'dataset_table_column', sa.Column('columnType', sa.String(), nullable=True)
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('dataset_table_column', 'columnType')
    # ### end Alembic commands ###

"""vpc default env flag

Revision ID: 46e5a33450b1
Revises: be22468d7342
Create Date: 2021-07-12 19:36:20.588492

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '46e5a33450b1'
down_revision = 'be22468d7342'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('vpc', sa.Column('default', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('vpc', 'default')
    # ### end Alembic commands ###

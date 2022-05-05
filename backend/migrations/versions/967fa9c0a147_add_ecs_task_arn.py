"""add ecs task arn

Revision ID: 967fa9c0a147
Revises: 5e5c84138af7
Create Date: 2021-10-06 07:48:30.726242

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '967fa9c0a147'
down_revision = '5e5c84138af7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('stack', sa.Column('EcsTaskArn', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('stack', 'EcsTaskArn')
    # ### end Alembic commands ###

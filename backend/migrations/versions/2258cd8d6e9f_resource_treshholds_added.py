"""describe_changes_shortly

Revision ID: 2258cd8d6e9f
Revises: 9efe5f7c69a1
Create Date: 2024-08-22 12:31:38.465650

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2258cd8d6e9f'
down_revision = '9efe5f7c69a1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('resource_threshold',
    sa.Column('actionId', sa.String(length=64), nullable=False),
    sa.Column('username', sa.String(length=64), nullable=False),
    sa.Column('actionType', sa.String(length=64), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('count', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('actionId')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('resource_threshold')
    # ### end Alembic commands ###

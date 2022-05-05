"""organization groups

Revision ID: decc96c5670f
Revises: 74b89c64f330
Create Date: 2021-08-13 08:17:02.257680

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'decc96c5670f'
down_revision = '74b89c64f330'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        'organization_group',
        sa.Column('groupUri', sa.String(), nullable=False),
        sa.Column('organizationUri', sa.String(), nullable=False),
        sa.Column('invitedBy', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('created', sa.DateTime(), nullable=True),
        sa.Column('updated', sa.DateTime(), nullable=True),
        sa.Column('deleted', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('groupUri', 'organizationUri'),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('organization_group')
    # ### end Alembic commands ###

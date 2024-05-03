"""describe_changes_shortly

Revision ID: af3e42a14920
Revises: a991ac7a85a2
Create Date: 2024-05-03 16:15:45.141150

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'af3e42a14920'
down_revision = 'a991ac7a85a2'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('resource_policy', sa.Column('groundsForPermission', sa.String(), nullable=True))
    op.create_index(op.f('ix_resource_policy_groundsForPermission'), 'resource_policy', ['groundsForPermission'], unique=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_resource_policy_groundsForPermission'), table_name='resource_policy')
    op.drop_column('resource_policy', 'groundsForPermission')
    # ### end Alembic commands ###

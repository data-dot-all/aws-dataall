"""_add_dataallManaged_flag

Revision ID: af0437dab922
Revises: f6cd4ba7dd8d
Create Date: 2024-02-15 10:42:06.833990

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'af0437dab922'
down_revision = 'f6cd4ba7dd8d'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('consumptionrole', sa.Column('dataaallManaged', sa.Boolean(), nullable=False))



def downgrade():
    op.drop_column('consumptionrole', 'dataaallManaged')


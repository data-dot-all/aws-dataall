"""dataset_lock_and_types_adjustment

Revision ID: 448d9dc95e94
Revises: e52fa2b8c887
Create Date: 2024-06-17 16:42:34.851166

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from dataall.modules.datasets_base.services.datasets_enums import DatasetTypes


# revision identifiers, used by Alembic.
revision = '448d9dc95e94'
down_revision = 'e52fa2b8c887'
branch_labels = None
depends_on = None



def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('dataset_lock', 'isLocked',
               existing_type=sa.BOOLEAN(),
               nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('dataset_lock', 'isLocked',
               existing_type=sa.BOOLEAN(),
               nullable=False)
    # ### end Alembic commands ###

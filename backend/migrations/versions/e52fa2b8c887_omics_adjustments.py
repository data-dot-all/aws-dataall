"""omics_adjustments

Revision ID: e52fa2b8c887
Revises: f2f7431c34e5
Create Date: 2024-06-17 14:45:06.997065

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e52fa2b8c887'
down_revision = 'f2f7431c34e5'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('omics_run', 'outputUri',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('omics_run', 'outputDatasetUri',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.create_foreign_key(None, 'omics_run', 'omics_workflow', ['workflowUri'], ['workflowUri'], ondelete='cascade')
    op.create_foreign_key(None, 'omics_run', 'environment', ['environmentUri'], ['environmentUri'], ondelete='cascade')
    op.alter_column('omics_workflow', 'environmentUri',
               existing_type=sa.VARCHAR(),
               nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('omics_workflow', 'environmentUri',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.drop_constraint(None, 'omics_run', type_='foreignkey')
    op.drop_constraint(None, 'omics_run', type_='foreignkey')
    op.alter_column('omics_run', 'outputDatasetUri',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('omics_run', 'outputUri',
               existing_type=sa.VARCHAR(),
               nullable=False)

    # ### end Alembic commands ###

"""sagemaker notebooks update

Revision ID: 94697ee46c0c
Revises: 9b589bf91485
Create Date: 2021-09-12 18:55:03.301399

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "94697ee46c0c"
down_revision = "9b589bf91485"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("sagemaker_notebook", sa.Column("VpcId", sa.String(), nullable=True))
    op.add_column("sagemaker_notebook", sa.Column("SubnetId", sa.String(), nullable=True))
    op.add_column("sagemaker_notebook", sa.Column("VolumeSizeInGB", sa.Integer(), nullable=True))
    op.add_column("sagemaker_notebook", sa.Column("InstanceType", sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("sagemaker_notebook", "InstanceType")
    op.drop_column("sagemaker_notebook", "VolumeSizeInGB")
    op.drop_column("sagemaker_notebook", "SubnetId")
    op.drop_column("sagemaker_notebook", "VpcId")
    # ### end Alembic commands ###

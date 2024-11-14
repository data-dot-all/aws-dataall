"""add_env_logs_bucket

Revision ID: 49c6b18ed814
Revises: b21f86882012
Create Date: 2024-11-13 19:16:18.030415

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '49c6b18ed814'
down_revision = 'b21f86882012'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('environment', sa.Column('EnvironmentLogsBucketName', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('environment', 'EnvironmentLogsBucketName')
    # ### end Alembic commands ###

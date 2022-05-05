"""vpc group

Revision ID: 74b89c64f330
Revises: e177eb044b31
Create Date: 2021-08-08 10:39:15.991280

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "74b89c64f330"
down_revision = "e177eb044b31"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("vpc", sa.Column("SamlGroupName", sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("vpc", "SamlGroupName")
    # ### end Alembic commands ###

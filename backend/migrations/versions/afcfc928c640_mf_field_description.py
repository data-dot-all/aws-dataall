"""mf_field_description

Revision ID: afcfc928c640
Revises: 7c5b30fee306
Create Date: 2024-08-05 14:09:40.972177

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'afcfc928c640'
down_revision = '852cdf6cf1e0'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('metadata_form_field', sa.Column('description', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('metadata_form_field', 'description')
    # ### end Alembic commands ###

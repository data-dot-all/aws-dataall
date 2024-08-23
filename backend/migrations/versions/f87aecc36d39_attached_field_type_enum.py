"""attached_field_type_enum

Revision ID: f87aecc36d39
Revises: 9efe5f7c69a1
Create Date: 2024-08-17 13:31:54.386554

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f87aecc36d39'
down_revision = '9efe5f7c69a1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute("CREATE TYPE metadataformfieldtype AS ENUM('String', 'Integer', 'Boolean', 'GlossaryTerm')")
    op.execute(
        'alter table attached_metadata_form_field alter column type TYPE metadataformfieldtype USING (type::metadataformfieldtype)'
    )

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute('DROP TYPE metadataformfieldtype')
    op.alter_column('attached_metadata_form_field', 'type', type_=sa.VARCHAR(), existing_nullable=True)
    # ### end Alembic commands ###

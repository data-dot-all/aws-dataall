"""release 3.6.0

Revision ID: bd4bea86de30
Revises: c5c6bbbc5de7
Create Date: 2021-11-29 06:10:27.519546

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'bd4bea86de30'
down_revision = 'c5c6bbbc5de7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        'vote',
        sa.Column('voteUri', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('targetUri', sa.String(), nullable=False),
        sa.Column('targetType', sa.String(), nullable=False),
        sa.Column('upvote', sa.Boolean(), nullable=True),
        sa.Column('created', sa.DateTime(), nullable=True),
        sa.Column('updated', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('voteUri'),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('vote')
    # ### end Alembic commands ###

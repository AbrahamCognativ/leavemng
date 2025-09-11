"""add approval note columns

Revision ID: g7h8i9j0k1l2
Revises: f7a882b00958
Create Date: 2025-01-10 18:13:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'g7h8i9j0k1l2'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade():
    # Add approval_note column to leave_requests table
    op.add_column('leave_requests', sa.Column('approval_note', sa.Text(), nullable=True))
    
    # Add approval_note column to wfh_requests table
    op.add_column('wfh_requests', sa.Column('approval_note', sa.Text(), nullable=True))


def downgrade():
    # Remove approval_note column from wfh_requests table
    op.drop_column('wfh_requests', 'approval_note')
    
    # Remove approval_note column from leave_requests table
    op.drop_column('leave_requests', 'approval_note')
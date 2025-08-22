"""add_wfh_requests_table_only

Revision ID: add_wfh_table
Revises: 9f0ca599025c
Create Date: 2025-08-19 22:17:11.974139

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_wfh_table'
down_revision: Union[str, None] = '9f0ca599025c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Use existing WFH status enum
    wfh_status_enum = postgresql.ENUM('pending', 'approved', 'rejected', 'cancelled', name='wfhstatusenum', create_type=False)
    
    # Create wfh_requests table
    op.create_table('wfh_requests',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('status', wfh_status_enum, nullable=False, default='pending'),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('decision_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('decided_by', sa.UUID(), nullable=True),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['decided_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('wfh_requests')
    
    # Drop the enum type
    wfh_status_enum = postgresql.ENUM('pending', 'approved', 'rejected', 'cancelled', name='wfhstatusenum')
    wfh_status_enum.drop(op.get_bind())
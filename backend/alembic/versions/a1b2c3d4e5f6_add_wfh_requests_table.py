"""add_wfh_requests_table

Revision ID: a1b2c3d4e5f6
Revises: 9f0ca599025c
Create Date: 2025-08-19 22:17:11.974139

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '9f0ca599025c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Check if table already exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if 'wfh_requests' not in existing_tables:
        # Create WFH status enum
        wfh_status_enum = postgresql.ENUM('pending', 'approved', 'rejected', 'cancelled', name='wfhstatusenum', create_type=True)
        
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
    op.drop_table('wfh_requests')
    wfh_status_enum = postgresql.ENUM('pending', 'approved', 'rejected', 'cancelled', name='wfhstatusenum')
    wfh_status_enum.drop(op.get_bind())
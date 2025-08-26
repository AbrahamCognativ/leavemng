"""add_policy_acknowledgments_table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2025-08-25 08:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None

def upgrade():
    # Check if table already exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if 'policy_acknowledgments' not in existing_tables:
        op.create_table('policy_acknowledgments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('policy_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('signature_data', sa.Text(), nullable=True),
        sa.Column('signature_method', sa.String(), nullable=True),
        sa.Column('notification_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notification_read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reminder_count', sa.String(), nullable=True),
        sa.Column('is_acknowledged', sa.Boolean(), nullable=False),
        sa.Column('acknowledgment_deadline', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['policy_id'], ['policies.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        
        # Create unique constraint and indexes
        op.create_index('idx_policy_user_acknowledgment', 'policy_acknowledgments', ['policy_id', 'user_id'], unique=True)
        op.create_index('idx_policy_acknowledgments_policy_id', 'policy_acknowledgments', ['policy_id'])
        op.create_index('idx_policy_acknowledgments_user_id', 'policy_acknowledgments', ['user_id'])
        op.create_index('idx_policy_acknowledgments_deadline', 'policy_acknowledgments', ['acknowledgment_deadline'])
        op.create_index('idx_policy_acknowledgments_acknowledged', 'policy_acknowledgments', ['is_acknowledged'])

def downgrade():
    op.drop_index('idx_policy_acknowledgments_acknowledged', table_name='policy_acknowledgments')
    op.drop_index('idx_policy_acknowledgments_deadline', table_name='policy_acknowledgments')
    op.drop_index('idx_policy_acknowledgments_user_id', table_name='policy_acknowledgments')
    op.drop_index('idx_policy_acknowledgments_policy_id', table_name='policy_acknowledgments')
    op.drop_index('idx_policy_user_acknowledgment', table_name='policy_acknowledgments')
    op.drop_table('policy_acknowledgments')
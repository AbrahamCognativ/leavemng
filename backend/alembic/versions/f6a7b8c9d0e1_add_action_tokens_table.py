"""add action tokens table

Revision ID: f6a7b8c9d0e1
Revises: 2331d51b0c12
Create Date: 2025-01-09 16:38:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f6a7b8c9d0e1'
down_revision = '2331d51b0c12'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum type for action types with proper error handling
    connection = op.get_bind()
    
    # Check if enum exists and create if it doesn't
    enum_exists = connection.execute(sa.text(
        "SELECT 1 FROM pg_type WHERE typname = 'actiontypeenum'"
    )).fetchone()
    
    if not enum_exists:
        connection.execute(sa.text(
            "CREATE TYPE actiontypeenum AS ENUM ('wfh_approve', 'wfh_reject', 'leave_approve', 'leave_reject')"
        ))
    
    # Check if table exists and create if it doesn't
    table_exists = connection.execute(sa.text(
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'action_tokens' AND table_schema = 'public'"
    )).fetchone()
    
    if not table_exists:
        connection.execute(sa.text("""
            CREATE TABLE action_tokens (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                resource_type VARCHAR NOT NULL,
                resource_id UUID NOT NULL,
                approver_id UUID NOT NULL,
                action_type actiontypeenum NOT NULL,
                token VARCHAR UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                CONSTRAINT fk_action_tokens_approver FOREIGN KEY (approver_id) REFERENCES users(id)
            )
        """))
        
        # Create index for performance
        connection.execute(sa.text(
            "CREATE INDEX idx_action_tokens_token ON action_tokens(token)"
        ))
        connection.execute(sa.text(
            "CREATE INDEX idx_action_tokens_resource ON action_tokens(resource_type, resource_id)"
        ))


def downgrade() -> None:
    # Clean downgrade - drop table and enum if they exist
    connection = op.get_bind()
    
    # Drop table if it exists
    connection.execute(sa.text("DROP TABLE IF EXISTS action_tokens CASCADE"))
    
    # Only drop enum if no other tables are using it
    enum_usage = connection.execute(sa.text("""
        SELECT 1 FROM information_schema.columns
        WHERE udt_name = 'actiontypeenum'
        AND table_name != 'action_tokens'
    """)).fetchone()
    
    if not enum_usage:
        connection.execute(sa.text("DROP TYPE IF EXISTS actiontypeenum"))
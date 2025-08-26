"""sync_migration_state

Revision ID: 2331d51b0c12
Revises: c3d4e5f6a7b8
Create Date: 2025-08-26 19:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2331d51b0c12'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None

def upgrade():
    # This migration syncs the state - no changes needed
    # All tables should already exist from previous migrations
    pass

def downgrade():
    # No downgrade needed for sync migration
    pass
# scripts/clear_db.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.db.session import SessionLocal
from app.db.base import Base  # Make sure this imports all your models
from app.models import user, org_unit, leave_type, leave_balance, leave_request, leave_document, audit_log

from sqlalchemy import inspect, text

def clear_all_tables():
    session = SessionLocal()
    meta = Base.metadata
    conn = session.connection()
    try:
        # Disable FK constraints for the session (Postgres)
        conn.execute(text("SET session_replication_role = replica;"))
        for table in reversed(meta.sorted_tables):
            conn.execute(table.delete())
        conn.execute(text("SET session_replication_role = DEFAULT;"))
        session.commit()
        print("All tables cleared.")
    except Exception as e:
        session.rollback()
        print("Error:", e)
    finally:
        session.close()

if __name__ == "__main__":
    clear_all_tables()


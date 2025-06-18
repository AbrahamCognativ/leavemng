# scripts/clear_db.py
from sqlalchemy import text
from app.db.base import Base  # Make sure this imports all your models
from app.db.session import SessionLocal
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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
    except (AttributeError, TypeError, Exception) as e:
        session.rollback()
        print("Error:", e)
    finally:
        session.close()


if __name__ == "__main__":
    clear_all_tables()

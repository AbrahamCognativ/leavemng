# Placeholder for DB session management
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


try:
    # If running inside FastAPI, get DB_URL from app.state.settings
    from fastapi import Request
    from app.settings import get_settings
    import contextvars

    _request: Request = contextvars.ContextVar('request').get(None)
    if _request is not None:
        DATABASE_URL = _request.app.state.settings.DB_URL
    else:
        DATABASE_URL = get_settings().DB_URL
except Exception:
    # Fallback for CLI/migrations
    from app.settings import get_settings
    DATABASE_URL = get_settings().DB_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

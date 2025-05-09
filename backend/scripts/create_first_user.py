# scripts/insert_first_user.py
"""
Script to insert the first user into the database. Intended for use in Docker or local dev setup.
"""
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.models.user import User
from app.db.base import Base
import uuid

from app.settings import get_settings

settings = get_settings()
DATABASE_URL = settings.DB_URL

engine = create_engine(DATABASE_URL)
Base.metadata.bind = engine

FIRST_USER = {
    "id": uuid.UUID("4c6a745a-bb63-4a9a-8916-f27ffd1bd63d"),
    "name": "User User",
    "email": "user@example.com",
    "hashed_password": "secret123",  # Replace with hashed password in production!
    "role_band": "Admin",
    "role_title": "Developer",
    "gender": "male",
    "passport_or_id_number": "111111",
    "profile_image_url": None,
    "manager_id": None,
    "org_unit_id": None,
    "is_active": True,
    "extra_metadata": None
}

def insert_first_user():
    session = Session(bind=engine)
    user = session.query(User).filter_by(id=FIRST_USER["id"]).first()
    if not user:
        user = User(**FIRST_USER)
        session.add(user)
        session.commit()
        print("First user inserted.")
    else:
        print("User already exists.")
    session.close()

if __name__ == "__main__":
    insert_first_user()

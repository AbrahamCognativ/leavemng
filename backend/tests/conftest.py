import hashlib
from app.utils.password import hash_password
from app.models.user import User
import pytest
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.org_unit import OrgUnit
from uuid import uuid4


@pytest.fixture(scope="session")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session")
def org_unit_id(db_session: Session):
    # Create a dummy org unit if not exists
    unit = db_session.query(OrgUnit).first()
    if not unit:
        unit = OrgUnit(id=uuid4(), name="Test Org Unit")
        db_session.add(unit)
        db_session.commit()
        db_session.refresh(unit)
    return str(unit.id)


@pytest.fixture(scope="session")
def seeded_admin(db_session: Session, org_unit_id):
    """Create the very first admin user directly in the DB."""
    # Remove old invalid admin if exists
    old_admin = db_session.query(User).filter(
        User.email == "admin_test@seed.local").first()
    if old_admin:
        from sqlalchemy import text
        db_session.execute(
            text("DELETE FROM leave_balances WHERE user_id = :user_id"), {
                "user_id": old_admin.id})
        db_session.delete(old_admin)
        db_session.commit()
    admin_email = "admin_test@example.com"
    admin = db_session.query(User).filter_by(email=admin_email).first()
    if not admin:
        admin = User(
            name="Seed Admin",
            email=admin_email,
            hashed_password=hash_password("adminpass"),
            role_band="Admin",
            role_title="Admin",
            passport_or_id_number=str(uuid4()),
            org_unit_id=org_unit_id,
            is_active=True,
            gender="male",
            id=uuid4()
        )
        db_session.add(admin)
        db_session.commit()
        db_session.refresh(admin)
    return {"id": str(admin.id), "email": admin_email, "password": "adminpass"}


@pytest.fixture(scope="session", autouse=False)
def cleanup_seeded_admin(db_session):
    """Delete the seeded admin user after tests."""
    admin_email = "admin_test@example.com"
    admin = db_session.query(User).filter_by(email=admin_email).first()
    if admin:
        db_session.delete(admin)
        db_session.commit()


@pytest.fixture(scope="session")
def seeded_leave_type(db_session):
    from app.models.leave_type import LeaveType
    leave_type = db_session.query(LeaveType).first()
    if not leave_type:
        leave_type = LeaveType(name="Annual", description="Annual Leave")
        db_session.add(leave_type)
        db_session.commit()
        db_session.refresh(leave_type)
    return leave_type

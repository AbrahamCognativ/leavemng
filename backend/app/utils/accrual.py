import datetime
from sqlalchemy.orm import Session
from decimal import Decimal
from app.models.leave_balance import LeaveBalance
from app.models.leave_policy import LeavePolicy, AccrualFrequencyEnum
from app.models.leave_type import LeaveType
from app.models.user import User
from app.utils.audit_log_utils import log_audit


def add_existing_users_to_leave_balances(db: Session):
    from app.models.leave_type import LeaveType, LeaveCodeEnum
    from app.models.leave_policy import LeavePolicy
    today = datetime.date.today()
    # Ensure all active users have LeaveBalance for every leave type
    active_users = db.query(User).filter(User.is_active == True).all()
    leave_types = db.query(LeaveType).all()
    for user in active_users:
        for leave_type in leave_types:
            exists = db.query(LeaveBalance).filter_by(user_id=user.id, leave_type_id=leave_type.id).first()
            if not exists:
                bal = LeaveBalance(
                    user_id=user.id,
                    leave_type_id=leave_type.id,
                    balance_days=leave_type.default_allocation_days if hasattr(leave_type, 'default_allocation_days') else 0,
                    updated_at=datetime.datetime.now(datetime.timezone.utc)
                )
                db.add(bal)
    db.commit()
    log_audit(db, "Add Existing Users to Leave Balances", "Added existing users to leave balances.")


def test_accrue_annual_leave(db: Session):
    """
    TEST FUNCTION: Add 2 days to the annual leave balance for all active users, for testing purposes only.
    """
    pass
    # from app.models.leave_type import LeaveType, LeaveCodeEnum
    # from decimal import Decimal
    # # Find the annual leave type
    # annual_leave_type = db.query(LeaveType).filter(LeaveType.code == LeaveCodeEnum.annual).first()
    # if not annual_leave_type:
    #     log_audit(db, "Test Annual Leave Accrual", "No annual leave type found. No database update was done.")
    #     return
    # users = db.query(User).filter(User.is_active == True).all()
    # for user in users:
    #     bal = db.query(LeaveBalance).filter_by(user_id=user.id, leave_type_id=annual_leave_type.id).first()
    #     if not bal:
    #         bal = LeaveBalance(user_id=user.id, leave_type_id=annual_leave_type.id, balance_days=0)
    #         db.add(bal)
    #     bal.balance_days = (bal.balance_days or Decimal(0)) + Decimal(2)
    # db.commit()
    # log_audit(db, "Test Annual Leave Accrual", {"users": [user.email for user in users]})


# def accrue_annual_leave_balances(db: Session):
#     """
#     Accrue annual leave for all active users by adding the policy's accrual_amount_per_period to their balance.
#     Does not cap by entitlement or check taken leave (simple accrual).
#     """
#     from app.models.leave_type import LeaveType, LeaveCodeEnum
#     from app.models.leave_policy import LeavePolicy
#     from decimal import Decimal
#     # Find annual leave type and policy
#     annual_leave_type = db.query(LeaveType).filter(LeaveType.code == LeaveCodeEnum.annual).first()
#     if not annual_leave_type:
#         log_audit(db, "Annual Leave Accrual", "No annual leave type found. No database update was done.")
#         return
#     policy = db.query(LeavePolicy).filter(LeavePolicy.leave_type_id == annual_leave_type.id).first()
#     if not policy:
#         log_audit(db, "Annual Leave Accrual", "No annual leave policy found. No database update was done.")
#         return
#     accrual_amount = Decimal(str(policy.accrual_amount_per_period or 0))
#     users = db.query(User).filter(User.is_active == True).all()
#     for user in users:
#         bal = db.query(LeaveBalance).filter_by(user_id=user.id, leave_type_id=annual_leave_type.id).first()
#         if not bal:
#             bal = LeaveBalance(user_id=user.id, leave_type_id=annual_leave_type.id, balance_days=0)
#             db.add(bal)
#         bal.balance_days = (bal.balance_days or Decimal(0)) + accrual_amount
#     db.commit()
#     log_audit(db, "Annual Leave Accrual", f"Added {accrual_amount} days to all annual leave balances for active users.")


def accrue_monthly_leave_balances(db: Session):
    """
    Accrue all monthly leave types for all active users.
    """
    from app.models.leave_policy import LeavePolicy, AccrualFrequencyEnum
    from app.models.leave_type import LeaveType
    from decimal import Decimal
    policies = db.query(LeavePolicy).filter(LeavePolicy.accrual_frequency == AccrualFrequencyEnum.monthly).all()
    if not policies:
        log_audit(db, "Monthly Leave Accrual", "No monthly leave policy found. No database update was done.")
        return
    users = db.query(User).filter(User.is_active == True).all()
    affected_types = []
    for policy in policies:
        leave_type = db.query(LeaveType).filter(LeaveType.id == policy.leave_type_id).first()
        if not leave_type:
            continue
        accrual_amount = Decimal(str(policy.accrual_amount_per_period or 0))
        affected_types.append(f"{leave_type.code if hasattr(leave_type, 'code') else leave_type.id}")
        for user in users:
            bal = db.query(LeaveBalance).filter_by(user_id=user.id, leave_type_id=leave_type.id).first()
            if not bal:
                bal = LeaveBalance(user_id=user.id, leave_type_id=leave_type.id, balance_days=0)
                db.add(bal)
            bal.balance_days = (bal.balance_days or Decimal(0)) + accrual_amount
    db.commit()
    log_audit(db, "Monthly Leave Accrual", f"Updated leave types: {', '.join(affected_types)}. Accrued {accrual_amount} days per active user (per policy).")

def accrue_quarterly_leave_balances(db: Session):
    """
    Accrue all quarterly leave types for all active users.
    """
    from app.models.leave_policy import LeavePolicy, AccrualFrequencyEnum
    from app.models.leave_type import LeaveType
    from decimal import Decimal
    policies = db.query(LeavePolicy).filter(LeavePolicy.accrual_frequency == AccrualFrequencyEnum.quarterly).all()
    if not policies:
        log_audit(db, "Quarterly Leave Accrual", "No quarterly leave policy found. No database update was done.")
        return
    users = db.query(User).filter(User.is_active == True).all()
    affected_types = []
    for policy in policies:
        leave_type = db.query(LeaveType).filter(LeaveType.id == policy.leave_type_id).first()
        if not leave_type:
            continue
        accrual_amount = Decimal(str(policy.accrual_amount_per_period or 0))
        affected_types.append(f"{leave_type.code if hasattr(leave_type, 'code') else leave_type.id}")
        for user in users:
            bal = db.query(LeaveBalance).filter_by(user_id=user.id, leave_type_id=leave_type.id).first()
            if not bal:
                bal = LeaveBalance(user_id=user.id, leave_type_id=leave_type.id, balance_days=0)
                db.add(bal)
            bal.balance_days = (bal.balance_days or Decimal(0)) + accrual_amount
    db.commit()
    log_audit(db, "Quarterly Leave Accrual", f"Updated leave types: {', '.join(affected_types)}. Accrued {accrual_amount} days per active user (per policy).")

def accrue_yearly_leave_balances(db: Session):
    """
    Accrue all yearly leave types for all active users.
    """
    from app.models.leave_policy import LeavePolicy, AccrualFrequencyEnum
    from app.models.leave_type import LeaveType
    from decimal import Decimal
    policies = db.query(LeavePolicy).filter(LeavePolicy.accrual_frequency == AccrualFrequencyEnum.yearly).all()
    if not policies:
        log_audit(db, "Yearly Leave Accrual", "No yearly leave policy found. No database update was done.")
        return
    users = db.query(User).filter(User.is_active == True).all()
    affected_types = []
    for policy in policies:
        leave_type = db.query(LeaveType).filter(LeaveType.id == policy.leave_type_id).first()
        if not leave_type:
            continue
        accrual_amount = Decimal(str(policy.accrual_amount_per_period or 0))
        affected_types.append(f"{leave_type.code if hasattr(leave_type, 'code') else leave_type.id}")
        for user in users:
            bal = db.query(LeaveBalance).filter_by(user_id=user.id, leave_type_id=leave_type.id).first()
            if not bal:
                bal = LeaveBalance(user_id=user.id, leave_type_id=leave_type.id, balance_days=0)
                db.add(bal)
            bal.balance_days = (bal.balance_days or Decimal(0)) + accrual_amount
    db.commit()
    log_audit(db, "Yearly Leave Accrual", f"Updated leave types: {', '.join(affected_types)}. Accrued {accrual_amount} days per active user (per policy).")


def reset_annual_leave_carry_forward(db: Session):
    """
    At end of December, reset annual leave balances above 5 to 5 days (carry forward rule).
    Should be run once per year (e.g., via scheduled job).
    """
    from app.models.leave_type import LeaveCodeEnum, LeaveType
    from app.models.leave_balance import LeaveBalance
    from sqlalchemy.orm import joinedload
    annual_type = db.query(LeaveType).filter(LeaveType.code == LeaveCodeEnum.annual).first()
    if not annual_type:
        return
    # balances = db.query(LeaveBalance).options(joinedload(LeaveBalance.user_id)).filter(LeaveBalance.leave_type_id == annual_type.id).all()
    balances = db.query(LeaveBalance).filter(LeaveBalance.leave_type_id == annual_type.id).all()
    for bal in balances:
        if bal.balance_days > 5:
            bal.balance_days = Decimal(5)
    db.commit()
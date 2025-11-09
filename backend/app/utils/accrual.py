import datetime
from sqlalchemy.orm import Session, joinedload
from decimal import Decimal
from app.models.leave_balance import LeaveBalance
from app.models.leave_policy import AccrualFrequencyEnum
from app.models.leave_type import LeaveType
from app.models.user import User
from app.models.leave_policy import LeavePolicy
from app.utils.audit_log_utils import log_audit


def add_existing_users_to_leave_balances(db: Session):
    # Ensure all active users have LeaveBalance for every leave type
    active_users = db.query(User).filter(User.is_active).all()
    leave_types = db.query(LeaveType).all()
    for user in active_users:
        for leave_type in leave_types:
            exists = db.query(LeaveBalance).filter_by(
                user_id=user.id, leave_type_id=leave_type.id).first()
            if not exists:
                bal = LeaveBalance(
                    user_id=user.id,
                    leave_type_id=leave_type.id,
                    balance_days=leave_type.default_allocation_days if hasattr(
                        leave_type,
                        'default_allocation_days') else 0,
                    updated_at=datetime.datetime.now(
                        datetime.timezone.utc))
                db.add(bal)
    db.commit()
    log_audit(db, "Add Existing Users to Leave Balances",
              "Added existing users to leave balances.")


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
    FIXED VERSION: Only applies policies to users in the correct organization.
    """
    from app.models.leave_policy import LeavePolicy
    from app.models.org_unit import OrgUnit
    
    policies = db.query(LeavePolicy).filter(
        LeavePolicy.accrual_frequency == AccrualFrequencyEnum.monthly).all()
    
    if not policies:
        log_audit(
            db,
            "Monthly Leave Accrual",
            "No monthly leave policy found. No database update was done.")
        return
    
    users = db.query(User).filter(User.is_active).all()
    org_units = db.query(OrgUnit).all()

    from collections import defaultdict, deque

    children_by_parent = defaultdict(list)
    for unit in org_units:
        if unit.parent_unit_id:
            children_by_parent[unit.parent_unit_id].append(unit.id)

    def collect_org_tree(root_id):
        """Return the set of org unit IDs rooted at root_id (including root)."""
        if not root_id:
            return set()
        visited = set()
        queue = deque([root_id])
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            queue.extend(children_by_parent.get(current, []))
        return visited
    
    total_users_processed = 0
    policy_summaries = []
    
    for policy in policies:
        leave_type = db.query(LeaveType).filter(
            LeaveType.id == policy.leave_type_id).first()
        if not leave_type:
            continue
        accrual_amount = Decimal(str(policy.accrual_amount_per_period or 0))
        policy_org_ids = collect_org_tree(policy.org_unit_id)
        if not policy_org_ids:
            continue

        policy_users = [
            user for user in users
            if user.org_unit_id in policy_org_ids]
        if not policy_users:
            continue
        
        for user in policy_users:
            bal = db.query(LeaveBalance).filter_by(
                user_id=user.id, leave_type_id=leave_type.id).first()
            if not bal:
                bal = LeaveBalance(
                    user_id=user.id,
                    leave_type_id=leave_type.id,
                    balance_days=0)
                db.add(bal)
            old_balance = bal.balance_days or Decimal(0)
            bal.balance_days = old_balance + accrual_amount
            total_users_processed += 1
        policy_summaries.append(
            f"{leave_type.code if hasattr(leave_type, 'code') else leave_type.id}: "
            f"{accrual_amount} days x {len(policy_users)} users")
    
    db.commit()
    if not policy_summaries:
        log_audit(
            db,
            "Monthly Leave Accrual",
            "Monthly leave policies found but no eligible users matched the associated organization trees.")
    else:
        log_audit(
            db,
            "Monthly Leave Accrual",
            f"Updated {total_users_processed} users. Details: {', '.join(policy_summaries)}.")


def accrue_quarterly_leave_balances(db: Session):
    """
    Accrue all quarterly leave types for all active users.
    """
    policies = db.query(LeavePolicy).filter(
        LeavePolicy.accrual_frequency == AccrualFrequencyEnum.quarterly).all()
    if not policies:
        log_audit(
            db,
            "Quarterly Leave Accrual",
            "No quarterly leave policy found. No database update was done.")
        return
    users = db.query(User).filter(User.is_active).all()
    affected_types = []
    for policy in policies:
        leave_type = db.query(LeaveType).filter(
            LeaveType.id == policy.leave_type_id).first()
        if not leave_type:
            continue
        accrual_amount = Decimal(str(policy.accrual_amount_per_period or 0))
        affected_types.append(
            f"{leave_type.code if hasattr(leave_type, 'code') else leave_type.id}")
        for user in users:
            bal = db.query(LeaveBalance).filter_by(
                user_id=user.id, leave_type_id=leave_type.id).first()
            if not bal:
                bal = LeaveBalance(
                    user_id=user.id,
                    leave_type_id=leave_type.id,
                    balance_days=0)
                db.add(bal)
            bal.balance_days = (
                bal.balance_days or Decimal(0)) + accrual_amount
    db.commit()
    log_audit(
        db,
        "Quarterly Leave Accrual",
        f"Updated leave types: {', '.join(affected_types)}. Accrued {accrual_amount} days per active user (per policy).")


def accrue_yearly_leave_balances(db: Session):
    """
    Accrue all yearly leave types for all active users.
    """
    policies = db.query(LeavePolicy).filter(
        LeavePolicy.accrual_frequency == AccrualFrequencyEnum.yearly).all()
    if not policies:
        log_audit(
            db,
            "Yearly Leave Accrual",
            "No yearly leave policy found. No database update was done.")
        return
    users = db.query(User).filter(User.is_active).all()
    affected_types = []
    for policy in policies:
        leave_type = db.query(LeaveType).filter(
            LeaveType.id == policy.leave_type_id).first()
        if not leave_type:
            continue
        accrual_amount = Decimal(str(policy.accrual_amount_per_period or 0))
        affected_types.append(
            f"{leave_type.code if hasattr(leave_type, 'code') else leave_type.id}")
        for user in users:
            bal = db.query(LeaveBalance).filter_by(
                user_id=user.id, leave_type_id=leave_type.id).first()
            if not bal:
                bal = LeaveBalance(
                    user_id=user.id,
                    leave_type_id=leave_type.id,
                    balance_days=0)
                db.add(bal)
            bal.balance_days = (
                bal.balance_days or Decimal(0)) + accrual_amount
    db.commit()
    log_audit(
        db,
        "Yearly Leave Accrual",
        f"Updated leave types: {', '.join(affected_types)}. Accrued {accrual_amount} days per active user (per policy).")


def reset_annual_leave_carry_forward(db: Session):
    """
    At end of December, reset annual leave balances above 5 to 5 days (carry forward rule).
    Should be run once per year (e.g., via scheduled job).
    """
    from app.models.leave_type import LeaveCodeEnum, LeaveType
    annual_type = db.query(LeaveType).filter(
        LeaveType.code == LeaveCodeEnum.annual).first()
    if not annual_type:
        log_audit(
            db,
            "Annual Leave Carry Forward",
            "No annual leave type found. No database update was done.")

    else:
        # balances = db.query(LeaveBalance).options(joinedload(LeaveBalance.user_id)).filter(LeaveBalance.leave_type_id == annual_type.id).all()
        balances = db.query(LeaveBalance).filter(
            LeaveBalance.leave_type_id == annual_type.id).all()
        for bal in balances:
            if bal.balance_days > 5:
                bal.balance_days = Decimal(5)
    db.commit()


def reset_yearly_leave_balances_on_join_date(db: Session):
    """
    At midnight, check for all users who joined today (created_at) and reset their leave types with a policy of accrual frequency of yearly.
    Should be run once daily (e.g., via scheduled job).
    """
    today = datetime.date.today()
    today_month_day = (today.month, today.day)
    yearly_policies = db.query(LeavePolicy).filter(
        LeavePolicy.accrual_frequency == AccrualFrequencyEnum.yearly).all()
    if not yearly_policies:
        log_audit(
            db,
            "Yearly Leave Accrual",
            "No yearly leave policy found. No database update was done.")
        return
    from sqlalchemy import func
    users = db.query(User).filter(
        func.extract('month', User.created_at) == today_month_day[0],  # pylint: disable=not-callable
        func.extract('day', User.created_at) == today_month_day[1]  # pylint: disable=not-callable
    ).options(
        joinedload(User.leave_balances)
    ).all()
    if not users:
        log_audit(
            db,
            "Yearly Leave Accrual",
            "No users found who joined today. No database update was done.")
        return
    for user in users:
        for leave_balance in user.leave_balances:
            for policy in yearly_policies:
                if policy.leave_type_id == leave_balance.leave_type_id:
                    leave_balance.balance_days = Decimal(
                        policy.default_allocation_days or 0)
    db.commit()
    log_audit(
        db,
        "Yearly Leave Accrual",
        f"Reset yearly leave balances for {len(users)} users.")

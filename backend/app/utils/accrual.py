import datetime
from sqlalchemy.orm import Session
from decimal import Decimal
from app.models.leave_balance import LeaveBalance
from app.models.leave_policy import LeavePolicy, AccrualFrequencyEnum
from app.models.leave_type import LeaveType
from app.models.user import User

def accrue_leave_balances(db: Session):
    """
    Accrue leave balances for all users and policies. For annual leave, accrue only on weekdays, up to entitlement (max 19), and calculate year from joining date.
    """
    today = datetime.date.today()
    policies = db.query(LeavePolicy).all()
    for policy in policies:
        # Only accrue if monthly
        if policy.accrual_frequency != AccrualFrequencyEnum.monthly:
            continue
        # Ensure all active users in org_unit have a LeaveBalance for this leave_type
        active_users = db.query(User).filter(User.org_unit_id == policy.org_unit_id, User.is_active == True).all()
        for user in active_users:
            exists = db.query(LeaveBalance).filter_by(user_id=user.id, leave_type_id=policy.leave_type_id).first()
            if not exists:
                bal = LeaveBalance(user_id=user.id, leave_type_id=policy.leave_type_id, balance_days=0)
                db.add(bal)
        db.commit()
        users = db.query(User).filter(User.org_unit_id == policy.org_unit_id).all()
        for user in users:
            # Gender eligibility
            if hasattr(policy, 'leave_type') and hasattr(policy.leave_type, 'code'):
                code = policy.leave_type.code.value if hasattr(policy.leave_type.code, 'value') else str(policy.leave_type.code)
            else:
                code = None
            gender = None
            if user.extra_metadata:
                import json
                try:
                    gender = json.loads(user.extra_metadata).get('gender')
                except Exception:
                    pass
            if code == 'maternity' and gender != 'female':
                continue
            if code == 'paternity' and gender != 'male':
                continue
            # Find or create leave balance
            bal = db.query(LeaveBalance).filter_by(user_id=user.id, leave_type_id=policy.leave_type_id).first()
            if not bal:
                bal = LeaveBalance(user_id=user.id, leave_type_id=policy.leave_type_id, balance_days=0)
                db.add(bal)
            # --- Annual Leave Accrual Logic ---
            if code == 'annual':
                # Entitlement (max 19)
                entitlement = 19
                if policy.allocation_days_per_year:
                    entitlement = min(float(policy.allocation_days_per_year), 19)
                # Calculate accrual year from joining date
                join_date = user.created_at.date() if hasattr(user.created_at, 'date') else user.created_at
                accrual_year_start = join_date.replace(year=today.year)
                if accrual_year_start > today:
                    accrual_year_start = join_date.replace(year=today.year-1)
                accrual_year_end = accrual_year_start.replace(year=accrual_year_start.year+1)
                # Count weekdays in this month
                from calendar import monthrange
                first, last = today.replace(day=1), today.replace(day=monthrange(today.year, today.month)[1])
                weekdays_this_month = sum(1 for d in range((last-first).days+1)
                                         if (first+datetime.timedelta(days=d)).weekday() < 5)
                # Accrual per month = entitlement / # of months in year (assume 12)
                accrual_amount = entitlement / 12.0
                # Add to balance, but cap at entitlement
                # Calculate total taken in this accrual year
                from app.models.leave_request import LeaveRequest
                taken = db.query(LeaveRequest).filter(
                    LeaveRequest.user_id == user.id,
                    LeaveRequest.leave_type_id == policy.leave_type_id,
                    LeaveRequest.start_date >= accrual_year_start,
                    LeaveRequest.start_date < accrual_year_end,
                    LeaveRequest.status == 'approved'
                ).all()
                taken_days = sum(lr.total_days for lr in taken)
                # Cap balance to entitlement minus taken (cannot accrue above entitlement)
                new_balance = float(bal.balance_days or 0) + accrual_amount
                if new_balance + taken_days > entitlement:
                    new_balance = entitlement - taken_days
                bal.balance_days = Decimal(max(new_balance, 0))
            else:
                # Default accrual for other leave types
                bal.balance_days = (bal.balance_days or Decimal(0)) + Decimal(str(policy.accrual_amount_per_period or 0))
    db.commit()


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


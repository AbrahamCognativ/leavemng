import datetime
from sqlalchemy.orm import Session
from decimal import Decimal
from app.models.leave_balance import LeaveBalance
from app.models.leave_policy import LeavePolicy, AccrualFrequencyEnum
from app.models.leave_type import LeaveType
from app.models.user import User

def accrue_leave_balances(db: Session):
    today = datetime.date.today()
    policies = db.query(LeavePolicy).all()
    for policy in policies:
        # Only accrue if monthly
        if policy.accrual_frequency != AccrualFrequencyEnum.monthly:
            continue
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
            bal.balance_days = (bal.balance_days or Decimal(0)) + Decimal(str(policy.accrual_amount_per_period or 0))
    db.commit()


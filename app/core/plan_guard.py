from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models.subscription import Subscription
from app.core.auth_dependency import get_current_user
from app.db.models.user import User

def require_plan(required_plan: str):
    def checker(user: User = Depends(get_current_user)):
        db = SessionLocal()
        sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
        db.close()

        if not sub or sub.plan_type != required_plan:
            return {"error": f"{required_plan.upper()} plan required"}
        return user

    return checker

import stripe
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import STRIPE_SECRET_KEY
from app.db.session import SessionLocal
from app.db.models.subscription import Subscription
from app.db.models.user import User
from app.core.auth_dependency import get_current_user

stripe.api_key = STRIPE_SECRET_KEY

router = APIRouter(prefix="/billing", tags=["Billing"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/checkout")
def create_checkout(plan: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):

    PRICE_MAP = {
        "pro": "price_PRO_ID",
        "elite": "price_ELITE_ID",
        "recruiter": "price_RECRUITER_ID"
    }

    price_id = PRICE_MAP.get(plan)

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="subscription",
        customer_email=user.email,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url="http://localhost:3000/success",
        cancel_url="http://localhost:3000/cancel",
    )

    return {"checkout_url": session.url}

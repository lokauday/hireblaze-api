import stripe
from fastapi import APIRouter, Request, Header
from sqlalchemy.orm import Session
from app.core.config import STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET
from app.db.session import SessionLocal
from app.db.models.subscription import Subscription
from app.db.models.user import User

stripe.api_key = STRIPE_SECRET_KEY

router = APIRouter(prefix="/billing", tags=["Billing Webhook"])


def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
):
    payload = await request.body()
    db: Session = get_db()

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=STRIPE_WEBHOOK_SECRET,
        )
    except Exception as e:
        return {"error": f"Webhook verification failed: {str(e)}"}

    # ✅ PAYMENT COMPLETED EVENT
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        customer_email = session.get("customer_email")
        subscription_id = session.get("subscription")

        # ✅ Find user by email
        user = db.query(User).filter(User.email == customer_email).first()
        if not user:
            return {"error": "User not found for subscription"}

        sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()

        if not sub:
            sub = Subscription(user_id=user.id)
            db.add(sub)

        # ✅ Auto-upgrade plan (default Elite for now)
        sub.plan_type = "elite"
        sub.status = "active"
        sub.stripe_subscription_id = subscription_id
        sub.stripe_customer_id = session.get("customer")

        db.commit()

    return {"status": "success"}

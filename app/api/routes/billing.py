from fastapi import APIRouter, Request
import stripe
import os

router = APIRouter(prefix="/billing", tags=["Billing"])

# Load Stripe secret from Railway environment
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# ✅ HEALTH CHECK FOR BILLING
@router.get("/status")
def billing_status():
    return {"status": "billing service active"}

import stripe
from fastapi import APIRouter
from app.core.config import STRIPE_SECRET_KEY, STRIPE_PUBLIC_KEY

router = APIRouter()

stripe.api_key = STRIPE_SECRET_KEY

@router.post("/create-checkout-session")
async def create_checkout_session():
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="subscription",
        line_items=[{
            "price": "price_1Sd0OfPssaktksvXkv6fN5wG",  # replace with your Stripe price ID
            "quantity": 1,
        }],
        success_url="https://your-railway-url/success",
        cancel_url="https://your-railway-url/cancel",
    )

    return {"sessionId": session.id}


# ✅ STRIPE WEBHOOK
@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except Exception as e:
        return {"error": str(e)}

    if event["type"] == "checkout.session.completed":
        print("✅ Payment successful")

    return {"status": "success"}

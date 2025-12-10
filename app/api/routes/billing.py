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

# ✅ CREATE CHECKOUT SESSION
@router.post("/create-checkout-session")
def create_checkout():
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": "Hireblaze Pro"},
                        "unit_amount": 999,
                        "recurring": {"interval": "month"},
                    },
                    "quantity": 1,
                }
            ],
            success_url="https://your-frontend-url/success",
            cancel_url="https://your-frontend-url/cancel",
        )

        return {"checkout_url": session.url}

    except Exception as e:
        return {"error": str(e)}

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

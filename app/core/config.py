import os
from dotenv import load_dotenv

# Load environment variables from env file (or .env if exists)
load_dotenv(dotenv_path="env", override=False)
load_dotenv(dotenv_path=".env", override=False)

DATABASE_URL = os.getenv("DATABASE_URL")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_PRICE_ID_PRO = os.getenv("STRIPE_PRICE_ID_PRO")  # Stripe price ID for Pro plan
STRIPE_PRICE_ID_ELITE = os.getenv("STRIPE_PRICE_ID_ELITE")  # Stripe price ID for Elite plan

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

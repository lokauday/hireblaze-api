import os

# ✅ Database
DATABASE_URL = os.getenv("DATABASE_URL")

# ✅ Security
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

# ✅ OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ✅ Stripe
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

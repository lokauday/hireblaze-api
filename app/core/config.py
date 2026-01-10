import os
import secrets
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file (must be first)
# Use absolute path to ensure .env is found regardless of working directory
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Default to SQLite for local development if DATABASE_URL not set
    DATABASE_URL = "sqlite:///./hireblaze.db"
    logger.warning("DATABASE_URL not set. Using SQLite for local development.")

# SECRET_KEY: Required in production, but provide safe dev default for local
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if os.getenv("ENVIRONMENT") == "production" or os.getenv("RAILWAY_ENVIRONMENT"):
        raise ValueError("SECRET_KEY must be set in production environment")
    else:
        # Generate a random secret for local development (not secure for production!)
        SECRET_KEY = secrets.token_urlsafe(32)
        logger.warning("SECRET_KEY not set. Generated temporary key for local development. Set SECRET_KEY in production!")

ALGORITHM = os.getenv("ALGORITHM", "HS256")

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
STRIPE_PRICE_ID_PRO = os.getenv("STRIPE_PRICE_ID_PRO")
STRIPE_PRICE_ID_ELITE = os.getenv("STRIPE_PRICE_ID_ELITE")
STRIPE_PRICE_ID_PREMIUM = os.getenv("STRIPE_PRICE_ID_PREMIUM")  # Premium plan price ID
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Feature gating limits
MAX_FREE_AI_CALLS_PER_DAY = int(os.getenv("MAX_FREE_AI_CALLS_PER_DAY", "3"))

# Frontend URL for redirects
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

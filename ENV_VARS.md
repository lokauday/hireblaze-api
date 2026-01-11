# Environment Variables Documentation

This document lists all environment variables used by the Hireblaze API.

## Required for Production

### Database
- `DATABASE_URL` - PostgreSQL connection string (e.g., `postgresql://user:pass@host:5432/dbname`)
  - **Production**: Required
  - **Local**: Optional (defaults to SQLite `sqlite:///./hireblaze.db`)

### Security
- `SECRET_KEY` - Secret key for JWT token signing (generate with `secrets.token_urlsafe(32)`)
  - **Production**: Required
  - **Local**: Optional (auto-generated if not set)

### Authentication
- `ALGORITHM` - JWT algorithm (default: `HS256`)

## Stripe Integration (Required for Billing)

- `STRIPE_SECRET_KEY` - Stripe secret key (from Stripe Dashboard)
- `STRIPE_WEBHOOK_SECRET` - Stripe webhook signing secret (from Stripe Dashboard → Webhooks)
- `STRIPE_PRICE_ID_PRO` - Stripe price ID for Pro plan
- `STRIPE_PRICE_ID_ELITE` - Stripe price ID for Elite plan
- `STRIPE_PRICE_ID_PREMIUM` - Legacy Stripe price ID for Premium plan (maps to Pro)

## AI/LLM Integration

- `OPENAI_API_KEY` - OpenAI API key for AI features

## Feature Gating

- `MAX_FREE_AI_CALLS_PER_DAY` - Daily AI call limit for free users (default: `3`)

## Frontend/URLs

- `FRONTEND_URL` - Frontend URL for redirects (e.g., `https://hireblaze.vercel.app`)
- `PRODUCTION_FRONTEND_URL` - Production frontend URL (optional)
- `ALLOWED_ORIGINS` - Comma-separated list of allowed CORS origins (optional)

## Deployment

### Railway
Set all environment variables in Railway dashboard → Variables.

### Vercel (Frontend)
Set `NEXT_PUBLIC_API_BASE_URL` to your backend API URL.

## Health Check

The `/api/v1/health` endpoint is available for monitoring deployment health.

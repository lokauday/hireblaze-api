# Railway Deployment Guide - Hireblaze API

**Step-by-step deployment guide for Railway platform.**

---

## ✅ Pre-Deployment Checklist

Before deploying, ensure you have:
- [x] Committed all changes to git
- [x] Pushed to GitHub repository
- [x] Created Railway account
- [x] Connected Railway to your GitHub repository

---

## 🚀 Step 1: Create Railway Project

1. Go to [Railway.app](https://railway.app)
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose your `hireblaze-api` repository
5. Railway will automatically detect FastAPI

---

## 🔧 Step 2: Add PostgreSQL Database

1. In your Railway project, click **"+ New"**
2. Select **"Database"** → **"Add PostgreSQL"**
3. Railway will create a Postgres instance and inject `DATABASE_URL` automatically

**Important:** The `DATABASE_URL` will be automatically available to your service.

---

## ⚙️ Step 3: Configure Environment Variables

Go to your service → **Variables** tab and add/verify:

### Required Variables

```bash
DATABASE_URL=<Railway auto-injects this from Postgres plugin>
SECRET_KEY=<generate 32+ character random string>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

**Generate SECRET_KEY:**
```bash
# On Linux/Mac:
openssl rand -hex 32

# On Windows PowerShell:
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | % {[char]$_})
```

### Optional: AI Features

If you're using AI endpoints (`/ats/score`, `/tailor/resume`, etc.):

```bash
OPENAI_API_KEY=<your-openai-api-key>
```

### Optional: Stripe Billing

If you're using billing endpoints (`/billing/*`):

```bash
STRIPE_SECRET_KEY=sk_test_<your-stripe-secret-key>
STRIPE_PUBLIC_KEY=pk_test_<your-stripe-public-key>
STRIPE_WEBHOOK_SECRET=whsec_<your-webhook-secret>
STRIPE_PRICE_ID_PRO=price_<your-pro-plan-price-id>
STRIPE_PRICE_ID_ELITE=price_<your-elite-plan-price-id>
```

**⚠️ Important:** If Stripe variables are missing, billing endpoints will return errors. The app will still start, but billing features won't work.

---

## 🖥️ Step 4: Configure Start Command

Go to your service → **Settings** tab:

1. Scroll to **"Start Command"**
2. Set to:
   ```
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

**Important:** Railway injects `$PORT` automatically. Your app must bind to `0.0.0.0`, not `127.0.0.1`.

---

## 📦 Step 5: Deploy

1. Railway will automatically deploy when you push to `main` branch
2. Or click **"Deploy"** → **"Redeploy"** to trigger manual deploy
3. Monitor the **"Deployments"** tab for status
4. Check **"Logs"** tab for startup messages

---

## ✅ Step 6: Verify Deployment

### 1. Health Check

Open in browser or curl:
```
https://<your-service>.railway.app/health
```

**Expected Response:**
```json
{"status": "ok"}
```

### 2. API Docs

Open in browser:
```
https://<your-service>.railway.app/docs
```

You should see the Swagger UI with all endpoints.

### 3. Check Logs

In Railway → **Logs** tab, you should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:XXXX (Press CTRL+C to quit)
```

---

## 🔍 Troubleshooting

### Issue: `/health` returns 404

**Solution:** Check if the health endpoint is registered in `app/main.py`:
```python
app.include_router(system.router)  # Should include /health
```

### Issue: Database Connection Failed

**Symptoms:**
- Logs show "Database may not be accessible"
- 500 errors on database queries

**Solution:**
1. Verify `DATABASE_URL` is set in Railway Variables
2. Check that Postgres plugin is attached to your service
3. Verify `DATABASE_URL` format: `postgresql://user:password@host:port/dbname`
4. Check Railway logs for connection errors

### Issue: App Crashes on Startup

**Symptoms:**
- Deployment fails
- Logs show import errors or missing modules

**Solution:**
1. Check `requirements.txt` includes all dependencies
2. Verify Python version (should be 3.11+)
3. Check logs for specific error messages

### Issue: Stripe Routes Crash

**Symptoms:**
- App starts but `/billing/*` endpoints return 500 errors

**Solution:**
1. Ensure all Stripe environment variables are set:
   - `STRIPE_SECRET_KEY`
   - `STRIPE_WEBHOOK_SECRET`
   - `STRIPE_PRICE_ID_PRO`
   - `STRIPE_PRICE_ID_ELITE`
2. If Stripe is optional, billing routes should handle missing vars gracefully

### Issue: CORS Errors

**Symptoms:**
- Frontend can't connect to API
- Browser shows CORS errors

**Solution:**
1. Update `app/main.py` CORS config:
   ```python
   allow_origins=[
       "http://localhost:3000",
       "https://your-frontend-domain.com",  # Add your production frontend
   ]
   ```
2. Or use environment variable `ALLOWED_ORIGINS` (if implemented)

---

## 📊 Production Sanity Checks

### ✅ Check 1: Database Uses PostgreSQL

In Railway logs, look for:
- "Connected to postgres" or similar
- No SQLite references (unless intentionally using SQLite)

If you see SQLite in logs, `DATABASE_URL` isn't being read correctly.

### ✅ Check 2: Environment Variables Present

Add startup logging to verify env vars (without exposing values):

```python
# In app/main.py startup
logger.info("Environment check:")
logger.info(f"DATABASE_URL present: {bool(DATABASE_URL)}")
logger.info(f"SECRET_KEY present: {bool(SECRET_KEY)}")
logger.info(f"STRIPE_SECRET_KEY present: {bool(STRIPE_SECRET_KEY)}")
logger.info(f"OPENAI_API_KEY present: {bool(OPENAI_API_KEY)}")
```

---

## 🌐 Step 7: Custom Domain (Optional)

1. In Railway service → **Settings** → **Domains**
2. Click **"Generate Domain"** or add custom domain
3. Railway will provide SSL certificate automatically

---

## 📝 Environment Variables Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `DATABASE_URL` | ✅ Yes | Postgres connection string | `postgresql://user:pass@host:5432/db` |
| `SECRET_KEY` | ✅ Yes | JWT secret (32+ chars) | `your-secret-key-here` |
| `ALGORITHM` | ✅ Yes | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | ✅ Yes | Token expiration | `60` |
| `OPENAI_API_KEY` | ⚠️ Optional | OpenAI API key | `sk-...` |
| `STRIPE_SECRET_KEY` | ⚠️ Optional | Stripe secret key | `sk_test_...` |
| `STRIPE_PUBLIC_KEY` | ⚠️ Optional | Stripe public key | `pk_test_...` |
| `STRIPE_WEBHOOK_SECRET` | ⚠️ Optional | Webhook secret | `whsec_...` |
| `STRIPE_PRICE_ID_PRO` | ⚠️ Optional | Pro plan price ID | `price_...` |
| `STRIPE_PRICE_ID_ELITE` | ⚠️ Optional | Elite plan price ID | `price_...` |

---

## 🔄 Continuous Deployment

Railway automatically deploys when you push to the connected branch (usually `main`).

To disable auto-deploy:
1. Go to **Settings** → **Source**
2. Toggle **"Auto Deploy"** off

---

## 📚 Additional Resources

- [Railway Documentation](https://docs.railway.app)
- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)
- [PostgreSQL on Railway](https://docs.railway.app/databases/postgresql)

---

## ✅ Final Checklist

- [ ] PostgreSQL database added
- [ ] All required environment variables set
- [ ] Start command configured: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- [ ] `/health` endpoint responds with `{"status": "ok"}`
- [ ] `/docs` endpoint loads Swagger UI
- [ ] Database connection successful (check logs)
- [ ] No errors in Railway logs
- [ ] Custom domain configured (optional)

**🎉 Your API is now live on Railway!**

# Testing Guide - Usage Limits & Stripe Billing

## Prerequisites

1. Server running: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
2. Database initialized: Run `python -c "from app.db.init_db import *"`
3. Test user created (use `/auth/signup`)

---

## Test Flow 1: Usage Quota System

### Step 1: Create Test User

```bash
curl -X POST "http://127.0.0.1:8000/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Quota Test User",
    "email": "quotatest@example.com",
    "password": "testpass123",
    "visa_status": "Citizen"
  }'
```

### Step 2: Login and Get Token

```bash
curl -X POST "http://127.0.0.1:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=quotatest@example.com&password=testpass123"
```

**Save the `access_token` from response as `TOKEN`**

### Step 3: Check Initial Usage (Should be empty)

```bash
curl -X GET "http://127.0.0.1:8000/me/usage" \
  -H "Authorization: Bearer TOKEN"
```

**Expected Response:**
```json
{
  "plan": "free",
  "month_key": "2026-01",
  "features": {
    "ats_scan": {"limit": 2, "used": 0, "remaining": 2, "unlimited": false},
    "resume_tailor": {"limit": 3, "used": 0, "remaining": 3, "unlimited": false},
    "cover_letter": {"limit": 3, "used": 0, "remaining": 3, "unlimited": false},
    "jd_parse": {"limit": 5, "used": 0, "remaining": 5, "unlimited": false}
  }
}
```

### Step 4: Use ATS Scan (Should succeed - 1/2 used)

```bash
curl -X POST "http://127.0.0.1:8000/ats/score" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "resume_text": "Software engineer with 5 years Python experience",
    "jd_text": "Looking for Python developer with 3+ years experience"
  }'
```

**Expected:** Success response with ATS score

### Step 5: Check Usage After First Request

```bash
curl -X GET "http://127.0.0.1:8000/me/usage" \
  -H "Authorization: Bearer TOKEN"
```

**Expected:** `ats_scan` should show `"used": 1, "remaining": 1`

### Step 6: Use ATS Scan Again (Should succeed - 2/2 used)

```bash
curl -X POST "http://127.0.0.1:8000/ats/score" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "resume_text": "Test resume",
    "jd_text": "Test JD"
  }'
```

### Step 7: Try Third ATS Scan (Should fail with 429)

```bash
curl -X POST "http://127.0.0.1:8000/ats/score" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "resume_text": "Test resume",
    "jd_text": "Test JD"
  }'
```

**Expected Response (HTTP 429):**
```json
{
  "detail": {
    "error": "quota_exceeded",
    "feature": "ats_scan",
    "plan": "free",
    "limit": 2,
    "used": 2,
    "remaining": 0
  }
}
```

### Step 8: Verify Usage Didn't Increase

```bash
curl -X GET "http://127.0.0.1:8000/me/usage" \
  -H "Authorization: Bearer TOKEN"
```

**Expected:** `ats_scan` should still show `"used": 2, "remaining": 0` (not 3)

---

## Test Flow 2: Elite Plan (Unlimited)

### Step 1: Upgrade User to Elite (via database)

```sql
-- Connect to SQLite: sqlite3 hireblaze.db
UPDATE subscriptions SET plan_type = 'elite' WHERE user_id = <user_id>;
```

### Step 2: Check Usage (Should show unlimited)

```bash
curl -X GET "http://127.0.0.1:8000/me/usage" \
  -H "Authorization: Bearer TOKEN"
```

**Expected Response:**
```json
{
  "plan": "elite",
  "month_key": "2026-01",
  "features": {
    "ats_scan": {"limit": null, "used": 2, "remaining": null, "unlimited": true},
    ...
  }
}
```

### Step 3: Use ATS Scan Multiple Times (Should always succeed)

```bash
# Run this 10 times - all should succeed
for i in {1..10}; do
  curl -X POST "http://127.0.0.1:8000/ats/score" \
    -H "Authorization: Bearer TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "resume_text": "Test",
      "jd_text": "Test"
    }'
  echo ""
done
```

**All requests should return 200 OK** (no 429 errors)

---

## Test Flow 3: Stripe Billing (Stub-Ready)

### Step 1: Create Checkout Session (Without Stripe Keys - Will Error Gracefully)

```bash
curl -X POST "http://127.0.0.1:8000/billing/create-checkout-session" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "plan": "pro",
    "success_url": "http://localhost:3000/dashboard?success=true",
    "cancel_url": "http://localhost:3000/billing?canceled=true"
  }'
```

**Expected:** Error about invalid plan or missing Stripe config (expected without keys)

### Step 2: Create Checkout Session with Valid Stripe Setup

**Once Stripe keys are configured in .env:**
- Set `STRIPE_SECRET_KEY`, `STRIPE_PRICE_ID_PRO`, `STRIPE_PRICE_ID_ELITE`
- Then the above command should return:
```json
{
  "checkout_url": "https://checkout.stripe.com/pay/cs_test_...",
  "session_id": "cs_test_..."
}
```

### Step 3: Create Portal Session (Requires Active Subscription)

```bash
curl -X POST "http://127.0.0.1:8000/billing/create-portal-session" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "return_url": "http://localhost:3000/billing"
  }'
```

**Expected:** Returns portal URL or error if no Stripe customer exists

---

## Test Flow 4: All AI Endpoints with Quota

### Test Resume Tailor (Free: 3/month)

```bash
# Should work first 3 times
curl -X POST "http://127.0.0.1:8000/tailor/resume" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "resume_text": "My resume",
    "jd_text": "Job description"
  }'
```

### Test Cover Letter (Free: 3/month)

```bash
curl -X POST "http://127.0.0.1:8000/cover-letter/generate" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "resume_text": "My resume",
    "jd_text": "Job description"
  }'
```

### Test JD Parse (Free: 5/month)

```bash
curl -X POST "http://127.0.0.1:8000/jd/skills" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jd_text": "We need a Python developer with Django experience"
  }'
```

---

## PowerShell Commands (Windows)

```powershell
# Login
$loginResponse = Invoke-RestMethod -Uri "http://127.0.0.1:8000/auth/login" `
  -Method POST `
  -ContentType "application/x-www-form-urlencoded" `
  -Body "username=quotatest@example.com&password=testpass123"
$token = $loginResponse.access_token

# Get usage
Invoke-RestMethod -Uri "http://127.0.0.1:8000/me/usage" `
  -Headers @{Authorization = "Bearer $token"}

# Test ATS scan
Invoke-RestMethod -Uri "http://127.0.0.1:8000/ats/score" `
  -Method POST `
  -Headers @{
    Authorization = "Bearer $token"
    "Content-Type" = "application/json"
  } `
  -Body (@{
    resume_text = "Test resume"
    jd_text = "Test JD"
  } | ConvertTo-Json)
```

---

## Verification Checklist

- [ ] GET /me/usage returns correct structure
- [ ] Quota allows until limit
- [ ] Quota blocks after limit (429 error)
- [ ] Elite plan is unlimited
- [ ] Usage is recorded atomically
- [ ] Usage doesn't increase when quota exceeded
- [ ] All AI endpoints enforce quota
- [ ] Billing endpoints return proper structure (stub-ready)
- [ ] /docs endpoint shows clean API documentation

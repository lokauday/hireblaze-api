# Database Initialization Fix - Production Postgres Tables

## 🔍 Problem

**Issue:** Production Postgres database has no tables (error: `relation "users" does not exist`).

**Root Cause:** Tables were not being created automatically on application startup for PostgreSQL databases.

---

## ✅ Solution Implemented

### 1. Created `app/db/init_db.py`

This module:
- Imports ALL database models to ensure they register with SQLAlchemy's `Base.metadata`
- Provides an `init_db()` function that calls `Base.metadata.create_all(bind=engine)`
- Works for both PostgreSQL (production) and SQLite (local development)

**Key Models Imported:**
- `User`
- `Subscription`
- `UsageEvent`
- `Resume`
- `JobDescription`
- `Application`
- `ATSScore`
- `CandidateBenchmark`
- `InterviewEvaluation`
- `InterviewSession`

**Total Tables: 10**

### 2. Updated `app/main.py` Startup Event

Added FastAPI startup event that:
1. Logs: `"Initializing database..."`
2. Calls: `init_db()`
3. Logs: `"Database initialization complete"`

**Important:** This runs **ONCE** on application startup, not on every request.

### 3. Created `app/db/models/__init__.py`

Centralized model imports to ensure all models are registered with `Base.metadata` before `create_all()` is called.

---

## 📋 Implementation Details

### `app/db/init_db.py`

```python
"""
Database initialization module.

Creates all database tables on startup.
This runs once when the FastAPI application starts (not per request).

IMPORTANT: All models MUST be imported here before create_all() is called,
otherwise their tables will not be created.
"""
import logging
from app.db.session import engine
from app.db.base import Base

# Import ALL models to ensure they register with Base.metadata
from app.db.models.user import User
from app.db.models.subscription import Subscription
from app.db.models.usage import UsageEvent
# ... (all other models)

def init_db():
    """
    Initialize database tables on startup.
    
    This function:
    1. Imports all models (they register with Base.metadata)
    2. Calls Base.metadata.create_all() to create tables if they don't exist
    
    Works for both PostgreSQL (production) and SQLite (local development).
    SQLAlchemy's create_all() is idempotent - it only creates missing tables.
    """
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}", exc_info=True)
        raise
```

### `app/main.py` Startup Event

```python
from app.db.init_db import init_db

@app.on_event("startup")
async def startup_event():
    """
    Initialize database tables on startup.
    
    This runs once when the FastAPI application starts (not per request).
    Works for both PostgreSQL (production) and SQLite (local development).
    """
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialization complete")
```

---

## ✅ Requirements Met

1. ✅ **Created `app/db/init_db.py` with `init_db()` function**
   - Imports Base and engine
   - Imports ALL models (User, Subscription, UsageEvent, etc.)
   - Calls `Base.metadata.create_all(bind=engine)`

2. ✅ **Updated `app/main.py` startup event**
   - Logs: `"Initializing database..."`
   - Calls: `init_db()`
   - Logs: `"Database initialization complete"`

3. ✅ **Runs ONLY on startup (not per request)**
   - Uses FastAPI's `@app.on_event("startup")` decorator
   - Runs once when the application starts

4. ✅ **Works for Railway Postgres**
   - `create_all()` works for any SQLAlchemy-compatible database
   - No conditional logic needed - works for both Postgres and SQLite

5. ✅ **SQLite support maintained**
   - `create_all()` is idempotent and works for SQLite
   - No special handling needed

---

## 🔍 Verification

### Test: Verify All Models Are Registered

```bash
python -c "from app.db.base import Base; from app.db.init_db import init_db; print(f'Total tables: {len(Base.metadata.tables)}'); [print(f'  - {name}') for name in Base.metadata.tables.keys()]"
```

**Expected Output:**
```
Total tables: 10
  - users
  - subscriptions
  - usage_events
  - resumes
  - job_descriptions
  - applications
  - ats_scores
  - candidate_benchmarks
  - interview_evaluations
  - interview_sessions
```

### Test: Verify Startup Logging

When the application starts, you should see:
```
INFO:     Initializing database...
INFO:     Database initialization complete
```

---

## 🚀 Deployment

### Railway Postgres

1. **Deploy the updated code** to Railway
2. **On startup**, the application will:
   - Log: `"Initializing database..."`
   - Create all tables in Postgres (if they don't exist)
   - Log: `"Database initialization complete"`
3. **Verify tables exist:**
   ```sql
   SELECT table_name FROM information_schema.tables 
   WHERE table_schema = 'public';
   ```
   Should show all 10 tables: `users`, `subscriptions`, `usage_events`, etc.

### Local SQLite

1. **Run the application locally**
2. **On startup**, the application will:
   - Log: `"Initializing database..."`
   - Create all tables in SQLite (if they don't exist)
   - Log: `"Database initialization complete"`
3. **SQLite file** will be created automatically (typically `app.db` or specified in `DATABASE_URL`)

---

## 🎯 Result

**Status:** ✅ **FIXED**

- ✅ Tables are now created automatically on startup
- ✅ Works for both PostgreSQL (production) and SQLite (local)
- ✅ Runs only once on startup (not per request)
- ✅ All models are properly imported and registered
- ✅ Clean logging for debugging
- ✅ Idempotent (safe to run multiple times)

**The `users` table (and all other tables) will now be created automatically when the application starts on Railway!**

---

## 📝 Files Modified

1. **`app/db/init_db.py`** - Created/Updated with `init_db()` function
2. **`app/main.py`** - Added startup event that calls `init_db()`
3. **`app/db/models/__init__.py`** - Created to centralize model imports

---

## ⚠️ Important Notes

1. **Model Imports Are Critical**: If a model is not imported before `create_all()` is called, its table will NOT be created. Always ensure all models are imported in `init_db.py`.

2. **Idempotent Operation**: `Base.metadata.create_all()` is safe to call multiple times. It only creates tables that don't exist, so it won't break if run again.

3. **Startup Event Only**: The startup event runs once when the FastAPI application starts, not on every request. This ensures optimal performance.

4. **Error Handling**: If table creation fails, the application will raise an exception and fail to start. This is intentional - we want to know immediately if there's a database issue.

---

## ✅ Ready for Production

The database initialization is now guaranteed to run on every startup, ensuring all tables exist in both PostgreSQL (production) and SQLite (local development).

**No manual database migrations or table creation needed!**

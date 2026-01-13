import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, APIRouter
from dotenv import load_dotenv

# ✅ Load environment variables from .env file
load_dotenv()

# ✅ Import logging configuration first (before other imports that may log)
from app.core.logging_config import setup_logging
setup_logging(log_level="INFO")
logger = logging.getLogger(__name__)

# ✅ Import All API Routes (required - fail startup if missing)
from app.api.routes import auth, resume, jd, ats, cover_letter, tailor, interview, application, usage
from app.api.routes import resume_versions
from app.api.routes import billing, billing_webhook, system, health
from app.api.routes.documents import router as documents_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.history import router as history_router
from app.api.routes.ai import router as ai_router

# ✅ Import Core Services
from app.services.socket_manager import ConnectionManager
from app.services.ai_engine import generate_live_answer
from app.services.speech_engine import transcribe_audio_chunk
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import re

# ✅ Import database initialization
from app.db.init_db import init_db





# ============================================
# ✅ FASTAPI APP INIT
# ============================================

app = FastAPI(
    title="Hireblaze AI",
    description="AI-powered job application assistant with usage quotas and billing",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

logger.info("Hireblaze API starting up...")


# ============================================
# ✅ STARTUP EVENT - Database Initialization
# ============================================

@app.on_event("startup")
async def startup_event():
    """
    Initialize database tables and auth system on startup.
    
    This runs once when the FastAPI application starts (not per request).
    Works for both PostgreSQL (production) and SQLite (local development).
    """
    import os
    from app.core import config
    
    # Validate critical environment variables on startup
    logger.info("Validating environment variables...")
    
    # Validate DATABASE_URL
    if not config.DATABASE_URL or config.DATABASE_URL == "sqlite:///./hireblaze.db":
        if os.getenv("ENVIRONMENT") == "production" or os.getenv("RAILWAY_ENVIRONMENT"):
            logger.error("DATABASE_URL is not set in production environment")
            raise ValueError("DATABASE_URL must be set in production environment")
        else:
            logger.warning("DATABASE_URL not set. Using SQLite for local development.")
    
    # Validate SECRET_KEY (already validated in config.py, but verify it's not None)
    if not config.SECRET_KEY:
        logger.error("SECRET_KEY is not set")
        raise ValueError("SECRET_KEY must be set")
    
    logger.info("Environment variables validated")
    
    # Run Alembic migrations if RUN_MIGRATIONS env var is set
    run_migrations_env = os.getenv("RUN_MIGRATIONS", "").strip()
    run_migrations = run_migrations_env.lower() in ("true", "1", "yes")
    
    if run_migrations:
        logger.info(f"Running Alembic migrations (RUN_MIGRATIONS={run_migrations_env})...")
        try:
            from alembic.config import Config
            from alembic import command
            
            alembic_cfg = Config(os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic.ini"))
            command.upgrade(alembic_cfg, "head")
            logger.info("Alembic migrations completed successfully")
        except Exception as e:
            logger.error(f"Alembic migrations failed: {e}", exc_info=True)
            raise RuntimeError(f"Database migrations failed: {e}") from e
    else:
        # Only use init_db() for local development (SQLite)
        is_production = os.getenv("ENVIRONMENT") == "production" or os.getenv("RAILWAY_ENVIRONMENT")
        if not is_production and config.DATABASE_URL.startswith("sqlite"):
            logger.info("Skipping Alembic migrations (RUN_MIGRATIONS not set). Using init_db() for local development.")
            try:
                init_db()
                logger.info("Database initialization complete")
            except Exception as e:
                logger.error(f"Database initialization failed: {e}", exc_info=True)
                raise
        else:
            logger.info("Skipping Alembic migrations (RUN_MIGRATIONS not set). Database schema should be managed via migrations.")
    
    # Initialize auth system (verify bcrypt/passlib is working)
    try:
        from app.core.security import hash_password, verify_password, create_access_token
        # Test password hashing to ensure bcrypt is configured correctly
        test_hash = hash_password("test_password_123")
        assert verify_password("test_password_123", test_hash), "Password verification failed"
        # Test JWT token creation to ensure SECRET_KEY is valid
        test_token = create_access_token({"sub": "test@example.com"})
        assert test_token, "Token creation failed"
        logger.info("Auth system initialized successfully")
    except Exception as e:
        logger.error(f"Auth system initialization failed: {e}", exc_info=True)
        raise

# ✅ CORS — ALLOW FRONTEND ORIGINS
# Support local dev, Vercel previews, and production domains
import os

# Get explicit allowed origins from env var (comma-separated)
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins_list = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",  # Next.js fallback port when 3000 is in use
    "http://127.0.0.1:3001",
    "http://localhost:3002",  # Next.js fallback port when 3000 and 3001 are in use
    "http://127.0.0.1:3002",
]

# Add origins from ALLOWED_ORIGINS env var if provided
if ALLOWED_ORIGINS:
    allowed_origins_list.extend([origin.strip() for origin in ALLOWED_ORIGINS.split(",") if origin.strip()])

# Add common production domains from env vars
FRONTEND_URL = os.getenv("FRONTEND_URL", "")
if FRONTEND_URL and FRONTEND_URL not in allowed_origins_list:
    allowed_origins_list.append(FRONTEND_URL)

PRODUCTION_FRONTEND_URL = os.getenv("PRODUCTION_FRONTEND_URL", "")
if PRODUCTION_FRONTEND_URL and PRODUCTION_FRONTEND_URL not in allowed_origins_list:
    allowed_origins_list.append(PRODUCTION_FRONTEND_URL)

# Regex pattern to allow any *.vercel.app subdomain (for preview deployments)
# Note: This is regex ONLY, NOT in allow_origins list
vercel_preview_pattern = r"^https:\/\/.*\.vercel\.app$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins_list,
    allow_origin_regex=vercel_preview_pattern,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Range", "X-Total-Count"],
)



# ============================================
# ✅ REGISTER ALL ROUTERS WITH /api/v1 PREFIX
# ============================================

# Create API v1 router group
api_v1_router = APIRouter(prefix="/api/v1")

# ✅ Register API Routes under /api/v1 prefix
api_v1_router.include_router(auth.router)
api_v1_router.include_router(resume.router)
api_v1_router.include_router(resume_versions.router)
api_v1_router.include_router(jd.router, tags=["AI"])  # JD parsing
api_v1_router.include_router(ats.router, tags=["AI"])  # ATS scoring
api_v1_router.include_router(cover_letter.router, tags=["AI"])  # Cover letter generation
api_v1_router.include_router(tailor.router, tags=["AI"])  # Resume tailoring
api_v1_router.include_router(interview.router)
api_v1_router.include_router(application.router)
api_v1_router.include_router(usage.router)  # Usage tracking and quota info - now /api/v1/usage
api_v1_router.include_router(billing.router)  # Billing (checkout, portal)
api_v1_router.include_router(billing_webhook.router)  # Stripe webhooks
api_v1_router.include_router(system.router)
api_v1_router.include_router(health.router)
# ✅ Core routes (required - must be available)
api_v1_router.include_router(documents_router)  # AI Drive - Documents CRUD - now /api/v1/documents
api_v1_router.include_router(jobs_router)  # Job Tracker
api_v1_router.include_router(history_router)  # Activity History - now /api/v1/history
api_v1_router.include_router(ai_router)  # AI endpoints (job-match, recruiter-lens, interview-pack, outreach)

# Mount the API v1 router
app.include_router(api_v1_router)

# ✅ Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

logger.info("All routes registered successfully")




# ============================================
# ✅ WEBSOCKET MANAGER
# ============================================

manager = ConnectionManager()


# ============================================
# ✅ REAL-TIME TEXT + AUDIO COPILOT SOCKET
# ============================================

@app.websocket("/ws/copilot")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    manager.active_connections.append(websocket)

    try:
        while True:
            data = await websocket.receive()

            # ✅ TEXT MODE (Manual Typed Question)
            if "text" in data:
                question = data["text"]

            # ✅ AUDIO MODE (Real-Time Mic Streaming)
            elif "bytes" in data:
                question = await transcribe_audio_chunk(data["bytes"])

            else:
                continue

            # ✅ AI Answer Generation
            answer = generate_live_answer(
                question=question,
                resume_text="",
                jd_text=""
            )

            # ✅ Broadcast Answer to All Clients
            for connection in manager.active_connections:
                await connection.send_text(answer)

    except WebSocketDisconnect:
        manager.active_connections.remove(websocket)


# ============================================
# ✅ HEALTH CHECK ROOT ENDPOINT
# ============================================

@app.get("/")
def root():
    return {"status": "Hireblaze API running"}


from fastapi.responses import FileResponse
import os

# Serve payment page
@app.get("/pay")
def serve_payment_page():
    return FileResponse("frontend/static/copilot.html")


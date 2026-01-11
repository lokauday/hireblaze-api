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
from app.api.routes import billing, billing_webhook, system
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
    logger.info("Initializing database...")
    
    # Run Alembic migrations safely (idempotent)
    try:
        from alembic.config import Config
        from alembic import command
        import os
        
        alembic_cfg = Config(os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic.ini"))
        command.upgrade(alembic_cfg, "head")
        logger.info("Alembic migrations completed")
    except Exception as e:
        logger.warning(f"Alembic migrations failed (non-fatal): {e}. Tables will be created via init_db() if needed.")
        # Continue with init_db as fallback
    
    # Fallback: Initialize database tables (idempotent - only creates missing tables)
    init_db()
    logger.info("Database initialization complete")
    
    # Initialize auth system (verify bcrypt/passlib is working)
    try:
        from app.core.security import hash_password, verify_password
        # Test password hashing to ensure bcrypt is configured correctly
        test_hash = hash_password("test_password_123")
        assert verify_password("test_password_123", test_hash), "Password verification failed"
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


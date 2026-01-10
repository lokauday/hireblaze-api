import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# ✅ Import logging configuration first (before other imports that may log)
from app.core.logging_config import setup_logging
setup_logging(log_level="INFO")
logger = logging.getLogger(__name__)

# ✅ Import All API Routes (required - fail startup if missing)
from app.api.routes import auth, resume, jd, ats, cover_letter, tailor, interview, application, usage
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

# ✅ CORS LOCKDOWN — ONLY ALLOW YOUR FRONTEND
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",      # local frontend
        "http://127.0.0.1:3000",
        # "https://hireblaze.ai",     # uncomment when domain is live
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)



# ============================================
# ✅ REGISTER ALL ROUTERS
# ============================================

# ✅ Register API Routes
app.include_router(auth.router)
app.include_router(resume.router)
app.include_router(jd.router, tags=["AI"])  # JD parsing
app.include_router(ats.router, tags=["AI"])  # ATS scoring
app.include_router(cover_letter.router, tags=["AI"])  # Cover letter generation
app.include_router(tailor.router, tags=["AI"])  # Resume tailoring
app.include_router(interview.router)
app.include_router(application.router)
app.include_router(usage.router)  # Usage tracking and quota info
app.include_router(billing.router)  # Billing (checkout, portal)
app.include_router(billing_webhook.router)  # Stripe webhooks
app.include_router(system.router)
# ✅ Core routes (required - must be available)
app.include_router(documents_router)  # AI Drive - Documents CRUD
app.include_router(jobs_router)  # Job Tracker
app.include_router(history_router)  # Activity History
app.include_router(ai_router)  # AI endpoints (job-match, recruiter-lens, interview-pack, outreach)

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


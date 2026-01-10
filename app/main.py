from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from sqlalchemy import inspect, text

# ✅ Import All API Routes directly from route files
from app.api.routes.auth import router as auth_router
from app.api.routes.resume import router as resume_router
from app.api.routes.jd import router as jd_router
from app.api.routes.ats import router as ats_router
from app.api.routes.cover_letter import router as cover_letter_router
from app.api.routes.tailor import router as tailor_router
from app.api.routes.interview import router as interview_router
from app.api.routes.application import router as application_router
from app.api.routes.billing import router as billing_router
from app.api.routes.billing_webhook import router as billing_webhook_router
from app.api.routes.system import router as system_router
from app.api.routes.copilot_ws import router as copilot_ws_router

# ✅ Import Core Services
from app.services.socket_manager import ConnectionManager
from app.services.ai_engine import generate_live_answer
from app.services.speech_engine import transcribe_audio_chunk

# ✅ Import Database components for table creation
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.core.config import DATABASE_URL

logger = logging.getLogger(__name__)


# ✅ Startup logic: Ensure database tables exist
def init_db():
    """Create all database tables if they don't exist."""
    try:
        # Log database URL scheme (without secrets)
        if "@" in DATABASE_URL:
            db_parts = DATABASE_URL.split("@")
            if len(db_parts) > 1:
                scheme = db_parts[0].split("://")[0] if "://" in db_parts[0] else "unknown"
                host_info = db_parts[1].split("/")[0] if "/" in db_parts[1] else db_parts[1]
                logger.info(f"Database: {scheme}://...@{host_info}")
        else:
            scheme = DATABASE_URL.split("://")[0] if "://" in DATABASE_URL else DATABASE_URL
            logger.info(f"Database: {scheme}://...")
        
        # Import all models to register them with Base.metadata BEFORE checking tables
        # This ensures all table definitions are available
        from app.db.models.user import User
        from app.db.models.subscription import Subscription
        from app.db.models.resume import Resume
        from app.db.models.job import JobDescription
        from app.db.models.application import Application
        from app.db.models.ats_score import ATSScore
        from app.db.models.interview_session import InterviewSession
        from app.db.models.interview_evaluation import InterviewEvaluation
        from app.db.models.candidate_benchmark import CandidateBenchmark
        
        # Check if users table exists
        try:
            inspector = inspect(engine)
            existing_tables = inspector.get_table_names()
            
            if "users" not in existing_tables:
                logger.info("Users table not found. Creating all tables...")
                Base.metadata.create_all(bind=engine)
                logger.info("✅ Database tables created successfully")
            else:
                logger.info(f"✅ Database tables already exist ({len(existing_tables)} tables found)")
                
                # Verify users table has correct structure
                try:
                    db = SessionLocal()
                    db.execute(text("SELECT 1 FROM users LIMIT 1"))
                    db.close()
                    logger.info("✅ Users table verified and accessible")
                except Exception as e:
                    logger.warning(f"Users table exists but may have issues: {e}")
                    # Try to create missing tables
                    logger.info("Attempting to create missing tables...")
                    Base.metadata.create_all(bind=engine)
        except Exception as inspect_error:
            # If inspect fails (e.g., SQLite), try creating tables anyway
            logger.warning(f"Could not inspect database: {inspect_error}")
            logger.info("Creating all tables...")
            Base.metadata.create_all(bind=engine)
            logger.info("✅ Database tables created")
                
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}", exc_info=True)
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Hireblaze API...")
    init_db()
    yield
    # Shutdown (if needed)
    logger.info("Shutting down Hireblaze API...")





# ============================================
# ✅ FASTAPI APP INIT
# ============================================

app = FastAPI(title="Hireblaze AI", lifespan=lifespan)

# ✅ CORS LOCKDOWN — ONLY ALLOW YOUR FRONTEND
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",      # local frontend
        "http://127.0.0.1:3000",
        # "https://hireblaze.ai",     # uncomment when domain is live
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)



# ============================================
# ✅ REGISTER ALL ROUTERS
# ============================================

app.include_router(auth_router)
app.include_router(resume_router)
app.include_router(jd_router)
app.include_router(ats_router)
app.include_router(cover_letter_router)
app.include_router(tailor_router)
app.include_router(interview_router)
app.include_router(application_router)
app.include_router(billing_router)
app.include_router(billing_webhook_router)
app.include_router(system_router)
app.include_router(copilot_ws_router)
app.mount("/static", StaticFiles(directory="static"), name="static")




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
from fastapi.staticfiles import StaticFiles
import os

# Serve the static folder
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

@app.get("/pay")
def serve_payment_page():
    return FileResponse("frontend/static/copilot.html")


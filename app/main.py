from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# ✅ Import All API Routes
from app.api.routes import auth, resume, jd, ats, cover_letter, tailor, interview, application

# ✅ Import Core Services
from app.services.socket_manager import ConnectionManager
from app.services.ai_engine import generate_live_answer
from app.services.speech_engine import transcribe_audio_chunk
from fastapi.staticfiles import StaticFiles
from app.api.routes import billing
from app.api.routes import application
from app.api.routes import billing_webhook
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import system





# ============================================
# ✅ FASTAPI APP INIT
# ============================================

app = FastAPI(title="Hireblaze AI")

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

app.include_router(auth.router)
app.include_router(resume.router)
app.include_router(jd.router)
app.include_router(ats.router)
app.include_router(cover_letter.router)
app.include_router(tailor.router)
app.include_router(interview.router)
app.include_router(application.router)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(billing.router)
app.include_router(application.router)
app.include_router(billing_webhook.router)
app.include_router(system.router)




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

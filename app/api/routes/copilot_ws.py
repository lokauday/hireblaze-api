from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.socket_manager import ConnectionManager
from app.services.ai_engine import generate_live_answer

router = APIRouter()
manager = ConnectionManager()

@router.websocket("/ws/copilot")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        while True:
            data = await websocket.receive_text()

            answer = generate_live_answer(
                question=data,
                resume_text="",
                jd_text=""
            )

            await manager.broadcast(answer)

    except WebSocketDisconnect:
        manager.disconnect(websocket)

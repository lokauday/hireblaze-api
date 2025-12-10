import websocket

ws = websocket.WebSocket()
ws.connect("ws://127.0.0.1:8000/ws/copilot")

print("✅ Connected to Copilot WebSocket")

while True:
    question = input("Ask interview question: ")
    ws.send(question)

    answer = ws.recv()
    print("🤖 Copilot Answer:", answer)

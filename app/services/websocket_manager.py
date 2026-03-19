import json
from typing import Dict, List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # Maps session_id (int) to a list of active WebSockets
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: int):
        await websocket.accept()
        session_id = int(session_id)
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
        print(f"📡 WS connected to session {session_id}. Total connections: {len(self.active_connections[session_id])}")

    def disconnect(self, websocket: WebSocket, session_id: int):
        session_id = int(session_id)
        if session_id in self.active_connections:
            self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        print(f"🔌 WS disconnected from session {session_id}")

    async def _send_safe(self, websocket: WebSocket, message: dict, session_id: int):
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            print(f"❌ Error sending WS message: {e}")
            self.disconnect(websocket, session_id)

    async def broadcast_to_session(self, session_id: int, message: dict):
        session_id = int(session_id)
        if session_id in self.active_connections:
            conns = self.active_connections[session_id]
            print(f"📣 Broadcasting to session {session_id} ({len(conns)} connections)")
            import asyncio
            for connection in list(conns):
                asyncio.create_task(self._send_safe(connection, message, session_id))
        else:
            print(f"⚠️ No active WS connections for session {session_id}")

manager = ConnectionManager()

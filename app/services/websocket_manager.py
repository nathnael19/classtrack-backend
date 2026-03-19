import json
from typing import Dict, List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # Maps session_id (int) to a list of active WebSockets
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: int):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)

    def disconnect(self, websocket: WebSocket, session_id: int):
        if session_id in self.active_connections:
            self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def broadcast_to_session(self, session_id: int, message: dict):
        if session_id in self.active_connections:
            # Create a copy of the list to avoid issues with disconnects during iteration
            for connection in list(self.active_connections[session_id]):
                try:
                    await connection.send_text(json.dumps(message))
                except Exception:
                    # If broadcasting fails, the connection is likely dead
                    self.disconnect(connection, session_id)

manager = ConnectionManager()

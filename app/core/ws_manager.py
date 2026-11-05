import asyncio
import json
from typing import Dict, List, Set
from fastapi import WebSocket

class ConnectionManager:
    """Real-time WebSocket hub broadcasting live tournament score updates."""
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, tournament_id: str, websocket: WebSocket):
        await websocket.accept()
        if tournament_id not in self.active_connections:
            self.active_connections[tournament_id] = set()
        self.active_connections[tournament_id].add(websocket)

    def disconnect(self, tournament_id: str, websocket: WebSocket):
        if tournament_id in self.active_connections:
            self.active_connections[tournament_id].discard(websocket)

    async def broadcast(self, tournament_id: str, message: dict):
        if tournament_id in self.active_connections:
            dead_sockets = set()
            for ws in self.active_connections[tournament_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead_sockets.add(ws)
            for ws in dead_sockets:
                self.active_connections[tournament_id].discard(ws)

manager = ConnectionManager()

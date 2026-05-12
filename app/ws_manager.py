from fastapi import WebSocket
from typing import Dict, Set


class ConnectionManager:
    def __init__(self):
        # room_id → set of WebSocket connections
        self.rooms: Dict[str, Set[WebSocket]] = {}
        # user_id → WebSocket (presence tracking)
        self.users: Dict[str, WebSocket] = {}

    async def connect(self, ws: WebSocket, room_id: str, user_id: str):
        await ws.accept()
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
        self.rooms[room_id].add(ws)
        self.users[user_id] = ws

    def disconnect(self, ws: WebSocket, room_id: str, user_id: str):
        if room_id in self.rooms:
            self.rooms[room_id].discard(ws)
            if not self.rooms[room_id]:
                del self.rooms[room_id]
        self.users.pop(user_id, None)

    async def broadcast(self, room_id: str, payload: dict, exclude: WebSocket = None):
        """Room ke sabhi connected users ko message bhejo"""
        dead = set()
        for ws in self.rooms.get(room_id, set()).copy():
            if ws == exclude:
                continue
            try:
                await ws.send_json(payload)
            except Exception:
                dead.add(ws)
        # Dead connections clean karo
        for ws in dead:
            self.rooms.get(room_id, set()).discard(ws)

    async def send_to_user(self, user_id: str, payload: dict):
        """Kisi specific user ko direct message bhejo"""
        ws = self.users.get(user_id)
        if ws:
            try:
                await ws.send_json(payload)
            except Exception:
                self.users.pop(user_id, None)

    def online_count(self, room_id: str) -> int:
        return len(self.rooms.get(room_id, set()))

    def is_user_online(self, user_id: str) -> bool:
        return user_id in self.users

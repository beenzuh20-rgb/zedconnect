"""
WebRTC Signaling Server for ZedConnect
Handles WebSocket connections for video/audio call signaling
"""

import json
import logging
from fastapi import WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from app.database import get_db
from app import models, config

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for call signaling.
    Maps user_id -> list of active WebSocket connections
    """

    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"User {user_id} connected for signaling. Total connections: {len(self.active_connections[user_id])}")

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"User {user_id} disconnected from signaling")

    def is_user_online(self, user_id: int) -> bool:
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0

    async def send_personal_message(self, message: dict, user_id: int):
        """Send a message to all connections of a specific user"""
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending to user {user_id}: {e}")

    async def broadcast_to_others(self, message: dict, sender_id: int, target_id: int):
        """Send a message from sender to target user"""
        await self.send_personal_message(message, target_id)


# Global connection manager instance
manager = ConnectionManager()


async def get_user_from_token(token: str, db: Session) -> models.User | None:
    """Extract user from JWT token for WebSocket auth"""
    try:
        if token.startswith("Bearer "):
            token = token[7:].strip()
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            return None
        user = db.query(models.User).filter(models.User.id == int(user_id)).first()
        return user
    except JWTError as e:
        logger.error(f"Token decode error: {e}")
        return None


async def signaling_websocket(websocket: WebSocket, db: Session = Depends(get_db)):
    """
    WebSocket endpoint for WebRTC signaling.
    Expects a 'token' query parameter for authentication.
    Messages are JSON with 'type' field:
      - offer: {type: "offer", target_id: int, sdp: str}
      - answer: {type: "answer", target_id: int, sdp: str}
      - ice_candidate: {type: "ice_candidate", target_id: int, candidate: str}
      - end_call: {type: "end_call", target_id: int}
      - call_request: {type: "call_request", target_id: int, call_type: "video"|"audio"}
      - call_accepted: {type: "call_accepted", target_id: int}
      - call_rejected: {type: "call_rejected", target_id: int}
      - call_busy: {type: "call_busy", target_id: int}
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        return

    user = await get_user_from_token(token, db)
    if not user:
        await websocket.close(code=4001, reason="Invalid authentication token")
        return

    user_id = user.id
    await manager.connect(websocket, user_id)

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "call_request":
                target_id = data.get("target_id")
                call_type = data.get("call_type", "video")

                if manager.is_user_online(target_id):
                    # Check if target is not busy (has only 1 connection - the signaling one)
                    # Notify target user of incoming call
                    await manager.send_personal_message({
                        "type": "incoming_call",
                        "from_id": user_id,
                        "from_name": user.full_name or "Anonymous",
                        "from_picture": user.profile_picture_url or "/static/default_profile.png",
                        "call_type": call_type
                    }, target_id)
                else:
                    # Target user is offline
                    await manager.send_personal_message({
                        "type": "user_offline",
                        "target_id": target_id
                    }, user_id)

            elif msg_type == "call_accepted":
                target_id = data.get("target_id")
                await manager.send_personal_message({
                    "type": "call_accepted",
                    "from_id": user_id
                }, target_id)

            elif msg_type == "call_rejected":
                target_id = data.get("target_id")
                await manager.send_personal_message({
                    "type": "call_rejected",
                    "from_id": user_id
                }, target_id)

            elif msg_type == "offer":
                target_id = data.get("target_id")
                await manager.send_personal_message({
                    "type": "offer",
                    "from_id": user_id,
                    "sdp": data.get("sdp")
                }, target_id)

            elif msg_type == "answer":
                target_id = data.get("target_id")
                await manager.send_personal_message({
                    "type": "answer",
                    "from_id": user_id,
                    "sdp": data.get("sdp")
                }, target_id)

            elif msg_type == "ice_candidate":
                target_id = data.get("target_id")
                await manager.send_personal_message({
                    "type": "ice_candidate",
                    "from_id": user_id,
                    "candidate": data.get("candidate")
                }, target_id)

            elif msg_type == "end_call":
                target_id = data.get("target_id")
                await manager.send_personal_message({
                    "type": "call_ended",
                    "from_id": user_id
                }, target_id)

            elif msg_type == "call_busy":
                target_id = data.get("target_id")
                await manager.send_personal_message({
                    "type": "call_busy",
                    "from_id": user_id
                }, target_id)

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
        logger.info(f"User {user_id} WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(websocket, user_id)

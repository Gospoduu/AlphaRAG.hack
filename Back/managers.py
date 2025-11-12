from fastapi import WebSocket
from typing import List, Dict
from pydantic import BaseModel
from enum import Enum
from uuid import UUID
from fastapi.exceptions import HTTPException
from pydantic.mypy import PydanticModelField
from events import EventBase

class EventType(str, Enum):
    NEW_TOKEN = "new_token"
    END_GENERATION = "end_generation"
    OPERATOR_MESSAGE = "operator_message"
    PING = "ping"
    PONG = "pong"

class ConnectionManager:
    def __init__(self):
        self.active_connections : Dict[str, WebSocket] = {}
    async def connect(
            self,
            user_uuid: UUID,
            websocket: WebSocket
            ):
        await websocket.accept()
        self.active_connections[str(user_uuid)] = websocket
    def disconnect(self, user_uuid:UUID):
        ws = self.active_connections.pop(str(user_uuid), None)
        if ws:
            self.active_connections.pop(str(user_uuid), None)

    async def send_event(
            self,
            user_uuid: UUID,
            event: EventBase,):
        try:
            ws = self.active_connections.get(str(user_uuid)) or None
            if ws is None:
                return
            await ws.send_json(event.model_dump())
        except AttributeError as e:
            return
        except Exception:
            self.disconnect(user_uuid)
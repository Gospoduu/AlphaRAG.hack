from fastapi import WebSocket
from typing import Dict
from enum import Enum
from uuid import UUID
from Back.core.events_bus.events import EventBase

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
        print("new connection")

    def disconnect(self, user_uuid:UUID, websocket:WebSocket | None = None):
        key = str(user_uuid)
        current = self.active_connections.get(key)
        if current is None:
            print("disconnect: no active connection")
            return
        if websocket is not None and current is not websocket:
            print(
                "disconnect: skip, stored ws is different",
                key,
                "stored_id=", id(current),
                "closing_id=", id(websocket),
            )
            return
        self.active_connections.pop(str(user_uuid), None)
        print("disconnect", key)

    async def send_event(
            self,
            user_uuid: UUID,
            event: EventBase,)->bool:
        ws = None
        try:
            ws = self.active_connections.get(str(user_uuid))
            if ws is None:
                print("NO WS FOUND for user", str(user_uuid))
                return False
            print("active_connections KEYS:", list(self.active_connections.keys()))
            print("trying to send to:", str(user_uuid), "event:", event.event)

            payload = event.model_dump(mode="json")
            await ws.send_json(payload)
            print("send event - ok")
            return True
        except AttributeError as e:
            print("except send event -",e)
            return False
        except Exception as e:
            print(f"except send event and disconnect before\n{e}")
            self.disconnect(user_uuid, ws)
            return False

    async def get_all_connections(
            self
    ):
        all_connections = self.active_connections
        return all_connections

manager = ConnectionManager()
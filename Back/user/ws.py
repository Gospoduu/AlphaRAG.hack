# user/ws.py
from ..managers import ConnectionManager
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..chat.events import client_events_dict as chat_events
from ..events import client_events_dict as base_events
from ..events import ErrorEvent, UnknownEventTypeErrorData
from ..events import  PongEvent, PingEvent
from uuid import UUID

manager = ConnectionManager()

router = APIRouter()

client_events = chat_events + base_events

@router.websocket("/ws/{user_uuid}")
async def websocket_endpoint(websocket: WebSocket, user_uuid: str):
    await manager.connect(user_uuid=UUID(user_uuid), websocket=websocket)
    try:
        while True:
            event_json = await websocket.receive_json()
            event_type = event_json.get("event")
            if event_type not in client_events:
                await manager.send_event(
                    user_uuid=UUID(user_uuid),
                    event=ErrorEvent(
                        data=UnknownEventTypeErrorData(
                            details=f"Unknown event type: {event_type}")
                    )
                )
            if event_type == "ping":
                await manager.send_event(
                    user_uuid=UUID(user_uuid),
                    event=PongEvent()
                )


    except WebSocketDisconnect:
        manager.disconnect(user_uuid=UUID(user_uuid))


# user/ws.py
import logging
from fastapi.params import Depends
from redis.asyncio import Redis
from ..managers import manager
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..chat.events import client_events_dict as chat_events
from ..events import client_events_dict as base_events
from ..events import ErrorEvent, UnknownEventTypeErrorData, InvalidDataError
from ..events import  PongEvent, PingEvent
from ..db.db import get_db
from uuid import UUID
from ..dispatcher import dispatcher_event
from ..cache.cache_manager import get_redis
from ..handler_manager import handler_manager
from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)

router = APIRouter(tags=["user_ws"])

client_events = chat_events | base_events

@router.websocket("/ws/{user_uuid}")
async def websocket_endpoint(websocket: WebSocket, user_uuid: str, db: AsyncSession = Depends(get_db), r: Redis = Depends(get_redis)):
    data_flags = {}
    await manager.connect(user_uuid=UUID(user_uuid), websocket=websocket)
    print("Ws was connected now", manager.active_connections)
    try:
        while True:
            try:
                event_json = await websocket.receive_json()
            except WebSocketDisconnect:
                # клиент закрыл соединение
                print("WebSocketDisconnect for", user_uuid)
                manager.disconnect(user_uuid, websocket)
                break
            except RuntimeError as e:
                # то самое "WebSocket is not connected. Need to call 'accept' first."
                print("Unexpected WS runtime error", e)
                manager.disconnect(user_uuid, websocket)
                break
            print("WS JSON EVENT:", event_json)
            event_type = event_json.get("event")
            if not event_type:
                print("WS UNKNOWN EVENT TYPE:", event_type)
                err = ErrorEvent(
                    data=InvalidDataError(details="Missing 'event' field in message")
                )
                await manager.send_event(UUID(user_uuid), err)
                continue
            event_cls = client_events.get(event_type)
            if event_cls is None:
                print("WS UNKNOWN EVENT TYPE:", event_type)
                err = ErrorEvent(
                    data=UnknownEventTypeErrorData(details=f"Unknown event type: {event_type}")
                )
                await manager.send_event(UUID(user_uuid), err)
                continue
            event = event_cls(**event_json)
            logger.info(f"Received event: {event_type}")
            async for h in dispatcher_event(event_name=event_type,
                                            event_obj=event,
                                            db=db,
                                            redis=r,
                                            handler_manager=handler_manager,
                                            data_flags=data_flags):
                await manager.send_event(UUID(user_uuid),h)


    except WebSocketDisconnect as e:
        manager.disconnect(UUID(user_uuid), websocket)
        logger.info("WebSocketDisconnect: %s", e)
    except Exception as e:
        manager.disconnect(UUID(user_uuid), websocket)
        logger.exception("Unexpected WS error")
    finally:
        # На всякий случай ещё раз подчистим
        manager.disconnect(user_uuid, websocket)



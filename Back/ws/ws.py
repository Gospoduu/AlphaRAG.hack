# user/ws.py
import json
import logging

import anyio
from fastapi.params import Depends
from redis.asyncio import Redis
from Back.ws.managers import manager
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from Back.modules.chat.events import client_events_dict as chat_events
from Back.core.events_bus.events import client_events_dict as base_events, server_events_dict
from Back.core.events_bus.events import ErrorEvent, UnknownEventTypeErrorData, InvalidDataError
from Back.infra.db import get_db
from uuid import UUID
from Back.infra.redis import get_redis
from sqlalchemy.ext.asyncio import AsyncSession
from Back.infra.redis.streams import add_new_cmd, subscribe_to_emit_stream
from pydantic import ValidationError
import asyncio
logger = logging.getLogger(__name__)

router = APIRouter(tags=["user_ws"])

client_events = chat_events | base_events

async def ws_to_redis_loop(websocket:WebSocket, user_uuid: UUID, r: Redis):
    while True:
        error_flag = False
        err = ErrorEvent(
            data=InvalidDataError(details="If you see this message - is very strange")
        )
        try:
            event_json = await websocket.receive_json()
        except WebSocketDisconnect:
            # клиент закрыл соединение
            logger.info(f"WebSocketDisconnect for {user_uuid}")
            # manager.disconnect(user_uuid, websocket)
            break
        except Exception as e:
            # то самое "WebSocket is not connected. Need to call 'accept' first."
            logger.info(f"Unexpected WS runtime error {str(e)}")
            # manager.disconnect(user_uuid, websocket)
            break
        try:

            logger.info(f"WS JSON EVENT: {event_json}")
            event_type = event_json.get("event")
            if not event_type:
                logger.error(f"WS UNKNOWN EVENT TYPE: {event_type}")
                err = ErrorEvent(
                    data=InvalidDataError(details="Missing 'event' field in message")
                )
                await manager.send_event(user_uuid, err)
                continue
            event_cls = client_events.get(event_type)
            if event_cls is None:
                logger.error(f"WS UNKNOWN EVENT TYPE: {event_type}")
                err = ErrorEvent(
                    data=UnknownEventTypeErrorData(details=f"Unknown event type: {event_type}")
                )
                await manager.send_event(user_uuid, err)
                continue
            event = event_cls(**event_json)
            # Payload validation is intentionally relaxed for API iteration phase.
            # In production, catch ValidationError explicitly and return structured errors.
            logger.info(f"Received event: {event_type}")
            await add_new_cmd(user_uuid, event, r)
        except ValidationError as e:
            error_flag = True
            logger.error(f"WS JSON EVENT ERROR: {str(e)}")
            err = ErrorEvent(data=InvalidDataError(details=str(e)))
        except asyncio.CancelledError:
            raise
        except Exception as e:
            error_flag = True
            logger.error(f"Unexpected WS runtime error {str(e)}")
            err = ErrorEvent(data=InvalidDataError(details=str(e)))
        if error_flag:
            try:
                await manager.send_event(user_uuid, err)
            except Exception as e:
                logger.error(f"WS JSON EVENT ERROR: {str(e)}")
            continue


async def ws_from_redis_loop(user_uuid: UUID, r: Redis):
    async for event_name, event in  subscribe_to_emit_stream(user_uuid, r):
        try:
            payload = json.loads(event["payload"])
        except Exception as e:
            logger.error(f"Bad redis payload json: {e}")
            continue
        logger.info(f"Received event: {event_name}")
        event_cls = server_events_dict.get(event_name)
        if event_cls is None:
            logger.error(f"WS UNKNOWN EVENT TYPE: {event_name}")
            continue
        try:
            event_obj = event_cls(**payload)
            sent = await manager.send_event(user_uuid, event_obj)
            if not sent:
                logger.info(f"Stop ws_from_redis_loop: no active ws for {user_uuid}")
                break
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Unexpected WS runtime error {str(e)}")
            continue


async def run_ws_pipes(websocket:WebSocket, user_uuid: UUID, r: Redis):
    async with anyio.create_task_group() as tg:
        tg.start_soon(ws_from_redis_loop, user_uuid, r)
        await ws_to_redis_loop(websocket, user_uuid, r)


@router.websocket("/ws/{user_uuid}")
async def websocket_endpoint(websocket: WebSocket, user_uuid: str, db: AsyncSession = Depends(get_db), r: Redis = Depends(get_redis)):
    uid = UUID(user_uuid)
    await manager.connect(uid, websocket)

    try:
        await run_ws_pipes(websocket, uid, r)
    finally:
        manager.disconnect(uid, websocket)



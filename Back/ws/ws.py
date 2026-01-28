# Back/ws/ws.py
import json
import logging

import anyio
from typing import AsyncGenerator, Callable, Optional
from fastapi.params import Depends
from redis.asyncio import Redis
from Back.ws.managers import manager
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from Back.core.events_bus.dispatcher import dispatcher_manager

from Back.core.events_bus.events import ErrorEvent, ErrorCode
from Back.infra.db.db import get_db
from uuid import UUID
from Back.infra.redis.cache_manager import get_redis
from ..core.events_bus.event_manager import event_manager
from sqlalchemy.ext.asyncio import AsyncSession
from Back.infra.redis.streams import add_new_cmd, subscribe_to_emit_stream
from pydantic import ValidationError
import asyncio
logger = logging.getLogger(__name__)

router = APIRouter(tags=["user_ws"])


async def ws_to_redis_loop(websocket:WebSocket, user_uuid: UUID, conn_id: int, r: Redis):
    while True:
        if not await manager.is_current(user_uuid, conn_id):
            logger.info("ws_to_redis_loop: stale conn, stop user=%s conn_id=%s", user_uuid, conn_id)
            return

        error_flag = False
        err = ErrorEvent.create_error_event(code=ErrorCode.INVALID_DATA,details="If you see this message - is very strange")

        try:
            event_json = await websocket.receive_json()
        except WebSocketDisconnect:
            # клиент закрыл соединение
            logger.info(f"WebSocketDisconnect for {user_uuid}")
            # manager.disconnect(user_uuid, websocket)
            return
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
                err = ErrorEvent.create_error_event(code=ErrorCode.INVALID_DATA,details="Missing 'event' field in message")
                await manager.send_event(user_uuid, err)
                continue
            event_cls = event_manager.get(event_type)
            if event_cls is None:
                logger.error(f"WS UNKNOWN EVENT TYPE: {event_type}")
                err = ErrorEvent.create_error_event(ErrorCode.UNKNOWN_EVENT,details=f"Unknown event type: {event_type}")

                await manager.send_event(user_uuid, err)
                continue
            event = event_cls.from_dict(event_json)
            # Payload validation is intentionally relaxed for API iteration phase.
            # In production, catch ValidationError explicitly and return structured errors.
            logger.info(f"Received event: {event_type}")
            await add_new_cmd(user_uuid, event, r)

        except ValidationError as e:
            error_flag = True
            logger.error(f"WS JSON EVENT ERROR: {str(e)}")
            err = ErrorEvent.create_error_event(ErrorCode.UNKNOWN_EVENT,details=str(e))
        except asyncio.CancelledError:
            raise
        except Exception as e:
            error_flag = True
            logger.error(f"Unexpected WS runtime error {str(e)}")
            err = ErrorEvent.create_error_event(ErrorCode.UNKNOWN_EVENT,details=str(e))
        if error_flag:
            try:
                await manager.send_event(user_uuid, err)
            except Exception as e:
                logger.error(f"WS JSON EVENT ERROR: {str(e)}")
            continue


async def ws_from_redis_loop(user_uuid: UUID, conn_id: int,r: Redis):
    async for entry_id, entry_data in  subscribe_to_emit_stream(user_uuid, r):
        if not await manager.is_current(user_uuid, conn_id):
            logger.info("ws_from_redis_loop: stale conn, stop user=%s conn_id=%s", user_uuid, conn_id)
            return
        event_name = entry_data.get("event")
        payload = entry_data.get("payload")
        if not event_name:
            logger.warning(f"No event name in cmd stream entry_id={entry_id} entry=%s", entry_data)
            continue
        if not payload:
            logger.warning(f"No payload data in cmd stream entry_id={entry_id} entry=%s", entry_data)
            continue

        logger.info(f"Received event: {event_name}")
        event_cls = event_manager.get(event_name)
        if event_cls is None:
            logger.error(f"WS UNKNOWN EVENT TYPE: {event_name}")
            continue
        try:
            event_obj = event_cls.from_json(payload)
            sent = await manager.send_event(user_uuid, event_obj)
            print(f"event:{event_obj.event}, meta:{event_obj.meta}")
            if not sent:
                logger.info(f"Stop ws_from_redis_loop: no active ws for {user_uuid}")
                break
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Unexpected WS runtime error {str(e)}")
            continue


async def run_ws_pipes(websocket: WebSocket, user_uuid: UUID, conn_id: int, r: Redis, get_db):

    await dispatcher_manager.ensure_dispatcher(user_uuid, r, get_db)

    async with anyio.create_task_group() as tg:
        tg.start_soon(ws_from_redis_loop, user_uuid, conn_id, r)

        # Как только ws_to_redis_loop выходит (disconnect) — отменяем всё остальное
        await ws_to_redis_loop(websocket, user_uuid, conn_id, r)
        tg.cancel_scope.cancel()


@router.websocket("/ws/{user_uuid}")
async def websocket_endpoint(websocket: WebSocket, user_uuid: str, r: Redis = Depends(get_redis)):
    uid = UUID(user_uuid)
    conn_id = await manager.connect(uid, websocket)
    try:
        await run_ws_pipes(websocket, uid, conn_id, r, get_db)
    finally:
        await manager.disconnect(uid, websocket=websocket, conn_id=conn_id)





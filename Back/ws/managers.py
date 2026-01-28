import uuid
from dataclasses import dataclass
from fastapi import WebSocket
from typing import Dict
import asyncio
from uuid import UUID

from Back.core.events_bus.events import EventBase


@dataclass(frozen=True)
class Conn:
    ws: WebSocket
    id: int | None

class Manager:
    def __init__(self):
        self._active: Dict[str, Conn] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._manager_lock: asyncio.Lock = asyncio.Lock()
    def _get_key(self,user_uuid: UUID) ->str:
        return str(user_uuid)

    async def _get_user_lock(self, user_uuid: UUID) -> asyncio.Lock:
        key = self._get_key(user_uuid)
        async with self._manager_lock:
            lock = self._locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._locks[key] = lock
            return lock

    async def send_event(self,  user_uuid: UUID, event: EventBase,) -> bool:
        key = self._get_key(user_uuid)
        async with await self._get_user_lock(user_uuid):
            cur = self._active.get(key)
            ws = cur.ws if cur else None
            if ws is None:
                return False
        try:
            await ws.send_json(event.model_dump(mode="json"))
            return True
        except Exception:
            return False

    async def connect(self, user_uuid: UUID, websocket: WebSocket)->int:
        key = self._get_key(user_uuid)
        await websocket.accept()
        async with await self._get_user_lock(user_uuid):
            old = self._active.get(key)
            old_ws = old.ws if old else None
            new_id = (old.id + 1) if old else 1
            self._active[key] = Conn(websocket, new_id)
        if old_ws and old_ws is not websocket:
            try:
                await old_ws.close(code=4001)
            except Exception:
                pass

        return new_id

    async def is_current(self, user_uuid: UUID, conn_id: int) -> bool:
        key = self._get_key(user_uuid)
        async with await self._get_user_lock(user_uuid):
            cur = self._active.get(key)
        return cur is not None and cur.id == conn_id

    async def disconnect(self, user_uuid: UUID, websocket: WebSocket | None, conn_id: int| None)->int| None:
        key = self._get_key(user_uuid)
        async with await self._get_user_lock(user_uuid):
            curr = self._active.get(key)
            if curr is None:
                return
            if conn_id is not None and curr.id != conn_id:
                return
            if websocket is not None and curr.ws is not websocket:
                return
            if websocket is None and conn_id is None:
                return
            self._active.pop(key)
            ws_to_close = curr.ws
        try:
            await ws_to_close.close()
        except Exception:
            pass

    async def get(self, user_uuid: UUID) -> Conn | None:
        key = self._get_key(user_uuid)
        async with await self._get_user_lock(user_uuid):
            return self._active.get(key)


manager = Manager()







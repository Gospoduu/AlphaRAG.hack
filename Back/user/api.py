from fastapi import APIRouter, Depends, Request, HTTPException
from sse_starlette.sse import EventSourceResponse
from crud import create_user
from schemas import CreateUserBase
from ..db.db import get_db
from ..utils.api import endpoint_try
from sqlalchemy.ext.asyncio import AsyncSession
from ..cache.cache_manager import add_active_user, delete_active_user, get_redis
import asyncio


router = APIRouter(prefix="/user", tags=["user"])

@router.post("/")
@endpoint_try
async def create_user_endpoint(
        user: CreateUserBase,
        db : AsyncSession = Depends(get_db)):
    new_user = await create_user(db, user.role.value)
    return {"status": "ok", "uuid": str(new_user.uuid), "role": new_user.role}

@router.get("/sse/{user_uuid}")
async def get_user_sse(user_uuid: str, request: Request, r = Depends(get_redis)):
    q = asyncio.Queue()

    await add_active_user(user_uuid, r)
    async def event_generator():
        while True:
            try:
                if await request.is_disconnected():
                    break
                message = await q.get()
                yield {"event": message.event, "data": message.data}
            except Exception as e:
                break
            finally:
                await delete_active_user(user_uuid, r)
                q.task_done()
    return EventSourceResponse(event_generator())

@router.get("/sse/{operator_uuid}")
async def get_user_sse_response(operator_uuid: str, request: Request):

    async def event_generator():
        tickets = asyncio.Queue()
        while True:
            if await request.is_disconnected():
                break
            ticket = await tickets.get()

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from .crud import create_user
from .schemas import CreateUserBase
from ..db.db import get_db
from ..utils.api import endpoint_try
from sqlalchemy.ext.asyncio import AsyncSession
from ..cache.cache_manager import add_active_user, delete_active_user, get_redis
from uuid import UUID
import asyncio

router = APIRouter(prefix="/user", tags=["user"])

all_active_users = {}

@router.post("/")
@endpoint_try
async def create_user_endpoint(
        user: CreateUserBase,
        db : AsyncSession = Depends(get_db)):
    new_user = await create_user(db, user.role.value)
    await db.commit()
    return {"status": "ok", "uuid": str(new_user.uuid), "role": new_user.role}


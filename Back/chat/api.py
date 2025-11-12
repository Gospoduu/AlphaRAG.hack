
from fastapi import APIRouter, Depends, HTTPException
from ..db.db import get_db
from ..cache.cache_manager import add_generated_token, delete_generated_text
from ..utils.api import endpoint_try
from ..user.ws import manager, ConnectionManager
from crud import get_user_chats, create_chat, delete_chat, create_message, get_last_message_local_id, get_chat_batch
from models import Role
from uuid import UUID
from schemas import CreateChatBase, CreateMessageBase
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Callable, AsyncGenerator
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
import asyncio


router = APIRouter(prefix="/chat", tags=["chat"])



async def create_token_event(
        chat_id: int,
        user_uuid: UUID,
        llm_stream: AsyncGenerator[str],
        ws_manager: ConnectionManager,

        r: Redis):
    try:
        was_exception = False
        detail = "Generate end's successful"
        async for token in llm_stream:
            await add_generated_token(token, chat_id, r)
            await ws_manager.send_event (
                user_uuid,
                {"event":"new_token",
                "data": TokenData(
                chat_id=chat_id,
                token=token)
                }
            )
    except Exception as ex:
        was_exception = True
        detail = str(ex)
        await delete_generated_text(chat_id, r)
    finally:
        yield {
            "event":"end_generation",
            "data":EndGenerationData(
                chat_id=chat_id,
                detail=detail,
                status="error" if was_exception else "success",
                ).model_dump()
                }


@router.get("/{user_uuid}/chats")
@endpoint_try
async def get_chats_endpoint(
        user_uuid: str,
        db: AsyncSession = Depends(get_db)):
    chats = await get_user_chats(db, UUID(user_uuid))
    resp = [{"id": chat.id, "title": chat.title} for chat in chats]
    return {"status": "ok","chats": resp}

@router.post("/")
@endpoint_try
async def new_chat_endpoint(
        user: CreateChatBase,
        db: AsyncSession = Depends(get_db)):
    try:
        chat = await create_chat(db=db,user_uuid=user.user_uuid, title="Новый чат")
        await db.commit()
        return {"chat_id": chat.id,
                "title": chat.title,
                "user_uuid": str(chat.user_uuid),
                "status": "ok"}
    except Exception as ex:
        await db.rollback()
        raise ex

@router.delete("/{chat_id}")
@endpoint_try
async def delete_chat_endpoint(
        chat_id: int,
        db: AsyncSession = Depends(get_db)
):
    try:
        await delete_chat(db=db, chat_id=chat_id)
        await db.commit()
        return {"status": "ok"}
    except Exception as ex:
        await db.rollback()
        raise ex

@router.get("/{chat_id}/messages")
@endpoint_try
async def get_messages_endpoint(
        chat_id: int,
        start_message_idx: int = 0,
        batch_size: int = 40,
        db: AsyncSession = Depends(get_db)):
    chat = await get_chat_batch(db, chat_id, start_message_idx, batch_size)
    response = [
        {"id": message.id,
            "chat_id": message.chat_id,
            "local_id": message.local_id,
            "user_role": message.user_role,
            "user_uuid": message.user_uuid,
            "text": message.text,
            "created_at": message.created_at.isoformat(),
        } for message in chat]

    return {"status": "ok", "messages": response}
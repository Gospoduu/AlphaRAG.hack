
from fastapi import APIRouter, Depends, HTTPException
from ..db.db import get_db
from ..utils.api import endpoint_try
from .crud import get_user_chats, create_chat, delete_chat, create_message, get_last_message_local_id, get_chat_batch
from uuid import UUID
from .schemas import CreateChatBase, CreateMessageBase
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter(prefix="/chat", tags=["chat"])

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
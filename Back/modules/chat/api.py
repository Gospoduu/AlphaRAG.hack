# Back/modules/chat/api.py
from fastapi import APIRouter, Depends
from redis.asyncio import Redis

from Back.infra.db.db import get_db
from Back.infra.redis.cache_manager import get_redis
from Back.utils.api import endpoint_try
from .operator_offers import schedule_operator_offer, cancel_operator_offer
from .models import Chat, Message, Role
from .crud import get_user_chats, create_chat, delete_chat, get_chat_batch, update_reaction
from uuid import UUID
from .schemas import CreateChatBase, PatchReaction
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter(prefix="/chat", tags=["chat"])

@router.get("/{user_uuid}/chats")
@endpoint_try
async def get_chats_endpoint(
        user_uuid: str,
        db: AsyncSession = Depends(get_db)):
    chats = await get_user_chats(db, UUID(user_uuid))
    resp = [{"id": chat.id, "title": chat.title, "is_blocked": chat.is_blocked} for chat in chats]
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
            "reaction": message.reaction,
            "created_at": message.created_at.isoformat(),
        } for message in chat]

    return {"status": "ok", "messages": response}

@router.patch("/reaction")
@endpoint_try
async def reaction_endpoint(
    request: PatchReaction,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    try:
        message = await db.get(Message, request.message_id)
        chat = await db.get(Chat, request.chat_id)
        if (message is None or chat is None or message.chat_id != chat.id
                or chat.user_uuid != request.user_uuid or message.user_role != Role.BOT):
            raise ValueError("Bot message does not belong to this user's chat")
        await update_reaction(db=db, message_id=request.message_id, react=request.reaction.value)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    # A notification failure must not undo or report failure for a saved reaction.
    if request.reaction == -1:
        await schedule_operator_offer(request.chat_id, request.message_id, request.user_uuid, redis)
    else:
        await cancel_operator_offer(request.chat_id, redis, request.message_id)
    return {"status": "ok", "message_id": request.message_id, "reaction": request.reaction}

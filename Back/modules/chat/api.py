# Back/modules/chat/api.py
from fastapi import APIRouter, Depends
from redis.asyncio import Redis
import asyncio

from Back.infra.db.db import get_db
from Back.infra.redis.cache_manager import get_redis
from Back.utils.api import endpoint_try
from Back.infra.kafka.handlers.llm_handlers import end_generation_handler, new_token_handler
from .events import NewTokenEvent, NewTokenData, EndGenerationEvent, EndGenerationData
from .crud import get_user_chats, create_chat, delete_chat, get_chat_batch, update_reaction
from .cache import get_dislike_status, set_dislike_status, get_dislike_timer, set_dislike_timer, delete_dislike_status
from uuid import UUID
from .schemas import CreateChatBase, PatchReaction
from sqlalchemy.ext.asyncio import AsyncSession


IS_USER_NEED_SUPPORT_MSG = ('Прошу прощение, я увидел, что вам не понравился мой пред идущий ответ.'
                            ' Наша команда старается делать все, что бы наш сервис становился лучше и оказывал вам качественную поддержку.'
                            ' Хотите - мы передадим ваш запрос специалисту поддержки, он точно сможет оказать вам помощь('
                            ' А я пока буду учиться, что бы потом помочь вам.')


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
            "created_at": message.created_at.isoformat(),
        } for message in chat]

    return {"status": "ok", "messages": response}

async def _send_operator_offer_after_delay(
        redis: Redis,
        db: AsyncSession,
        chat_id: int,
        user_uuid: UUID,
):
    await asyncio.sleep(4)
    if await get_dislike_timer(chat_id, redis):
        for i, token in enumerate(IS_USER_NEED_SUPPORT_MSG):
            event = NewTokenEvent(
                data=NewTokenData(
                    token=token,
                    chat_id=chat_id,
                    user_uuid=user_uuid,
                    id=i,
                ),
            )
            await new_token_handler(event, redis)
            await asyncio.sleep(0.03)
        event = EndGenerationEvent(
            data=EndGenerationData(
                chat_id=chat_id,
                user_uuid=user_uuid,
                details="is_user_need_support",
                all_text=IS_USER_NEED_SUPPORT_MSG,
            )
        )
        await end_generation_handler(event, db, redis)



@router.patch("/reaction")
@endpoint_try
async def reaction_endpoint(
    request: PatchReaction,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    # -1: dislike, 0: None, 1: like
    await update_reaction(
        db=db,
        message_id=request.message_id,
        reaction=request.reaction,
    )

    if request.reaction == -1:
        if not await get_dislike_status(
                chat_id=request.chat_id,
                redis=redis,
        ):
            await set_dislike_status(
                chat_id=request.chat_id,
                redis=redis,
            )

            await set_dislike_timer(
                chat_id=request.chat_id,
                redis=redis,
            )

            asyncio.create_task(
                _send_operator_offer_after_delay(
                    chat_id=request.chat_id,
                    user_uuid=request.user_uuid,
                    db=db,
                    redis=redis,
                )
            )
    elif await get_dislike_status(
                chat_id=request.chat_id,
                redis=redis,
        ):
        await delete_dislike_status(
            chat_id=request.chat_id,
            redis=redis,
        )




    return {
        "status": "ok",
        "message_id": request.message_id,
        "reaction": request.reaction,
    }

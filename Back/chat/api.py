from time import sleep

from fastapi import APIRouter, Depends, HTTPException
from ..db.db import get_db
from ..cache.cache_manager import add_generated_token, delete_generated_text
from ..utils.api import endpoint_try
from crud import get_user_chats, create_chat
from uuid import UUID
from schemas import CreateChatBase
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Callable, AsyncGenerator
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from redis.asyncio import Redis
import asyncio

router = APIRouter(prefix="/chat", tags=["chat"])

async def llm_answer_plug(prompt: str):
    ans = f"Тут мог быть ответ ЛЛМ на этот промпт: `{prompt}`\n"
    for s in range(2,len(ans), 2):
        await asyncio.sleep(0.3)
        yield ans[s - 1] + ans[s]

async def create_token_event(chat_id: int, llm_stream: AsyncGenerator[str], r: Redis):
    try:
        was_exception = False
        detail = "Generate end's successful"
        async for token in llm_stream:
            await add_generated_token(token, chat_id, r)
            yield {"event":"new_token",
                   "data":{"chat_id":chat_id,
                           "token":token,
                           "is_final":False}}
    except Exception as ex:
        was_exception = True
        detail = str(ex)
        await delete_generated_text(chat_id, r)
    finally:
        yield {
            "event":"end_generation",
               "data":{"chat_id":chat_id,
                       "status": "error" if was_exception else "success",
                       "detail":detail,
                       "is_final":True
            }
        }

@router.get("/{user_uuid}")
@endpoint_try
async def get_chat(
        user_uuid: str,
        db: AsyncSession = Depends(get_db)):
    chats = await get_user_chats(db, UUID(user_uuid))
    await db.commit()
    resp = [{"id": chat.id, "title": chat.title} for chat in chats]
    return {"status": "ok","chats": resp}

@router.post("/")
@endpoint_try
async def new_chat(
        user: CreateChatBase,
        db: AsyncSession = Depends(get_db)):
    try:
        chat = await create_chat(db=db,user_uuid=user.user_uuid, title="Новый чат")
        await db.commit()
        return {"chat_id": chat.id,
                "title": chat.title,
                "user_uuid": str(chat.user_uuid),
                "status": "ok"}
    except Exception as e:
        await db.rollback()





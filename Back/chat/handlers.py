from collections.abc import Callable
from email import message
from typing import AsyncGenerator, Dict
from redis import RedisError
from redis.asyncio import Redis
from ..cache.cache_manager import add_generated_token, delete_generated_text, check_generated_text, change_chat_status, check_chat_status, GenerationStatus, redis_is_fine, update_generated_text, ensure_redis_connection
from Back.events import PingEvent
from events import NewMessageEvent
from events import NewTokenEvent, NewTokenData, EndGenerationEvent, MessageResponseEvent, MessageResponseData, GeneratedTextEvent, GeneratedTextData, EndGenerationData
import asyncio
from crud import create_message, get_last_message_local_id, get_is_generate, change_is_generate
from sqlalchemy.ext.asyncio import AsyncSession
from ..user.models import Role
from  uuid import UUID
from ..events import ErrorEvent, UnknownEventTypeErrorData, NotEventTypeErrorData, InvalidDataError, ConnectionErrorData
from cache import set_awaited_message, check_awaited_message
from dotenv import load_dotenv
from pathlib import Path
import logging
import os

logger = logging.getLogger(__name__)

env_path = Path(__file__).resolve().parent.parent / ".env"
print("🔍 Ищу .env по пути:", env_path)
load_dotenv(dotenv_path=env_path)

LLM_USER_UUID = os.getenv("LLM_USER_UUID")
print("📦 LLM_USER_UUID =", LLM_USER_UUID)

async def llm_answer_plug(prompt: str):
    ans = f"Тут мог быть ответ ЛЛМ на этот промпт: `{prompt}`\n"
    for s in range(2,len(ans), 2):
        await asyncio.sleep(0.3)
        yield ans[s - 1] + ans[s]



async def message_handler(
        message: NewMessageEvent,
        db: AsyncSession):
    try:
        last_message_local_id = await get_last_message_local_id(
            db,
            message.data.chat_id
        ) or 0
        new_message =  await create_message(
            db=db,
            user_uuid=message.data.user_uuid,
            chat_id=message.data.chat_id,
            local_id=last_message_local_id + 1,
            text=message.data.text,
            user_role=Role.USER.value,
        )
        await db.commit()
        return MessageResponseEvent(
            data=MessageResponseData(
                id=new_message.id,
                text=new_message.text,
                user_uuid=new_message.user_uuid,
                chat_id=new_message.chat_id,
                user_role=new_message.user_role,
                answered_to=new_message.answered_to,
                local_id=new_message.local_id,
            )
        )
    except ConnectionError:
        await db.rollback()
        return ErrorEvent(
            data=ConnectionErrorData(details="Database connection lost.")
        )
    except AttributeError as e:
        await db.rollback()
        return ErrorEvent(
            data=InvalidDataError(
                details=f"Invalid message data structure: {str(e)}. Got: {message.data.model_dump()}"
            )
        )
    except Exception as e:
        await db.rollback()
        return ErrorEvent(data=InvalidDataError(details=str(e)))

async def llm_answer_handler(
        new_message: NewMessageEvent,
        data_flags: Dict[str, bool],
        db: AsyncSession,
        r: Redis,
        llm_answer_generator: Callable = llm_answer_plug,
):
    prompt = new_message.data.text
    chat_id = new_message.data.chat_id

    details = "Generation end's correct."
    was_error = False
    redis_failed = False
    saved_text = ""
    redis_retry = True
    status = "ok"
    data_flags["is_saved_in_db"] = False
    data_flags["is_saved_in_redis"] = False
    is_saved_in_redis = False
    is_saved_in_db = False
    try:
        try:
            await change_chat_status(
                chat_id,
                GenerationStatus.IN_PROGRESS.value,
                r
            )
        except Exception as e:
            logger.warning(f"Redis unavailable when setting status: {e}")
            redis_failed = True

        try:
            await change_is_generate(db, chat_id, True)
            await db.commit()
        except Exception as e:
            logger.exception("Failed to set DB is_generate")
            details = f"DB failure when marking generation start: {e}"
            was_error = True
            status = "fatal"
            raise ConnectionError(details)
        try:
            if await check_chat_status(chat_id, r) == GenerationStatus.IN_PROGRESS.value:
                cached = await check_generated_text(chat_id, r)
                if cached:
                    saved_text = cached
                    yield GeneratedTextEvent(
                        data=GeneratedTextData(
                            chat_id=chat_id,
                            text=saved_text
                        )
                    )
        except Exception as e:
            logger.info("No cached text / Redis read failed: {e}")
            redis_failed = True

        async for token in llm_answer_generator(prompt):
            saved_text += token
            try:
                if redis_failed and redis_retry:
                    redis_retry = False
                    if await ensure_redis_connection(r):
                        redis_failed = False
                        await update_generated_text(saved_text, chat_id, r)
                        await change_chat_status(chat_id, GenerationStatus.IN_PROGRESS.value, r)
                    redis_retry = True
                else:
                    await add_generated_token(token, chat_id, r)
            except Exception as e:
                logger.exception(f"Failed to add generated token: {e}")
                redis_failed = True

            yield NewTokenEvent(
                data=NewTokenData(
                    token=token,
                    chat_id=chat_id)
            )
    except ConnectionError as e:
        logger.exception(f"DB failure when marking generation start: {e}")
        was_error = True
        status="error"
    except Exception as e:
        logger.exception(f"Generation error: {e}")
        status = "error"
        was_error = True
    finally:
        if not was_error:
            generated_message = await create_message(
                    db=db,
                    user_uuid=UUID(LLM_USER_UUID),
                    chat_id=new_message.data.chat_id,
                    local_id=await get_last_message_local_id(db, chat_id) or 1,
                    text=saved_text,
                    answered_to=None,
                    user_role=Role.BOT.value,
                )
            try:
                await db.commit()
                await change_is_generate(db, chat_id, False)
                data_flags["is_saved_in_db"] = True
                is_saved_in_db = True
            except Exception as e:
                logger.exception(f"Failed to create message: {e}")
            try:
                if is_saved_in_db:
                    await set_awaited_message(generated_message, r)
                    data_flags["is_saved_in_redis"] = True
                    is_saved_in_redis = True
                await change_chat_status(chat_id, GenerationStatus.FINISHED, r)
                await delete_generated_text(chat_id, r)

            except Exception as e:
                logger.exception(f"Failed to set awaited message: {e}")
                details = f"Cache failure when setting awaited message: {e}"

        if not (is_saved_in_redis or is_saved_in_db):
            status = "fatal"

        yield EndGenerationEvent(
            status=status,
            data=EndGenerationData(
                chat_id=chat_id,
                details=details,
            )
        )

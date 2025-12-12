from collections.abc import Callable
from typing import AsyncGenerator, Dict
from redis import RedisError
from redis.asyncio import Redis
from ..cache.cache_manager import redis_is_fine
from .cache import add_generated_token, delete_generated_text, check_generated_text, change_chat_status, check_chat_status, GenerationStatus, update_generated_text, ensure_redis_connection
from Back.events import PingEvent, EventBase, ErrorData
from ..handler_manager import handler_manager
from .events import NewMessageEvent, GenerationRestoreEvent, GenerationRestoreData
from .events import NewTokenEvent, NewTokenData, EndGenerationEvent, MessageResponseEvent, MessageResponseData, GeneratedTextEvent, GeneratedTextData, EndGenerationData, ReconnectionErrorEvent, ReconnectionErrorData
import asyncio
from .crud import create_message, get_last_message_local_id, get_is_generate, change_is_generate
from sqlalchemy.ext.asyncio import AsyncSession
from ..user.models import Role
from  uuid import UUID
from ..events import ErrorEvent, UnknownEventTypeErrorData, NotEventTypeErrorData, InvalidDataError, ConnectionErrorData
from .cache import set_awaited_message, check_awaited_message, subscribe_to_stream, add_token_to_stream, add_end_to_stream
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
    for s in range(1,len(ans), 2):
        await asyncio.sleep(0.1)
        yield ans[s - 1] + ans[s]



async def message_handler(
        message: NewMessageEvent,
        db: AsyncSession)-> EventBase:
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
        print(f"✅ Message saved: {new_message.id}, {new_message.text}")
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
        print(f"❌ Error in message_handler: {str(e)}")
        await db.rollback()
        return ErrorEvent(data=InvalidDataError(details=str(e)))

async def llm_answer_handler(
        new_message: NewMessageEvent,
        data_flags: Dict[str, bool],
        db: AsyncSession,
        redis: Redis,
        llm_answer_generator: Callable = llm_answer_plug,
)->AsyncGenerator[EventBase, None]:
    print(f"🔍 llm_answer_handler: {new_message.data.chat_id}, {new_message.data.text}")  # Логирование текста сообщения

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
    new_token_id = 0
    try:
        try:
            await change_chat_status(
                chat_id,
                GenerationStatus.IN_PROGRESS.value,
                redis
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
            if await check_chat_status(chat_id, redis) == GenerationStatus.IN_PROGRESS.value:
                cached = await check_generated_text(chat_id, redis)
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
        print("🔄 Generating text...")
        async for token in llm_answer_generator(prompt):
            print(f"Generated token: {token}")
            saved_text += token
            try:
                if redis_failed and redis_retry:
                    redis_retry = False
                    if await ensure_redis_connection(redis):
                        redis_failed = False
                        await update_generated_text(saved_text, chat_id, redis)
                        await change_chat_status(chat_id, GenerationStatus.IN_PROGRESS.value, redis)
                    redis_retry = True
                else:
                    await add_generated_token(token, chat_id, redis)
                    await add_token_to_stream(token, chat_id, redis)
            except Exception as e:
                logger.exception(f"Failed to add generated token: {e}")
                print(f"❌ Failed to add generated token: {e}")
                redis_failed = True

            yield NewTokenEvent(

                data=NewTokenData(
                    token=token,
                    chat_id=chat_id,
                    id=new_token_id,
                )
            )
            new_token_id += 1
    except ConnectionError as e:
        print(f"❌ Error during generation: {str(e)}")
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
                print(f"❌ Failed to create message: {e}")
                logger.exception(f"Failed to create message: {e}")
            try:
                if is_saved_in_db:
                    await set_awaited_message(generated_message, redis)
                    data_flags["is_saved_in_redis"] = True
                    is_saved_in_redis = True
                await add_end_to_stream("Generation end's correctly", chat_id, redis)
                await change_chat_status(chat_id, GenerationStatus.FINISHED, redis)
                await delete_generated_text(chat_id, redis)

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
async def restore_handler(event: GenerationRestoreEvent, redis: Redis)->AsyncGenerator[EventBase, None]:
    chat_id = event.data.chat_id
    last_token_id = event.data.last_token_id or 0
    status = await check_chat_status(chat_id, redis)
    if status != GenerationStatus.IN_PROGRESS.value:
        # генерация уже не идёт
        yield ReconnectionErrorEvent(
            data=ReconnectionErrorData(

                chat_id=chat_id,
                details="Generation is not in progress",
            )
        )
        return
    cached = await check_generated_text(chat_id, redis)
    if cached:
        print(f"Cached: {cached}")
        yield GeneratedTextEvent(
            data=GeneratedTextData(
                chat_id=chat_id,
                text=cached,
            )
        )
    return
    # last_id = event.data.last_id or "$"
    # async for event_name, payload in subscribe_to_stream(chat_id=chat_id,redis=redis, last_id=last_id):
    #     if event_name == "new_token":
    #         yield NewTokenEvent(
    #             data=NewTokenData(
    #                 chat_id=chat_id,
    #                 token=payload["token"],
    #                 id=last_token_id
    #             )
    #         )
    #         last_token_id += 1
    #     elif event_name == "end_generation":
    #         yield EndGenerationEvent(
    #             status="ok",
    #             data=EndGenerationData(
    #                 chat_id=chat_id,
    #                 details=payload.get("details", "From stream"),
    #             )
    #         )
    #         break

handler_manager.register("generation_restore",restore_handler)
handler_manager.register("new_message", message_handler, llm_answer_handler)


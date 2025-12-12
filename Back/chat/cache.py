import json

from datetime import datetime
from typing import AsyncGenerator
from uuid import UUID
from enum import Enum
import logging
from ..cache.cache_manager import ensure_redis_connection

logger = logging.getLogger(__name__)

class GenerationStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"
    ERROR = "error"
    AWAIT = "await"

def to_serializable(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value

from redis.asyncio import Redis
from .models import Message

async def __get_chat_awaited_message_key(chat_id: int) -> str:
    return f"{chat_id}:queue"

def __get_stream_key(chat_id: int):
    return f"chat:{chat_id}:stream"

def __get_chat_status_key(chat_id: int):
    key = f"chat:{chat_id}:status"
    return key
def __get_generator_key(chat_id: int):
    key = f"chat:{chat_id}:generated_text"
    return key


async def add_generated_token(token: str, chat_id: int, redis: Redis):
    key = __get_generator_key(chat_id)
    await redis.append(key, token)
    await redis.expire(key, 60*60*24)

async def check_generated_text(
    chat_id: int,
    redis: Redis,
):
    key = __get_generator_key(chat_id)
    return await redis.get(key)

async def update_generated_text(
    new_text: str,
    chat_id: int,
    redis: Redis,
):
    key = __get_generator_key(chat_id)
    await redis.set(key, new_text)

async def change_chat_status(chat_id: int,new_status: str, redis: Redis):
    key = __get_chat_status_key(chat_id)
    if new_status not in [s.value for s in GenerationStatus]:
        raise ValueError("Unknown new status")
    await redis.set(key, new_status)
async def check_chat_status(
    chat_id: int,
    redis: Redis,
):
    key = __get_chat_status_key(chat_id)
    return await redis.get(key)

async def delete_generated_text(chat_id: int, redis: Redis):
    key = f"chat:{chat_id}:generated_text"
    await redis.delete(key)


async def check_awaited_message(chat_id: int, redis:Redis) -> bool:
    return True if await redis.get(await __get_chat_awaited_message_key(chat_id)) else False


async def set_awaited_message(message: Message, redis: Redis):
    key = await __get_chat_awaited_message_key(message.chat_id)
    data = {
        "chat_id": message.chat_id,
        "id": message.id,
        "text": message.text,
        "answered_to": message.answered_to,
        "reaction": message.reaction,
        "created_at": message.created_at,
        "user_uuid": message.user_uuid,
        "local_id": message.local_id,
    }
    data = {k: to_serializable(v) for k, v in data.items()}
    await redis.set(key, json.dumps(data))
    return True

async def delete_awaited_message(chat_id: int, redis: Redis):
    key = await __get_chat_awaited_message_key(chat_id)
    await redis.delete(key)

async def add_token_to_stream(
        token: str,
        chat_id: int,
        redis: Redis
):
    stream_key = __get_stream_key(chat_id)
    await redis.xadd(
        stream_key,
        {"event": "new_token", "token": token},
    )
async def add_end_to_stream(
        details: str,
        chat_id: int,
        redis: Redis
):
    stream_key = __get_stream_key(chat_id)
    await redis.xadd(
        stream_key,
        {"event": "end_generation", "details": details},
    )

async def subscribe_to_stream(
        chat_id: int,
        redis: Redis,
        last_id: str = "$"
):
    stream_key = __get_stream_key(chat_id)

    while True:
        resp = await redis.xread(streams={stream_key: last_id},
                                 count=None,
                                 block=5_000)
        if not resp:
            continue
        _, entries = resp[0]
        for entry_id, entry_data in entries:
            event_name = entry_data["event"]
            yield event_name, entry_data
            last_id = entry_id

async def llm_generate_to_redis(
    chat_id: int,
    prompt: str,
    redis: Redis,
    db_factory,
    llm_answer_generator: AsyncGenerator,
    last_id: str = "$"
):


    details = "Generation end's correct."
    was_error = False
    redis_failed = False
    saved_text = ""
    redis_retry = True
    status = "ok"
    is_saved_in_redis = False
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
            if await check_chat_status(chat_id, redis) == GenerationStatus.IN_PROGRESS.value:
                cached = await check_generated_text(chat_id, redis)
                if cached:
                    saved_text = cached

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

            yield
            new_token_id += 1
    except ConnectionError as e:
        print(f"❌ Error during generation: {str(e)}")
        logger.exception(f"DB failure when marking generation start: {e}")
        was_error = True
        status = "error"
    except Exception as e:
        logger.exception(f"Generation error: {e}")
        status = "error"
        was_error = True
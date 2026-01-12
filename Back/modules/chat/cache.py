from Back.modules.chat.models import Message
from Back.utils.redis import to_serializable
from redis.asyncio import Redis
from enum import Enum
import json

class GenerationStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"
    ERROR = "error"
    AWAIT = "await"

def __get_chat_awaited_message_key(chat_id: int) -> str:
    return f"{chat_id}:queue"

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
    return True if await redis.get(__get_chat_awaited_message_key(chat_id)) else False

async def set_awaited_message(message: Message, redis: Redis):
    key = __get_chat_awaited_message_key(message.chat_id)
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
    await redis.expire(key, 60 * 60 * 24)
    return True

async def delete_awaited_message(chat_id: int, redis: Redis):
    key = __get_chat_awaited_message_key(chat_id)
    await redis.delete(key)
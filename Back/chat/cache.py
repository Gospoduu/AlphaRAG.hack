import json

from redis.asyncio import Redis
from models import Message

async def __get_chat_awaited_message_key(chat_id: int) -> str:
    return f"{chat_id}:queue"

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
    await redis.set(key, json.dumps(data))
    return True

async def delete_awaited_message(chat_id: int, redis: Redis):
    key = await __get_chat_awaited_message_key(chat_id)
    await redis.delete(key)

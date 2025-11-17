import json

from datetime import datetime
from uuid import UUID

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
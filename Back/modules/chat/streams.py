# Back/modules/chat/streams.py

from Back.core.events_bus.events import EventBase
from Back.infra.redis.safe import xadd_safe, xread_safe, xrange_safe
from redis.asyncio import Redis


# =================== chat_stream =====================
def _get_stream_key(chat_id: int):
    return f"chat:{chat_id}:stream"

async def add_new_chat_stream(
    chat_id: int,
    event: EventBase,
    redis: Redis,
)->str:
    key = _get_stream_key(chat_id)
    event_type = event.event
    return await xadd_safe(redis, key, {"event": event_type, "payload": event.to_json()})

async def subscribe_to_chat_stream(
        chat_id: int,
        redis: Redis,
        last_id: str = "$"
):
    stream_key = _get_stream_key(chat_id)

    while True:
        resp = await xread_safe(redis,streams={stream_key: last_id}, block=5_000)
        if not resp:
            continue
        _, entries = resp[0]
        for entry_id, entry_data in entries:
            yield entry_id, entry_data
            last_id = entry_id
async def read_chat_stream_since(chat_id: int, redis: Redis, last_id: str = "0-0", limit: int = 500):
    """
    Одноразово читает события строго ПОСЛЕ last_id.
    Возвращает список (entry_id, entry_data)
    """
    key = _get_stream_key(chat_id)
    start = f"({last_id}"  # exclusive
    return await xrange_safe(redis,key, min=start, max="+", count=limit)
# ==============================================================


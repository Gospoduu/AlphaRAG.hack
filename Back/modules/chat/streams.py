from Back.core.events_bus.events import EventBase
from redis.asyncio import Redis
from Back.utils.redis import to_serializable
import json


# =================== chat_stream =====================
def _get_stream_key(chat_id: int):
    return f"chat:{chat_id}:stream"

async def add_new_chat_stream(
    chat_id: int,
    event: EventBase,
    redis: Redis,
):
    key = _get_stream_key(chat_id)
    event_type = event.event
    await redis.xadd(key, {"event": event_type, "payload": json.dumps(event.model_dump(), default=to_serializable)})

async def subscribe_to_chat_stream(
        chat_id: int,
        redis: Redis,
        last_id: str = "$"
):
    stream_key = _get_stream_key(chat_id)

    while True:
        resp = await redis.xread(streams={stream_key: last_id},
                                 count=None,
                                 block=5_000)
        if not resp:
            continue
        _, entries = resp[0]
        for entry_id, entry_data in entries:
            event_name = entry_data["event"]
            yield entry_id, event_name, entry_data
            last_id = entry_id
# ==============================================================


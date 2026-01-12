import json

from uuid import UUID
import logging
from Back.core.events_bus.events import EventBase
from Back.core.events_bus.events import ErrorEvent, ErrorCode
from Back.utils.redis import stream_add_try, stream_subscribe_try
logger = logging.getLogger(__name__)
from redis.asyncio import Redis

# ================== emit_stream ====================
def _get_emit_key(user_uuid: UUID):
    return f"emit:{user_uuid}:stream"

async def add_new_emit(
    user_uuid: UUID,
    event: EventBase,
    redis: Redis,
):
    key = _get_emit_key(user_uuid)
    event_type = event.event
    @stream_add_try
    await redis.xadd(key, {"event": event_type,"payload":event.to_json()},maxlen=5000)

async def subscribe_to_emit_stream(
        user_uuid: UUID,
        redis: Redis,
        last_id: str = "$"
):
    stream_key = _get_emit_key(user_uuid)

    while True:
        resp = await redis.xread(streams={stream_key: last_id},
                                 block=5_000)
        if not resp:
            continue
        _, entries = resp[0]
        for entry_id, entry_data in entries:
            event_name = entry_data.get("event")
            if event_name is None:
                logger.warning(f"Event {event_name} not found in stream {stream_key}")
                error = ErrorEvent.create_error_event(ErrorCode.UNKNOWN_EVENT, "no event name")
                yield error.event, error.to_json()
                last_id = entry_id
                continue
            yield event_name, entry_data
            last_id = entry_id
# =================== cmd_stream =====================
def _get_cmd_key(user_uuid: UUID):
    return f"cmd:{user_uuid}:stream"

async def add_new_cmd(
    user_uuid: UUID,
    event: EventBase,
    redis: Redis,
):
    key = _get_cmd_key(user_uuid)
    event_type = event.event
    await redis.xadd(key, {"event": event_type, "payload": event.to_json()}, maxlen=5000)

async def subscribe_to_cmd_stream(
        user_uuid: UUID,
        redis: Redis,
        last_id: str = "$"
):
    stream_key = _get_cmd_key(user_uuid)

    while True:
        resp = await redis.xread(streams={stream_key: last_id},
                                 block=5_000)
        if not resp:
            continue
        _, entries = resp[0]
        for entry_id, entry_data in entries:
            event_name = entry_data.get("event")
            if event_name is None:
                logger.warning(f"Event {event_name} not found in stream {stream_key}")
                error = ErrorEvent.create_error_event(ErrorCode.UNKNOWN_EVENT, "no event name")
                yield error.event, error.to_json()
                last_id = entry_id
                continue
            yield event_name, entry_data
            last_id = entry_id


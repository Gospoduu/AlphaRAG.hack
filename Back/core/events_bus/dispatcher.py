from typing import Callable, AsyncGenerator, Awaitable, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from logging import getLogger
from Back.core.events_bus.handler_manager import handler_manager
from Back.infra.redis.streams import subscribe_to_cmd_stream
from uuid import UUID
from redis.asyncio import Redis
from Back.core.events_bus.events import EventBase
import asyncio
import json
from Back.ws.ws import client_events


logger = getLogger(__name__)

def parse_event(event: str, payload: str) -> EventBase:
    event_cls = client_events.get(event)

    if event_cls is None:
        raise KeyError(f"Event '{event}' not found in event manager")

    # Возвращаем созданный экземпляр события, инициализируем его через from_json
    return event_cls.from_json(payload)



def _log_task_result(task: asyncio.Task):
    try:
        task.result()
    except asyncio.CancelledError:
        logger.info("Handler task cancelled")
    except Exception:
        logger.exception("Handler task crashed")

async def _run_handler_with_db(
    handler: Callable[..., Awaitable[Any]],
    entry_data: Dict[str, Any],
    redis: Redis,
    get_db: Callable[[], AsyncGenerator[AsyncSession, None]]
) -> None:
    agen = get_db()
    try:
        db = await agen.__anext__()
        await handler(**entry_data,redis=redis, db=db)
    except StopAsyncIteration:
            raise RuntimeError("get_db() did not yield a database session")
    finally:
        await agen.aclose()

async def dispatcher_event(user_uuid: UUID, redis: Redis, get_db: Callable[[], AsyncGenerator[AsyncSession, None]]):
    async for event_name, entry_data in subscribe_to_cmd_stream(user_uuid, redis):
        handlers = handler_manager.get_handlers(event_name)
        if not handlers:
            logger.warning("No handlers for event '%s'", event_name)
            continue

        for handler in handlers:
            logger.info("Dispatching event='%s' handler=%s", event_name, handler)
            task = asyncio.create_task(_run_handler_with_db(handler, entry_data, redis, get_db))
            task.add_done_callback(_log_task_result)





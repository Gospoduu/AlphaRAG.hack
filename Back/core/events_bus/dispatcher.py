# core/event_bus/dispatcher

from typing import Callable, AsyncGenerator, Awaitable, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from logging import getLogger
from Back.core.events_bus.handler_manager import handler_manager
from Back.infra.redis.streams import subscribe_to_cmd_stream
from uuid import UUID
from redis.asyncio import Redis
from Back.core.events_bus.events import EventBase
import asyncio
from .event_manager import event_manager
from Back.core.events_bus.handler_policy import get_policy
from Back.core.exc import RetryableError
import json

logger = getLogger(__name__)


def _log_task_result(task: asyncio.Task):
    try:
        task.result()
    except asyncio.CancelledError:
        logger.info("Handler task cancelled")
    except Exception:
        logger.exception("Handler task crashed")

async def run_handler(
    handler: Callable[..., Awaitable[Any]],
    event: EventBase,
    redis: Redis,
    get_db: Callable[[], AsyncGenerator[AsyncSession, None]]
) -> None:

    policy = get_policy(handler)
    attempts = policy.try_cnt if policy.retry else 1

    for attempt in range(attempts):
        agen = None
        db = None
        try:
            agen = get_db()
            try:
                db = await agen.__anext__()
            except StopAsyncIteration:
                raise RuntimeError("get_db() did not yield a database session")
            result = await handler(event, redis=redis, db=db)
            logger.info(f"Handler {handler.__qualname__} ends successfully")
            return result

        except asyncio.CancelledError:
            logger.warning(f"Handler `{handler.__qualname__}` task cancelled ")
            raise
        except RetryableError:
            if db is not None:
                try:
                    await db.rollback()
                except Exception:
                    logger.exception(f"Rollback db for retry handler `{handler.__qualname__}` failed")
            if attempt == attempts - 1:
                logger.exception(f"Handler `{handler.__qualname__}` task crashed (no retries left)")
                raise
            logger.warning(f"Handler `{handler.__qualname__}` task crashed, retrying, attempt: {attempt + 1}",
                           exc_info=True)

            await asyncio.sleep(policy.delay)

        except Exception:
            if db is not None:
                try:
                    await db.rollback()
                except Exception:
                    logger.exception("Rollback failed for handler %s", handler.__qualname__)
            logger.exception(f"Handler `{handler.__qualname__}` task crashed")
            raise

        finally:
            if agen is not None:
                try:
                    await agen.aclose()
                except Exception:
                    logger.exception("Failed to close db generator")


async def dispatcher_event(user_uuid: UUID, redis: Redis, get_db: Callable[[], AsyncGenerator[AsyncSession, None]]):
    async for entry_id, entry_data in subscribe_to_cmd_stream(user_uuid, redis):
        event_name = entry_data.get("event")
        if not event_name:
            logger.warning("No event name in cmd stream entry_id=%s entry=%s", entry_id, entry_data)
            continue
        payload = entry_data.get("payload")
        if payload is None:
            logger.warning("No payload in cmd stream entry_id=%s event=%s", entry_id, event_name)
            continue
        handlers = handler_manager.get(event_name)
        if not handlers:
            logger.warning("No handlers for event '%s'", event_name)
            continue
        event_cls = event_manager.get(event_name)
        if not event_cls:
            logger.warning("No event for event '%s'", event_name)
            continue
        try:
            parsed_event = event_cls.from_json(payload)
            parsed_event.meta["stream_id"] = entry_id
        except Exception as e:
            logger.exception("Failed to parse event payload: %s, error: %s", event_name, str(e))
            continue
        for handler in handlers:
            logger.info("Dispatching event='%s' handler=%s", event_name, handler)
            task = asyncio.create_task(run_handler(handler, parsed_event, redis, get_db), name=f"{event_name}:{handler.__name__}")
            task.add_done_callback(_log_task_result)


class DispatcherManager:
    def __init__(self):
        self._dispatcher_tasks: Dict[UUID, asyncio.Task] = {}
        self._locks: Dict[UUID, asyncio.Lock] = {}

    async def ensure_dispatcher(self, user_uuid: UUID, redis: Redis, get_db):
        lock = self._locks.setdefault(user_uuid, asyncio.Lock())
        async with lock:
            task = self._dispatcher_tasks.get(user_uuid)
            if task and not task.done():
                return task

            task = asyncio.create_task(
                dispatcher_event(user_uuid, redis, get_db),
                name=f"dispatcher:{user_uuid}",
            )

            def _cleanup(t: asyncio.Task):
                cur = self._dispatcher_tasks.get(user_uuid)
                if cur is t:
                    self._dispatcher_tasks.pop(user_uuid, None)
                _log_task_result(t)

            task.add_done_callback(_cleanup)
            self._dispatcher_tasks[user_uuid] = task
            return task

    async def stop_dispatcher(self, user_uuid: UUID):
        task = self._dispatcher_tasks.pop(user_uuid, None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
dispatcher_manager = DispatcherManager()
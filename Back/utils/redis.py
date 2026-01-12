from uuid import UUID
from datetime import datetime
from logging import getLogger
import asyncio

logger = getLogger(__name__)


def to_serializable(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value

def stream_add_try(add_func):
    async def wrapper(*args, **kwargs):
        try:
            return await add_func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Fatal. Redis xadd failed ({add_func.__name__}): {e}")
            raise
    return wrapper

def stream_subscribe_try(subscribe_func):
    async def wrapper(*args, **kwargs):
        try:
            return await subscribe_func(*args, **kwargs)
        except asyncio.CancelledError as e:
            logger.error(f"Fatal. Redis subscribe failed{subscribe_func.__name__} cancelled: {e}")
            raise
        except Exception as e:
            logger.exception(f"Redis subscribe failed{subscribe_func.__name__} error: {e}")
            await asyncio.sleep(0.5)
    return wrapper

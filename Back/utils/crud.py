# Back/utils/crud.py

from Back.infra.db.exc import _DB_RETRYABLE
from Back.core.exc import RetryableError
from logging import getLogger
from functools import wraps
import asyncio

logger = getLogger(__name__)

def safe_crud(crud_func):
    @wraps(crud_func)
    async def wrapper(*args, **kwargs):
        try:
            result = await crud_func(*args, **kwargs)
        except asyncio.CancelledError:
            logger.warning("CRUD cancelled: %s", crud_func.__qualname__)
            raise
        except _DB_RETRYABLE as e:
            logger.exception("Retryable DB error in CRUD", extra={"crud": crud_func.__qualname__})
            raise RetryableError(f"failed crud func `{crud_func.__qualname__}`, {e!r}") from e
        else:
            return result
    return wrapper
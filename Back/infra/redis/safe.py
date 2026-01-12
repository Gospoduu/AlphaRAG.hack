from __future__ import annotations

import asyncio
from logging import getLogger
from typing import Any, Mapping

from redis.asyncio import Redis

logger = getLogger(__name__)


async def xadd_safe(
    redis: Redis,
    key: str,
    data: Mapping[str, Any],
    *,
    maxlen: int | None = None,
):
    try:
        return await redis.xadd(key, dict(data), maxlen=maxlen)
    except asyncio.CancelledError:
        logger.warning("xadd_safe cancelled. key: %s", key)
        raise
    except Exception as e:
        logger.exception("Redis xadd failed", extra={"key": key, "fields": list(data.keys()), "error": str(e)})
        raise


async def xread_safe(
    redis: Redis,
    streams: Mapping[str, str],
    *,
    block_ms: int = 5_000,
    count: int | None = None,
    retry_sleep_s: float = 0.5,
    retry_sleep_max_s: float = 5.0,
):
    sleep_s = retry_sleep_s

    while True:
        try:
            return await redis.xread(streams=dict(streams), block=block_ms, count=count)
        except asyncio.CancelledError:
            logger.warning("xread_safe cancelled. streams: %s", streams)
            raise
        except Exception as e:
            logger.exception(
                "Redis xread failed",
                extra={"streams": list(streams.keys()), "block_ms": block_ms, "count": count, "error": str(e)},
            )
            await asyncio.sleep(sleep_s)
            sleep_s = min(sleep_s * 2, retry_sleep_max_s)

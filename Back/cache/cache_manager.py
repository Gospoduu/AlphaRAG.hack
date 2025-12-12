from enum import Enum
from .start_redis import redis_client
from redis.asyncio import Redis
from typing import AsyncGenerator
from ..events import EventBase, EventDataBase
import asyncio

async def get_redis()->AsyncGenerator[Redis]:
    yield redis_client

async def add_active_user(user_uuid: str, redis: Redis):
    await redis.sadd("active_users",user_uuid)

async def delete_active_user(user_uuid: str, redis: Redis):
    await redis.srem("active_users", user_uuid)

async def add_active_operator(operator_uuid: str, redis: Redis):
    await redis.sadd("active_operators", operator_uuid)

async def delete_active_operator(operator_uuid: str, redis: Redis):
    await redis.srem("active_operators", operator_uuid)

async def redis_is_fine(redis: Redis):
    is_fine = False
    try:
        await redis.ping()
        is_fine = True
    except Exception as e:
        pass
    return is_fine

async def ensure_redis_connection(r: Redis, retries: int = 3, delay: float = 2.0):
    for i in range(retries):
        if await redis_is_fine(r):
            return True
        await asyncio.sleep(delay)
    return False



import redis
from enum import Enum
from start_redis import redis_client
from redis.asyncio import Redis
from typing import AsyncGenerator
from ..events import EventBase, EventDataBase
import asyncio

class GenerationStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"
    ERROR = "error"
    AWAIT = "await"

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

def __get_chat_status_key(chat_id: int):
    key = f"chat:{chat_id}:status"
    return key
def __get_generator_key(chat_id: int):
    key = f"chat:{chat_id}:generated_text"
    return key

async def add_generated_token(token: str, chat_id: int, redis: Redis):
    key = __get_generator_key(chat_id)
    await redis.append(key, token)
    await redis.expire(key, 60*60*24)

async def check_generated_text(
    chat_id: int,
    redis: Redis,
):
    key = __get_generator_key(chat_id)
    return await redis.get(key)

async def update_generated_text(
    new_text: str,
    chat_id: int,
    redis: Redis,
):
    key = __get_generator_key(chat_id)
    await redis.set(key, new_text)

async def change_chat_status(chat_id: int,new_status: str, redis: Redis):
    key = __get_chat_status_key(chat_id)
    if new_status not in GenerationStatus:
        raise ValueError("Unknown new status")
    await redis.set(key, new_status)
async def check_chat_status(
    chat_id: int,
    redis: Redis,
):
    key = __get_chat_status_key(chat_id)
    return await redis.get(key)

async def delete_generated_text(chat_id: int, redis: Redis):
    key = f"chat:{chat_id}:generated_text"
    await redis.delete(key)

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
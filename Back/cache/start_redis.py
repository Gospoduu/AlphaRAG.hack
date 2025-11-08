import uuid

import redis.asyncio as redis
from dotenv import load_dotenv
import os
from pathlib import Path
from typing import AsyncGenerator

env_path = Path(__file__).resolve().parent.parent / ".env"
print("🔍 Ищу .env по пути:", env_path)
load_dotenv(dotenv_path=env_path)

print("📦 REDIS_URL =", os.getenv("REDIS_URL"))

redis_client = redis.from_url(os.getenv("REDIS_URL"),
                              decode_responses=True,
                              max_connections=40)

# Back/infra/db/db.py

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine,AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv
import os
from pathlib import Path

env_path = None
for p in Path(__file__).resolve().parents:
    candidate = p / ".env"
    if candidate.exists():
        env_path = candidate
        break

print("🔍 Ищу .env по пути:", env_path)
load_dotenv(dotenv_path=env_path)

print("📦 DATABASE_URL =", os.getenv("DATABASE_URL"))

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncGenerator:
    async with AsyncSessionLocal() as session:
        yield session
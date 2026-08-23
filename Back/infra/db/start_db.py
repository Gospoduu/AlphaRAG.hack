# Back/infra/db/start_db.py

import os
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError


from pathlib import Path
import sys

# ФИКС для Docker: добавляем корень проекта (/app) в sys.pat


# Теперь используем абсолютные импорты для Docker

# Сначала пробуем абсолютные импорты (для Docker)
from Back.infra.db.db import engine, AsyncSessionLocal, Base
from Back.modules.user.models import *
from Back.modules.chat.models import *

# Загружаем .env
env_path = Path(__file__).resolve().parents[3] / ".env"
print("🔍 Ищу .env по пути:", env_path)
load_dotenv(dotenv_path=env_path)


LLM_USER_UUID = os.getenv("LLM_USER_UUID")


async def init_db():
    print("⚠️ Полная пересборка БД: DROP ALL → CREATE ALL")

    # 1. Удаляем все таблицы (drop_all автоматически учитывает foreign key порядок)
    async with engine.begin() as conn:
        print("🗑  Удаляю все таблицы...")
        await conn.run_sync(Base.metadata.drop_all)

    # 2. Создаем все таблицы заново
    async with engine.begin() as conn:
        print("📦 Создаю таблицы...")
        await conn.run_sync(Base.metadata.create_all)

    print("✅ Таблицы пересозданы")

    # 3. Добавляем LLM-пользователя
    if not LLM_USER_UUID:
        raise RuntimeError("⚠️ Переменная окружения LLM_USER_UUID не задана в .env")

    llm_uuid = UUID(LLM_USER_UUID)

    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(User).where(User.uuid == llm_uuid)
            )
            llm_user = result.scalar_one_or_none()

            if llm_user is None:
                llm_user = User(
                    uuid=llm_uuid,
                    role=Role.BOT.value,
                    created_at=datetime.now(),
                )
                session.add(llm_user)
                await session.commit()
                print(f"🤖 Создан LLM-пользователь: {llm_uuid}")
            else:
                print(f"🤖 LLM-пользователь уже существует: {llm_user.uuid}")

        except SQLAlchemyError as e:
            await session.rollback()
            print(f"❌ Ошибка при создании LLM-пользователя: {e}")
            raise

    print("🎉 Инициализация БД завершена.")
# AlphaRAG.hack/run_local.py
import asyncio
import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "Back" / "static"
DB_PATH = BASE_DIR / "local_chat.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (uuid TEXT PRIMARY KEY, role TEXT, created_at TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY AUTOINCREMENT, user_uuid TEXT, title TEXT, created_at TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, local_id INTEGER, user_uuid TEXT, user_role TEXT, text TEXT, created_at TEXT)")
    conn.commit()
    conn.close()

init_db()

app = FastAPI(title="Tender Hack Local Support Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def read_root():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"status": "ok", "message": "Index file not found in static dir"}

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.get("/api/redis/ping")
async def redis_ping():
    return {"redis": "ok"}

@app.get("/api/db/ping")
async def db_ping():
    return {"db": "ok"}

class UserCreate(BaseModel):
    role: str = "supplier"

class ChatCreate(BaseModel):
    user_uuid: str

@app.post("/api/user/")
async def create_user_endpoint(user: UserCreate):
    new_uuid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO users (uuid, role, created_at) VALUES (?, ?, ?)", (new_uuid, user.role, now))
    conn.commit()
    conn.close()
    return {"status": "ok", "uuid": new_uuid, "role": user.role}

@app.get("/api/chat/{user_uuid}/chats")
async def get_user_chats(user_uuid: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, title FROM chats WHERE user_uuid = ? ORDER BY id DESC", (user_uuid,))
    rows = cur.fetchall()
    conn.close()
    chats = [{"id": r[0], "title": r[1]} for r in rows]
    return {"status": "ok", "chats": chats}

@app.post("/api/chat/")
async def create_chat_endpoint(payload: ChatCreate):
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO chats (user_uuid, title, created_at) VALUES (?, ?, ?)", (payload.user_uuid, "Новый диалог", now))
    chat_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {"status": "ok", "chat_id": chat_id, "title": "Новый диалог", "user_uuid": payload.user_uuid}

@app.delete("/api/chat/{chat_id}")
async def delete_chat_endpoint(chat_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
    cur.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.get("/api/chat/{chat_id}/messages")
async def get_messages(chat_id: int, start_message_idx: int = 0, batch_size: int = 50):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, chat_id, local_id, user_uuid, user_role, text, created_at FROM messages WHERE chat_id = ? ORDER BY id DESC LIMIT ? OFFSET ?", (chat_id, batch_size, start_message_idx))
    rows = cur.fetchall()
    conn.close()
    messages = [{"id": r[0], "chat_id": r[1], "local_id": r[2], "user_uuid": r[3], "user_role": r[4], "text": r[5], "created_at": r[6]} for r in rows]
    return {"status": "ok", "messages": messages}

def generate_tender_response(user_text: str) -> str:
    t = user_text.lower()
    if any(k in t for k in ["эцп", "крипто", "сертификат", "подпис"]):
        return (
            "### 🔑 Инструкция по настройке ЭЦП и плагина КриптоПро\n\n"
            "Для корректного подписания документов на **Портале Поставщиков**:\n\n"
            "1. **Проверьте плагин:** убедитесь, что установлен `КриптоПро ЭЦП Browser plug-in` (версия не ниже 2.0.145).\n"
            "2. **Сертификаты:** установите корневой сертификат Минцифры РФ (ГУЦ) в доверенные корневые центры.\n"
            "3. **Доверенные узлы:** добавьте адреса `*.zakupki.mos.ru` и `*.mos.ru` в доверенные узлы плагина.\n\n"
            "> 💡 **Совет:** При ошибке подписи очистите кэш браузера (`Ctrl+F5`) или проверьте срок действия лицензии КриптоПро."
        )
    if any(k in t for k in ["котировочн", "сесси", "ставк", "оферт"]):
        return (
            "### 📊 Регламент котировочных сессий (Портал Поставщиков)\n\n"
            "- **Длительность:** стандартная сессия длится **24 часа** (экспресс — от 3 до 6 часов).\n"
            "- **Шаг снижения:** от **0.5% до 5%** от текущей минимальной стоимости оферты.\n"
            "- **Автопродление:** ставка за 5 минут до финала продлевает сессию ещё на 5 минут (до 3 раз).\n\n"
            "Победитель определяется по наименьшей цене на момент окончания сессии и обязан подписать проект контракта в течение **1 рабочего дня**."
        )
    if any(k in t for k in ["регистрац", "войти", "аккаунт", "профиль"]):
        return (
            "### 🏢 Регистрация поставщика через ЕСИА (Госуслуги)\n\n"
            "1. Войдите с подтвержденной учетной записью руководителя на Госуслугах.\n"
            "2. В Личном кабинете заполните карточку компании (ИНН, ОГРН, банковские реквизиты).\n"
            "3. Подпишите электронное заявление вашей УКЭП.\n\n"
            "⏱️ Автоматическая верификация через СМЭВ занимает **от 15 минут до 2 часов**."
        )
    if any(k in t for k in ["контракт", "срок", "оплат"]):
        return (
            "### 📑 Нормативные сроки по контрактам (44-ФЗ / 223-ФЗ)\n\n"
            "- **Формирование контракта заказчиком:** до 2 рабочих дней.\n"
            "- **Подписание победителем:** 1 рабочий день с момента публикации проекта.\n"
            "- **Оплата поставленного товара:** до 7 рабочих дней с даты подписания акта приемки (по нормам 44-ФЗ)."
        )
    return (
        f"### 🤖 Консультация интеллектуального ассистента\n\n"
        f"По вашему обращению: *«{user_text}»* сформирован ответ по регламенту **Портала Поставщиков Москвы (zakupki.mos.ru)**:\n\n"
        "1. Запрос успешно зарегистрирован в системе интеллектуальной поддержки.\n"
        "2. Регламентные материалы и шаблоны документов доступны в Личном кабинете участника закупок.\n"
        "3. Если ситуация требует индивидуального технического решения или разбора логов ЕИС, нажмите **«Вызвать оператора»** для подключения L2-инженера."
    )

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, user_uuid: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_uuid] = websocket

    def disconnect(self, user_uuid: str):
        if user_uuid in self.active_connections:
            del self.active_connections[user_uuid]

manager = ConnectionManager()

@app.websocket("/api/ws/{user_uuid}")
async def websocket_endpoint(websocket: WebSocket, user_uuid: str):
    await manager.connect(user_uuid, websocket)
    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                msg = json.loads(raw_data)
            except Exception:
                continue
            event = msg.get("event", "")
            if event in ("PING", "ping"):
                await websocket.send_json({"event": "pong", "status": "OK"})
                continue
            if event in ("NEW_MESSAGE", "new_message"):
                data = msg.get("data", {})
                chat_id = int(data.get("chat_id", 0))
                user_text = data.get("text", "")
                role = data.get("role", "supplier")
                now = datetime.utcnow().isoformat()

                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute("INSERT INTO messages (chat_id, local_id, user_uuid, user_role, text, created_at) VALUES (?, 1, ?, ?, ?, ?)", (chat_id, user_uuid, role, user_text, now))
                conn.commit()

                cur.execute("SELECT title FROM chats WHERE id = ?", (chat_id,))
                title_row = cur.fetchone()
                if title_row and title_row[0] in ("Новый диалог", "Новый чат"):
                    short_title = (user_text[:35] + "...") if len(user_text) > 35 else user_text
                    cur.execute("UPDATE chats SET title = ? WHERE id = ?", (short_title, chat_id))
                    conn.commit()
                conn.close()

                full_bot_response = generate_tender_response(user_text)
                words = full_bot_response.split(" ")
                accumulated = ""
                for i, word in enumerate(words):
                    token = word + (" " if i < len(words) - 1 else "")
                    accumulated += token
                    await websocket.send_json({"event": "new_token", "status": "OK", "data": {"chat_id": chat_id, "token": token}})
                    await asyncio.sleep(0.02)

                await websocket.send_json({"event": "end_generation", "status": "OK", "data": {"chat_id": chat_id, "text": accumulated}})

                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute("INSERT INTO messages (chat_id, local_id, user_uuid, user_role, text, created_at) VALUES (?, 2, 'bot-system', 'bot', ?, ?)", (chat_id, accumulated, datetime.utcnow().isoformat()))
                conn.commit()
                conn.close()
    except WebSocketDisconnect:
        manager.disconnect(user_uuid)
    except Exception:
        manager.disconnect(user_uuid)

if __name__ == "__main__":
    print("=" * 60)
    print(">>> Tender Hack Local Support Server Starting...")
    print(">>> Open in browser: http://localhost:8000")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

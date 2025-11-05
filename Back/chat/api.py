from fastapi import APIRouter, Depends, HTTPException

router = APIRouter()

router.get("/chats/user_uuid")
def get_chats():
    chats = [
        {"chat_id" :1, "title" : "Заглушка чата 1"},
        {"chat_id" :2, "title" : "Заглушка чата 2"},
        {"chat_id" : 3, "title" : "Заглушка чата 3"}
    ]
    return chats

router.get("/chat/{chat_id}")
def get_chat(chat_id):
    chat = [{"user": "User1", "text":"mes1"},
            {"user": "User2", "text":"mes2"},
            {"user": "User1", "text":"mes3"}]

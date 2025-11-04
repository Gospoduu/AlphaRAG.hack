# AlphaRAG API

Бэкенд-сервис на FastAPI с поддержкой RAG и многопоточной работы чатов.

---

## Запуск в Docker

Сборка и запуск контейнера:

```bash
docker build -t alpharag-api -f Back/Dockerfile .
docker run -p 8000:8000 alpharag-api
```
После запуска приложение будет доступно по адресу:

http://localhost:8000/health
 — проверка состояния

http://localhost:8000/docs
 — Swagger UI (документация API)
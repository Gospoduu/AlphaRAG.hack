# AlphaRAG /metrics

`GET http://localhost:8000/metrics` — Prometheus text format.

HTTP RPS:

```promql
sum(rate(alpharag_http_requests_total[$__rate_interval]))
```

По маршруту и статусу:

```promql
sum by (method, route, status) (rate(alpharag_http_requests_total[$__rate_interval]))
```

Считаются завершённые HTTP-запросы, включая ошибки, 404 и static. `/metrics`, `/api/health`, `/api/redis/ping`, `/api/db/ping` исключены. Route — шаблон (`/api/chat/{chat_id}/messages`), неизвестные пути объединены в `unmatched`; UUID и сырые URL не создают отдельные серии.

Чат идёт по WebSocket, поэтому HTTP RPS не равен потоку вопросов. Отдельная метрика считает валидированные команды, успешно записанные в Redis (не завершённые ответы RAG):

```promql
sum(rate(alpharag_ws_commands_total{event="NEW_MESSAGE"}[$__rate_interval]))
```

Все команды кроме PING:

```promql
sum by (event) (rate(alpharag_ws_commands_total[$__rate_interval]))
```

Счётчики процесса сбрасываются при рестарте/reload; Prometheus `rate` обрабатывает сброс. Текущий запуск — один Uvicorn worker. При масштабировании используйте отдельный scrape target на каждый процесс/контейнер или настройте multiprocess mode prometheus-client. Несколько workers за одним общим `/metrics` без этой настройки дадут неверные значения.

Проверка HTTP middleware: `docker compose run --rm --no-deps backend python -m unittest discover -s tests -p test_http_metrics.py -v`.

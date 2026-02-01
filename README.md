# хакатонщики 2.0

**Цель:** Создать серверную часть  для чат-бота.

**Деплой:**  

**Видео:** 

**Инструкция:** 

## Стек

- **Backend:** Python, FastAPI
- **Frontend:** JS
- **Контейнеризация:** Docker
- **Развёртывание:**
- **DB:** PostgreSQL
- **Vector DB:** Qdrant
- **ML:** Python, transformers, torch, pandas
- **SLM:** 

## Структура проекта

- **`backend/`**

```
├── main.py                      # 
├── config.py                    #
├── Dockerfile                   #
├── chat/                        #
│   └── ...                      # 
├── logger/                      #
│   └── log_config.py            # Логирование
└── requirements.txt             # Зависимости для backend 
```

- **`frontend/`**

## Задачи (To-Do)

- [ ] **Backend:**
  - [ ] Написать endpoint `/upload` для загрузки CSV (FastAPI)

- [ ] **Frontend:**
  - [ ] Инициализировать React-app

- [ ] **Docker:**
  - [ ] Написать `docker-compose.yml` для запуска backend + frontend
     
- [ ] **CI/CD & Deploy:**
  - [ ] создать ветку Deploy
     
- [ ] **DB:**
  - [ ] написать модели таблиц
     
- [ ] **Vector DB:**
  - [ ] загрузить базу знаний
       
- [ ] **ML-логика:**
  - [ ] выбрать наилучшую модельку под задачу
  - [ ] подготовить данные для загрузки в Qdrant


## Запуск

**`docker`**

```bash
docker-compose up --build
```

**`frontend/`**

```bash
cd ./frontend
npm run dev
```

**`backend/`**




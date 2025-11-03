# хакатонщики 2.0

**Цель:** Настройка RAG для вопросов и ответов. Система, которая понимает на какие вопросы из базы знаний Альфа-банка можно ответить, а на какие - нет.

**Деплой:**  

**Видео:** 

**Инструкция:** 

## Стек

- **Backend:** Python, FastAPI
- **Frontend:** React JS
- **Контейнеризация:** Docker
- **Развёртывание:**
- **DB:**
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
  - [ ] 
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


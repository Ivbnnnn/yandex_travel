# Локальный запуск

Из корня репозитория:

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose ps
```

Для запуска Python-сервисов из корневого `.venv` установите локальные пакеты:

```powershell
.\.venv\Scripts\python -m pip install -e ./shared -e ./services/gateway -e ./services/identity_service
```

`docker compose` запускает:

| Контейнер | Назначение | Адрес на компьютере |
| --- | --- | --- |
| `postgres` | БД `travel_identity`, отдельная роль `identity_service` | `localhost:55432` |
| `kafka` | Один KRaft-брокер; внутри сети доступен как `kafka:19092` | `localhost:9092` |
| `kafka-init` | Однократно создаёт `identity.events.v1` и `analytics.events.v1` | — |
| `identity-migrate` | Однократно применяет миграции Alembic | — |
| `identity-service` | Регистрация, вход, refresh, профиль и избранное | `http://localhost:8001` |
| `identity-outbox` | Отправляет события из таблицы outbox в Kafka | — |
| `gateway` | Публичные `/api/v1/*` и событие сброса фильтров | `http://localhost:8000` |

PostgreSQL и Kafka хранят данные в именованных томах `postgres_data` и `kafka_data`.
Обычный `docker compose down` их сохраняет. Инициализация роли и базы PostgreSQL
выполняется при первом создании пустого тома.

Проверка запуска:

```powershell
curl.exe http://localhost:8000/health/live
curl.exe http://localhost:8001/health/ready
```

Пример регистрации через gateway:

```powershell
curl.exe -X POST http://localhost:8000/api/v1/auth/register `
  -H "Content-Type: application/json" `
  -d '{"email":"user@example.com","password":"change-this-password"}'
```

Реализованные маршруты identity: `POST /auth/register`, `/auth/login`,
`/auth/refresh`, `/auth/logout`, `GET /users/me`, `DELETE /users/me`,
`GET/POST /users/me/favorites` и `DELETE /users/me/favorites/{hotel_id}`.
Все они доступны через gateway с префиксом `/api/v1`.
`logout` отзывает refresh-сессию; уже выданный access-токен действует до истечения срока
(по умолчанию 15 минут). Деактивация пользователя закрывает доступ сразу.

Каталог пока не реализован. Добавление отеля в избранное проверяет его через catalog
и до запуска catalog-service вернёт `503`. Запросы gateway к ещё не созданным
catalog, search, booking, payment и notification также вернут `502`.

Настройки `.env.example` предназначены только для локального стенда. Перед запуском
в другом окружении замените пароли и `IDENTITY_JWT_SECRET`.

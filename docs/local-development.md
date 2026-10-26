# Запуск и API монолита

## Docker Compose

```powershell
python tools/setup_local.py
docker compose --env-file .env.monolith up --build -d
docker compose --env-file .env.monolith ps
docker compose --env-file .env.monolith logs --tail 100 app
```

API: http://localhost:8000/api/v1. Swagger: /docs. Healthcheck: /health.
Администратор: ADMIN_EMAIL и ADMIN_PASSWORD из .env.monolith.

## Локальный Python

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe tools/setup_local.py
docker compose --env-file .env.monolith up -d postgres
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Не запускайте одновременно Docker app и локальный uvicorn на одном порту.
DATABASE_URL для локального Python берётся из .env.monolith; для контейнера Compose
подставляет адрес postgres. Основная конфигурация монолита не читает .env.local.

## Основные API

Все пути ниже имеют префикс /api/v1.

| Методы | Путь | Доступ |
| --- | --- | --- |
| POST | /auth/register, /auth/login | Публичный, разрешённый Origin |
| POST | /auth/refresh, /auth/logout | Refresh cookie, Origin, X-CSRF-Token |
| GET, PATCH, DELETE | /users/me | Пользователь; DELETE деактивирует |
| GET | /filters, /hotels, /hotels/search | Гость |
| GET | /hotels/compare?hotel_ids=UUID&hotel_ids=UUID | Гость; 2–3 разных отеля |
| GET | /hotels/{id}, /hotels/{id}/rooms, /rooms/{id}, /rooms/{id}/rates | Гость |
| POST | /hotels, /hotels/{id}/rooms, /rooms/{id}/rates | Администратор |
| PATCH, DELETE | /hotels/{id}, /rooms/{id}, /rates/{id} | Администратор; DELETE деактивирует |
| POST | /hotels/{id}/photos, /rooms/{id}/photos | Администратор |
| POST | /favorites | Пользователь; hotel_id в теле |
| GET | /users/me/favorites, /favorites/{id} | Владелец |
| DELETE | /favorites/{id} | Владелец |
| POST | /bookings | Пользователь; Idempotency-Key |
| GET | /bookings/{id}, /users/me/bookings | Владелец |
| POST | /bookings/{id}/cancel | Владелец |
| POST | /payments | Владелец; Idempotency-Key; только demo |
| GET | /payments/{id} | Владелец; обновление статуса демоплатежа |
| POST | /hotels/{id}/reviews | Владелец завершённого проживания |
| GET | /users/me/notifications | Пользователь |
| PATCH | /notifications/{id}/read | Владелец |
| POST | /analytics/events | Публичный; только reset_filters |

Query поиска: city, check_in, check_out, guests_count, rooms_count,
interior_style, booking_purpose, tags, sort, page, limit. Для мультивыбора повторяйте
параметры: interior_style=light&interior_style=loft. Значения справочников — /filters.
Внутри одной группы используется OR, между группами AND. Условия номера относятся
к одной категории. total считает отели после проверки доступности до пагинации.

У /hotels/search обязательны city и обе даты. /hotels позволяет просматривать каталог
без дат. Невалидные поля дают 422, отсутствие объекта — 404, чужой объект — 403,
конфликт состояния или занятого остатка — 409. Тело бизнес-ошибки: code и detail.

Для POST/PATCH/DELETE с cookies передавайте Origin: http://localhost:8000
и X-CSRF-Token со значением csrf_token. Login/register требуют Origin без CSRF.
Swagger, открытый на localhost:8000, получает cookies после успешного login.
Bearer доступен для access JWT; при явном Bearer заголовке CSRF не требуется.

В login принимаются email/password. В register дополнительно name и необязательный
phone. Ответ не содержит пароль или хеш. Права администратора нельзя задать через
register или PATCH профиля.

## Выбранные упрощения

Демооплата вместо эквайринга; in-app уведомления вместо email/SMS; один тип валюты RUB;
категория номеров со stock; создание схемы на старте вместо миграций; один процесс.
Тестов нет — их добавляет тестировщик. Данные и воспроизводимый сценарий доступны
через API и Swagger. Полная схема слоёв и ограничений — в [README](../README.md).

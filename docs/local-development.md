# Локальный запуск

Нужны Python 3.12+ и Docker Desktop. Все команды выполняются из корня проекта.

```powershell
.\.venv\Scripts\python.exe -m pip install -e ./shared -e "./user_service[dev]" -e ./gateway
.\.venv\Scripts\python.exe tools/setup_local.py
docker compose --env-file .env.local up --build -d
docker compose --env-file .env.local ps
```

setup_local.py создаёт две RSA-пары в .local/keys и .env.local со случайными
CSRF secret и паролем PostgreSQL. Повторный запуск сохраняет существующие файлы.
Старый .env сохраняется. Настройки читают .env, затем .env.local; переменные процесса
имеют приоритет. Ключи и .env.local исключены из Git и контекста сборки Docker.

Docker запускает PostgreSQL, миграцию, user-service и gateway. API доступен на
http://localhost:8000. У user-service нет опубликованного порта. Новый том
user_postgres_data не затрагивает прежние тома проекта.
Kafka включается отдельно: docker compose --env-file .env.local --profile messaging up -d kafka.

Проверка полного сценария с временным пользователем:

```powershell
curl.exe http://localhost:8000/health/live
.\.venv\Scripts\python.exe tools/smoke_auth.py
```

## Запуск Python на хосте

Установите пакеты и создайте конфигурацию командами выше, затем:

```powershell
docker compose --env-file .env.local up -d postgres
.\.venv\Scripts\python.exe -m alembic -c user_service/alembic.ini upgrade head
.\.venv\Scripts\python.exe -m uvicorn user_service.main:create_user_app --factory --port 8001
```

В другом терминале:

```powershell
.\.venv\Scripts\python.exe -m uvicorn gateway.main:create_gateway_app --factory --port 8000
```

Миграциям нужен только DATABASE_URL. Одновременно запускать host gateway и Docker
gateway на одном порту нельзя. Swagger user-service при запуске на хосте: localhost:8001/docs.

## Маршруты через gateway

| Метод | Путь | Назначение |
| --- | --- | --- |
| POST | /api/users/auth/register | email, password, name, phone; ответ 201 без входа |
| POST | /api/users/auth/login | email, password; профиль и три cookies |
| POST | /api/users/auth/refresh | Новые JWT и CSRF по действующему refresh |
| POST | /api/users/auth/logout | Отзыв refresh, очистка cookies, ответ 204 |
| GET | /api/users/users/me | Свой профиль |
| PATCH | /api/users/users/me | Изменение email/name/phone |
| DELETE | /api/users/users/me | Удаление пользователя и сессий, очистка cookies |
| GET | /api/users/users/{id} | Только свой профиль; чужой ID даёт 403 |

Запросы записи требуют Origin из ALLOWED_ORIGINS. Login/register защищены Origin;
refresh/logout и закрытые запросы записи дополнительно требуют X-CSRF-Token.

Пример браузерного клиента с localhost:5173:

```javascript
const api = "http://localhost:8000/api/users";
await fetch(api + "/auth/login", {
  method: "POST",
  credentials: "include",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email: "user@example.com", password: "your-password" })
});

const csrf = decodeURIComponent(
  document.cookie.split("; ").find(item => item.startsWith("csrf_token="))?.split("=")[1] ?? ""
);
await fetch(api + "/users/me", {
  method: "PATCH",
  credentials: "include",
  headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
  body: JSON.stringify({ name: "Новое имя" })
});
```

При другом адресе страницы измените ALLOWED_ORIGINS в .env.local. Для HTTPS
установите COOKIE_SECURE=true. Пример рассчитан на один hostname с разными портами.
Для разных сайтов нужны SameSite=none, Secure и отдельное решение о размещении
CSRF-cookie и клиента; фронтенд не сможет читать cookie чужого hostname.

## Проверки

```powershell
.\.venv\Scripts\python.exe -m ruff check shared user_service gateway tests tools
.\.venv\Scripts\python.exe -m pytest -q
```

По умолчанию каждый сценарий получает отдельную SQLite; запрос проходит через gateway
до user-service. Для PostgreSQL задайте TEST_DATABASE_URL. Имя тестовой базы обязательно
начинается с user_service_test: тесты сбрасывают users и refresh_sessions этой базы.

Последовательность проверки токенов и ограничения отзыва описаны в
[ARCHITECTURE.md](../ARCHITECTURE.md).

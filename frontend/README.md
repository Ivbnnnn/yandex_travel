# Фронтенд «Путешествия»

React + TypeScript + Vite + Tailwind 4 + TanStack Query + React Router. Работает с бэком из этого репозитория.

## Запуск

```bash
# 1. бэк (из корня репозитория)
python tools/setup_local.py
docker compose --env-file .env.monolith up --build -d
# в .env.monolith для локального HTTP: COOKIE_SECURE=false

# 2. фронт
cd frontend
npm install
npm run dev          # http://localhost:5173
```

Vite проксирует `/api` на `localhost:8000` и подставляет заголовок `Origin: http://localhost:8000`,
поэтому настройки бэка (`ALLOWED_ORIGINS`) менять не нужно.

## Фото в каталоге

В сид-данных фотографий нет (показываются цветные заглушки). Чтобы добавить:

```bash
ADMIN_PASSWORD='<из .env.monolith>' npm run seed
```

## Структура

```
src/
├── api/        client.ts (fetch + CSRF + refresh), types.ts, hooks.ts
├── components/ Layout, SearchForm, HotelCard
├── lib/        format.ts (даты, деньги), search.ts (состояние поиска в URL)
├── pages/      Home, Search, Hotel, Compare, Login, Checkout, Booking, MyBookings, Favorites, Profile
├── auth.tsx    AuthContext (статус через GET /users/me)
├── compare.tsx выбор 2–3 отелей для сравнения
└── ui.tsx      кнопки, чипы, рейтинг, заглушки фото, тосты
```

## Как это устроено

- **Авторизация:** токены в httpOnly-cookie; на POST/PATCH/DELETE уходит `X-CSRF-Token` из cookie `csrf_token`;
  на 401 один раз вызывается `/auth/refresh` и запрос повторяется.
- **Поиск:** город, даты, гости и фильтры хранятся в URL (работают «Назад» и обновление страницы).
- **Выбор до входа:** отель/номер/тариф/даты лежат в URL страницы оформления; после входа возвращаемся туда же.
- **Бронь:** `POST /bookings` с `Idempotency-Key` (ключ хранится в sessionStorage, повторный клик не создаёт дубль),
  дальше страница брони с таймером удержания (15 минут) и демо-оплатой.
- **Демо-оплата:** успех, отказ, таймаут (для таймаута опрашивается `GET /payments/{id}`).

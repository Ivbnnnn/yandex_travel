// Добавляет демо-фото отелям и номерам через админский API (в сид-данных фото нет).
// Запуск (из папки frontend):
//   ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD=... node scripts/seed-photos.mjs
// Email и пароль админа — в .env.monolith (ADMIN_EMAIL, ADMIN_PASSWORD). Нужен Node 20+.
const API = process.env.API_URL ?? 'http://localhost:8000/api/v1'
const email = process.env.ADMIN_EMAIL ?? 'admin@example.com'
const password = process.env.ADMIN_PASSWORD
if (!password) {
  console.error('Укажите ADMIN_PASSWORD (см. .env.monolith)')
  process.exit(1)
}

const login = await fetch(`${API}/auth/login`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', Origin: 'http://localhost:8000' },
  body: JSON.stringify({ email, password }),
})
if (!login.ok) {
  console.error('Вход не удался:', login.status, await login.text())
  process.exit(1)
}
const cookie = login.headers.getSetCookie().find((c) => c.startsWith('access_token='))
const token = cookie.split(';')[0].split('=')[1]
// С Bearer-токеном CSRF и Origin не требуются
const auth = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }

const photo = (seed, w = 1200, h = 800) => `https://picsum.photos/seed/${seed}/${w}/${h}`
const list = await (await fetch(`${API}/hotels?limit=100&sort=name`)).json()
let added = 0

for (const item of list.items) {
  const id = item.hotel_id
  const detail = await (await fetch(`${API}/hotels/${id}`)).json()
  if (detail.photos.length === 0) {
    for (let i = 0; i < 5; i++) {
      await fetch(`${API}/hotels/${id}/photos`, {
        method: 'POST', headers: auth,
        body: JSON.stringify({ url: photo(`${id}-${i}`), sort_order: i }),
      })
      added++
    }
  }
  for (const room of detail.rooms) {
    if (room.photos.length === 0) {
      await fetch(`${API}/rooms/${room.room_id}/photos`, {
        method: 'POST', headers: auth,
        body: JSON.stringify({ url: photo(`${room.room_id}`, 800, 600), sort_order: 0 }),
      })
      added++
    }
  }
}
console.log(`Готово, добавлено фото: ${added}`)

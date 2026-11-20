// Добавляет фото отелям и номерам через админский API (в сид-данных фото нет).
// Запуск из папки frontend:
//   ADMIN_PASSWORD='...' npm run seed
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

// Свои фото у каждого города. hotels: по одному на отель
// (порядок: «У парка», «Тихий двор», «Городские истории»); rooms: фото номеров города.
const PHOTOS = {
  'Москва': {
    hotels: [
      'https://avatars.mds.yandex.net/i?id=7f7690da638652b9216c4bfbfef3eb8387e237be-5335549-images-thumbs&n=13',
      'https://avatars.mds.yandex.net/i?id=c7e8e0e0cf442c08c5f656c3e18bab4175543433-11003380-images-thumbs&n=13',
      'https://cdn3.enuygun.com/media/lib/1x720/uploads/image/rooms-boutique-moskova-genel-35760453.webp',
    ],
    rooms: [
      'https://avatars.mds.yandex.net/get-travel-rooms/20703332/2a0000019f2939206bfbc771c2cde5300b2a/optimize',
      'https://avatars.mds.yandex.net/i?id=9d93ff6686ead22d08e28675c3f92edf0c941996-5879690-images-thumbs&n=13',
      'https://avatars.mds.yandex.net/i?id=561053f2fa3feb3c0ccbb074f014d8b5a1cb4a82-3534103-images-thumbs&n=13',
      'https://avatars.mds.yandex.net/i?id=aea4d5824c66e71ee9b66a806e85a12504e76d88-5289253-images-thumbs&n=13',
      'https://avatars.mds.yandex.net/i?id=a64f85acc60610f3f3c868b2a4622e074fc9c10a-5236521-images-thumbs&n=13',
      'https://avatars.mds.yandex.net/i?id=15a002b8bd2a30d7c1dad77efeed93cba093ffbd-5887708-images-thumbs&n=13',
      'https://avatars.mds.yandex.net/i?id=da75271f05dbddbec8f5a08bd89e13dfc044a188-4767450-images-thumbs&n=13',
      'https://avatars.mds.yandex.net/i?id=bb1bbd3bcf81379d85ccab47c448b8f8f85a3c62-8354186-images-thumbs&n=13',
      'https://avatars.mds.yandex.net/i?id=4c687cab88e6bc8686b6db99ebac2600ee234c2b-9747317-images-thumbs&n=13',
      'https://avatars.mds.yandex.net/i?id=c729cd2a750916930d19abd812f38a4a36e55d8b-5221780-images-thumbs&n=13',
    ],
  },
  'Санкт-Петербург': {
    hotels: [
      'https://avatars.mds.yandex.net/i?id=2af5b9c136c164e6f8044ee99a0549dd6968a6da-5296855-images-thumbs&n=13',
      'https://avatars.mds.yandex.net/i?id=293e181d4b08c18a61dc55c25ae679966450db60-8275014-images-thumbs&n=13',
      'https://avatars.mds.yandex.net/i?id=5f380f021521c3a5320dc09382c1b0e345094b3f-5552450-images-thumbs&n=13',
    ],
    rooms: [
      'https://avatars.mds.yandex.net/i?id=e775a757e5a0d4ce912b6be15d66e47af2c7fe94-5224518-images-thumbs&n=13',
      'https://avatars.mds.yandex.net/i?id=8d94fbf6c1f3bcd881a58a4e23d90054288150bd-4800903-images-thumbs&n=13',
      'https://avatars.mds.yandex.net/i?id=33f46588fba709848b2c827dc5628f773c649b0f-6263806-images-thumbs&n=13',
      'https://avatars.mds.yandex.net/i?id=3920fefe4cb1e4a58c486a30099c134b70f8a609-8497835-images-thumbs&n=13',
      'https://avatars.mds.yandex.net/i?id=b213c54351bdf9bd438afc1fbb2fbfea43f9bbc7-5575740-images-thumbs&n=13',
      'https://avatars.mds.yandex.net/i?id=a1165851a742abb2c6aba73fddecf15c2685ff96-9858428-images-thumbs&n=13',
      'https://avatars.mds.yandex.net/i?id=b137c53200612488b79e8da8fabf6f05998ce13e-10268314-images-thumbs&n=13',
      'https://avatars.mds.yandex.net/i?id=820c9e410e39012095633dc5caf9684321653544-16496400-images-thumbs&n=13',
      'https://avatars.mds.yandex.net/i?id=70b463824dd90a8ef93a937873d5f505fdf323d7-8978567-images-thumbs&n=13',
      'https://avatars.mds.yandex.net/i?id=2bf2a0bb490fa65edecb354e01dbeceb18e63aa2-5209122-images-thumbs&n=13',
      'https://avatars.mds.yandex.net/i?id=5e4ae180b589e909bf7a229c8fbd49e5d3263aa4-10671814-images-thumbs&n=13',
    ],
  },
  'Казань': {
    hotels: [
      'https://avatars.mds.yandex.net/i?id=76f3aa49a19cc2bde887ee026ecb75264700f105-5277428-images-thumbs&n=13',
      'https://avatars.mds.yandex.net/i?id=4dfba0033e803d15bc7c636f43248ee2_sr-7004933-images-thumbs&n=13',
      'https://avatars.mds.yandex.net/i?id=f8e8a802797275a09f89eae44374e6c10e75fbe6-9240324-images-thumbs&n=13',
    ],
    rooms: [
      'https://avatars.mds.yandex.net/i?id=81a5cbfe96c24be86a743698f36cbfc246a47644-4377975-images-thumbs&n=13',
      'https://avatars.mds.yandex.net/i?id=4da5cbdb2cc07e4b672ad1b8aa6fc5847181ba12-12004727-images-thumbs&n=13',
      'https://avatars.mds.yandex.net/i?id=614e33897b0232c91e7e0a8465c7590e986932dd-15067175-images-thumbs&n=13',
      'https://avatars.mds.yandex.net/i?id=ab04277a8698c2fcabba9b5bd690b8b717f98748-5579113-images-thumbs&n=13',
      'https://avatars.mds.yandex.net/i?id=aaebcd034e2bb7a0baab13feac15a16655648b8f-12475759-images-thumbs&n=13',
      'https://avatars.mds.yandex.net/i?id=02f6229a412fbf1b884d04b3d2086faa61ee7839-5662910-images-thumbs&n=13',
      'https://avatars.mds.yandex.net/i?id=ddb29619c12aaeb15e9b88f80a1842318cba0b36-13104207-images-thumbs&n=13',
      'https://avatars.mds.yandex.net/i?id=f40d0c1f9af3efc6eeacf3d7164ed8a14027d604-4922198-images-thumbs&n=13',
      'https://avatars.mds.yandex.net/i?id=cfeadfa25f8c5c5b1828d60ad803674ff8a84f97-5869745-images-thumbs&n=13',
      'https://avatars.mds.yandex.net/i?id=854d315332a0d1b1b2a4aa1b07129f4819a988cd-10734181-images-thumbs&n=13',
    ],
  },
}
const HOTEL_ORDER = ['У парка', 'Тихий двор', 'Городские истории']
const ROOM_ORDER = ['Светлый стандарт', 'Минимализм', 'Лофт']

// Защита: одна и та же ссылка не должна встречаться в двух городах
const seen = new Map()
for (const [city, g] of Object.entries(PHOTOS)) {
  for (const url of [...g.hotels, ...g.rooms]) {
    if (seen.has(url) && seen.get(url) !== city) {
      console.error(`Ссылка повторяется в городах «${seen.get(url)}» и «${city}»:\n${url}`)
      process.exit(1)
    }
    seen.set(url, city)
  }
}

// Запасной вариант для города, где ссылки не заданы
const KW = { 'Москва': 'moscow', 'Санкт-Петербург': 'petersburg', 'Казань': 'kazan' }
const fallback = (city, room, n) =>
  `https://loremflickr.com/${room ? '800/600' : '1200/800'}/${KW[city] ?? 'city'},${room ? 'bedroom' : 'hotel'}?lock=${Object.keys(PHOTOS).indexOf(city) * 1000 + n}`

const pick = (list, i) => (list.length ? list[i % list.length] : null)
const post = (path, url) =>
  fetch(`${API}${path}`, { method: 'POST', headers: auth, body: JSON.stringify({ url, sort_order: 0 }) })

const list = await (await fetch(`${API}/hotels?limit=100&sort=name`)).json()
let added = 0

for (const item of list.items) {
  const group = PHOTOS[item.city] ?? { hotels: [], rooms: [] }
  const k = Math.max(0, HOTEL_ORDER.indexOf(item.name.split(' · ')[0]))
  const detail = await (await fetch(`${API}/hotels/${item.hotel_id}`)).json()

  if (detail.photos.length === 0) {
    await post(`/hotels/${item.hotel_id}/photos`, pick(group.hotels, k) ?? fallback(item.city, false, k))
    added++
  }
  for (const room of detail.rooms) {
    if (room.photos.length > 0) continue
    const j = Math.max(0, ROOM_ORDER.indexOf(room.name))
    await post(`/rooms/${room.room_id}/photos`, pick(group.rooms, k * 3 + j) ?? fallback(item.city, true, k * 3 + j))
    added++
  }
}
console.log(`Готово, добавлено фото: ${added}`)

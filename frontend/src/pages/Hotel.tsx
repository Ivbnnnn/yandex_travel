import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useHotel } from '../api/hooks'
import type { Room } from '../api/types'
import { FavButton } from '../components/HotelCard'
import { SearchForm } from '../components/SearchForm'
import { dateRu, money, nightsBetween, nightsText, num } from '../lib/format'
import { datesParams, parseSearch } from '../lib/search'
import { Button, ErrorBox, Photo, Pin, Rating, Spinner, Tag, useToast } from '../ui'
import { useCompare } from '../compare'

export default function HotelPage() {
  const { id = '' } = useParams()
  const [sp, setSp] = useSearchParams()
  const s = parseSearch(sp)
  const qs = datesParams(s).toString()
  const q = useHotel(id, qs)
  const { ids, toggle } = useCompare()
  const toast = useToast()
  if (q.isLoading) return <Spinner />
  if (q.isError) return <ErrorBox error={q.error} />
  const h = q.data!
  const nights = nightsBetween(s.check_in, s.check_out)
  const photos = h.photos.slice(0, 5)
  const map =
    h.latitude != null && h.longitude != null
      ? `https://yandex.ru/maps/?pt=${num(h.longitude)},${num(h.latitude)}&z=15&l=map`
      : `https://yandex.ru/maps/?text=${encodeURIComponent(h.address)}`

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-2">
          <h1 className="text-3xl font-extrabold tracking-tight">{h.name}</h1>
          <div className="flex flex-wrap items-center gap-3">
            <Rating value={h.rating} />
            <a href={map} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-sm text-muted underline-offset-2 hover:underline">
              <Pin /> {h.address}
            </a>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex cursor-pointer items-center gap-2 text-sm text-muted">
            <input
              type="checkbox" className="size-4 accent-black" checked={ids.includes(h.hotel_id)}
              onChange={() => !toggle(h.hotel_id) && toast('Для сравнения можно выбрать не больше трёх отелей', 'error')}
            />
            Сравнить
          </label>
          <FavButton hotelId={h.hotel_id} />
        </div>
      </div>

      <div className="grid h-72 gap-2 overflow-hidden rounded-2xl sm:h-96 sm:grid-cols-4 sm:grid-rows-2">
        {(photos.length < 3 ? [0] : [0, 1, 2, 3, 4]).map((i) => (
          <Photo
            key={i} src={photos[i]?.url} seed={h.hotel_id + i} alt={h.name}
            className={`size-full ${photos.length < 3 ? 'sm:col-span-4 sm:row-span-2' : i === 0 ? 'sm:col-span-2 sm:row-span-2' : 'hidden sm:grid'}`}
          />
        ))}
      </div>

      <div className="flex flex-wrap gap-1.5">{h.tags.map((t) => <Tag key={t}>{t}</Tag>)}</div>
      <p className="max-w-3xl text-[17px] leading-relaxed">{h.description}</p>

      <section className="space-y-4">
        <h2 className="text-2xl font-bold">Номера и тарифы</h2>
        <SearchForm
          key={s.check_in + s.check_out + s.guests_count + s.rooms_count}
          initial={s} showCity={false} submitText="Обновить"
          onSubmit={(n) => setSp(datesParams(n))}
        />
        <p className="text-sm text-muted">
          {dateRu(s.check_in)} — {dateRu(s.check_out)}, {nightsText(nights)}
        </p>
        {h.rooms.length === 0 && <p className="text-muted">В этом отеле пока нет номеров.</p>}
        {h.rooms.map((r) => <RoomCard key={r.room_id} room={r} hotelId={h.hotel_id} s={s} nights={nights} />)}
      </section>

      <section className="space-y-3">
        <h2 className="text-2xl font-bold">Отзывы</h2>
        {h.reviews.length === 0 && <p className="text-muted">Пока никто не оставил отзыв. Отзыв можно написать после завершённого проживания.</p>}
        <div className="grid gap-3 sm:grid-cols-2">
          {h.reviews.map((r) => (
            <div key={r.review_id} className="rounded-2xl bg-white p-5">
              <div className="mb-1 font-bold">{'★'.repeat(r.rating)}<span className="text-line">{'★'.repeat(5 - r.rating)}</span></div>
              <p>{r.text}</p>
              <div className="mt-2 text-sm text-muted">{dateRu(r.created_at.slice(0, 10), true)}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}

function RoomCard({ room, hotelId, s, nights }: { room: Room; hotelId: string; s: ReturnType<typeof parseSearch>; nights: number }) {
  const left = room.available_count
  return (
    <article className="overflow-hidden rounded-2xl bg-white">
      <div className="grid sm:grid-cols-[16rem_1fr]">
        <Photo src={room.photos[0]?.url} seed={room.room_id} alt={room.name} className="h-44 w-full sm:h-full" />
        <div className="p-5">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h3 className="text-xl font-bold">{room.name}</h3>
            <span className="text-sm text-muted">до {room.capacity} гостей{left !== null && left <= 3 && left > 0 ? ` · осталось ${left}` : ''}</span>
          </div>
          <p className="mt-1 text-muted">{room.description}</p>
          <div className="mt-2 flex flex-wrap gap-1.5">{room.tags.map((t) => <Tag key={t}>{t}</Tag>)}</div>
        </div>
      </div>
      <div className="divide-y divide-line border-t border-line">
        {room.rates.map((r) => (
          <div key={r.rate_id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
            <div>
              <div className="font-semibold">{r.name}</div>
              <div className="text-sm text-muted">{r.breakfast_included ? 'Завтрак включён' : 'Без питания'} · {r.cancellation_policy}</div>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <div className="text-xl font-extrabold">{money(num(r.price) * nights * s.rooms_count, r.currency)}</div>
                <div className="text-xs text-muted">{money(r.price, r.currency)} за ночь</div>
              </div>
              {room.can_book ? (
                <Link to={`/checkout?${new URLSearchParams({ hotel: hotelId, room: room.room_id, rate: r.rate_id, ...Object.fromEntries(datesParams(s)) })}`}>
                  <Button>Выбрать</Button>
                </Link>
              ) : (
                <Button disabled>Недоступно</Button>
              )}
            </div>
          </div>
        ))}
        {!room.can_book && room.rates.length > 0 && (
          <div className="bg-surface-2 px-5 py-3 text-sm text-muted">Нет свободных номеров на эти даты или номер не вмещает всех гостей.</div>
        )}
      </div>
    </article>
  )
}

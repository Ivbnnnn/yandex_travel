import { Link, Navigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { HotelDetail } from '../api/types'
import { useCompare } from '../compare'
import { money, num } from '../lib/format'
import { Button, ErrorBox, Photo, Rating, Spinner, Tag } from '../ui'

export default function Compare() {
  const { ids, toggle } = useCompare()
  const q = useQuery({
    queryKey: ['compare', ids],
    queryFn: () => api<{ items: HotelDetail[] }>(`/hotels/compare?${ids.map((i) => `hotel_ids=${i}`).join('&')}`),
    enabled: ids.length >= 2,
  })
  if (ids.length < 2) return <Navigate to="/" replace />
  if (q.isLoading) return <Spinner />
  if (q.isError) return <ErrorBox error={q.error} />
  const items = q.data!.items
  const minPrice = (h: HotelDetail) => {
    const p = h.rooms.flatMap((r) => r.rates.map((x) => num(x.price)))
    return p.length ? money(Math.min(...p)) : '—'
  }
  const rows: [string, (h: HotelDetail) => React.ReactNode][] = [
    ['Рейтинг', (h) => <Rating value={h.rating} />],
    ['Цена за ночь от', (h) => <b>{minPrice(h)}</b>],
    ['Город', (h) => h.city],
    ['Адрес', (h) => h.address],
    ['Категорий номеров', (h) => h.rooms.length],
    ['Удобства', (h) => <div className="flex flex-wrap gap-1.5">{h.tags.map((t) => <Tag key={t}>{t}</Tag>)}</div>],
    ['Отзывов', (h) => h.reviews.length],
    ['Описание', (h) => <span className="text-sm text-muted">{h.description}</span>],
  ]
  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-extrabold tracking-tight">Сравнение отелей</h1>
      <div className="overflow-x-auto rounded-2xl bg-white">
        <table className="w-full min-w-[40rem] text-left align-top">
          <thead>
            <tr>
              <th className="w-44 p-4" />
              {items.map((h) => (
                <th key={h.hotel_id} className="p-4 align-top font-normal">
                  <Photo src={h.photos[0]?.url} seed={h.hotel_id} className="mb-3 h-32 w-full rounded-xl" />
                  <Link to={`/hotels/${h.hotel_id}`} className="block text-lg font-bold hover:underline">{h.name}</Link>
                  <Button variant="ghost" size="sm" className="-ml-3 mt-1" onClick={() => toggle(h.hotel_id)}>Убрать</Button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map(([label, cell]) => (
              <tr key={label} className="border-t border-line">
                <th className="p-4 text-sm font-medium text-muted">{label}</th>
                {items.map((h) => <td key={h.hotel_id} className="p-4">{cell(h)}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

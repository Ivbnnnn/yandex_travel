import { Link, useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api, errMsg } from '../api/client'
import type { HotelListItem } from '../api/types'
import { useFavorites } from '../api/hooks'
import { useAuth } from '../auth'
import { useCompare } from '../compare'
import { money } from '../lib/format'
import { Heart, Photo, Pin, Rating, Tag, useToast } from '../ui'

export function FavButton({ hotelId }: { hotelId: string }) {
  const { user } = useAuth()
  const nav = useNavigate()
  const qc = useQueryClient()
  const toast = useToast()
  const favs = useFavorites()
  const fav = favs.data?.items.find((f) => f.hotel_id === hotelId)
  const m = useMutation({
    mutationFn: () =>
      fav
        ? api(`/favorites/${fav.favorite_id}`, { method: 'DELETE' })
        : api('/favorites', { method: 'POST', body: { hotel_id: hotelId } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['favorites'] }),
    onError: (e) => toast(errMsg(e), 'error'),
  })
  return (
    <button
      type="button"
      aria-label={fav ? 'Убрать из избранного' : 'В избранное'}
      disabled={m.isPending}
      onClick={() => (user ? m.mutate() : nav(`/login?next=${encodeURIComponent(location.pathname + location.search)}`))}
      className="grid size-10 cursor-pointer place-items-center rounded-full bg-white/95 shadow transition-transform hover:scale-105"
    >
      <Heart filled={!!fav} />
    </button>
  )
}

export function HotelCard({ hotel, query }: { hotel: HotelListItem; query: string }) {
  const { ids, toggle } = useCompare()
  const toast = useToast()
  const to = `/hotels/${hotel.hotel_id}?${query}`
  return (
    <article className="flex flex-col overflow-hidden rounded-2xl bg-white sm:flex-row">
      <Link to={to} className="relative block shrink-0 sm:w-72">
        <Photo src={hotel.preview_photo_url} seed={hotel.hotel_id} alt={hotel.name} className="h-52 w-full sm:h-full" />
      </Link>
      <div className="flex flex-1 flex-col gap-2 p-5">
        <div className="flex items-start justify-between gap-3">
          <Link to={to} className="text-xl font-bold leading-tight hover:underline">{hotel.name}</Link>
          <FavButton hotelId={hotel.hotel_id} />
        </div>
        <Rating value={hotel.rating} />
        <p className="flex items-center gap-1 text-sm text-muted"><Pin /> {hotel.address}</p>
        <div className="flex flex-wrap gap-1.5">{hotel.tags.map((t) => <Tag key={t}>{t}</Tag>)}</div>
        <div className="mt-auto flex flex-wrap items-end justify-between gap-3 pt-3">
          <label className="flex cursor-pointer items-center gap-2 text-sm text-muted">
            <input
              type="checkbox" className="size-4 accent-black"
              checked={ids.includes(hotel.hotel_id)}
              onChange={() => !toggle(hotel.hotel_id) && toast('Для сравнения можно выбрать не больше трёх отелей', 'error')}
            />
            Сравнить
          </label>
          <div className="text-right">
            <div className="text-sm text-muted">за ночь от</div>
            <div className="text-2xl font-extrabold">{money(hotel.min_price, hotel.currency)}</div>
          </div>
        </div>
      </div>
    </article>
  )
}

import { addDays, todayISO } from './format'

export type Sort = 'price_asc' | 'price_desc' | 'rating_desc' | 'name'

export interface SearchState {
  city: string
  check_in: string
  check_out: string
  guests_count: number
  rooms_count: number
  interior_style: string[]
  booking_purpose: string[]
  tags: string[]
  sort: Sort
  page: number
}

const int = (v: string | null, def: number, min: number, max: number) => {
  const n = parseInt(v ?? '', 10)
  return Number.isFinite(n) ? Math.min(max, Math.max(min, n)) : def
}

// Состояние поиска живёт в URL; даты по умолчанию — через неделю на 2 ночи
export function parseSearch(sp: URLSearchParams): SearchState {
  let check_in = sp.get('check_in') ?? ''
  let check_out = sp.get('check_out') ?? ''
  if (!check_in || check_in < todayISO()) check_in = addDays(todayISO(), 7)
  if (!check_out || check_out <= check_in) check_out = addDays(check_in, 2)
  const sort = sp.get('sort') as Sort
  return {
    city: sp.get('city') ?? '',
    check_in,
    check_out,
    guests_count: int(sp.get('guests_count'), 2, 1, 100),
    rooms_count: int(sp.get('rooms_count'), 1, 1, 20),
    interior_style: sp.getAll('interior_style'),
    booking_purpose: sp.getAll('booking_purpose'),
    tags: sp.getAll('tags'),
    sort: ['price_asc', 'price_desc', 'rating_desc', 'name'].includes(sort) ? sort : 'price_asc',
    page: int(sp.get('page'), 1, 1, 10000),
  }
}

export function toParams(s: SearchState): URLSearchParams {
  const p = new URLSearchParams()
  if (s.city) p.set('city', s.city)
  p.set('check_in', s.check_in)
  p.set('check_out', s.check_out)
  p.set('guests_count', String(s.guests_count))
  p.set('rooms_count', String(s.rooms_count))
  s.interior_style.forEach((v) => p.append('interior_style', v))
  s.booking_purpose.forEach((v) => p.append('booking_purpose', v))
  s.tags.forEach((v) => p.append('tags', v))
  p.set('sort', s.sort)
  if (s.page > 1) p.set('page', String(s.page))
  return p
}

// Только даты и гости — то, что нужно карточке отеля и оформлению
export function datesParams(s: SearchState): URLSearchParams {
  return new URLSearchParams({
    check_in: s.check_in,
    check_out: s.check_out,
    guests_count: String(s.guests_count),
    rooms_count: String(s.rooms_count),
  })
}

import { Navigate, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import { useFilters, useSearch } from '../api/hooks'
import { HotelCard } from '../components/HotelCard'
import { SearchForm } from '../components/SearchForm'
import { nightsBetween, nightsText, plural } from '../lib/format'
import { datesParams, parseSearch, toParams, type SearchState, type Sort } from '../lib/search'
import { Button, Chip, Empty, ErrorBox, Spinner, inputCls } from '../ui'

const TAGS = [['wifi', 'Wi-Fi'], ['parking', 'Парковка'], ['pets', 'С питомцами']]

export default function Search() {
  
  const [sp, setSp] = useSearchParams()
  const s = parseSearch(sp)
  const filters = useFilters()
  const q = useSearch(toParams(s).toString(), !!s.city)
  if (!s.city) return <Navigate to="/" replace />

  const update = (patch: Partial<SearchState>) => setSp(toParams({ ...s, page: 1, ...patch }))
  const toggle = (key: 'interior_style' | 'booking_purpose' | 'tags', v: string) =>
    update({ [key]: s[key].includes(v) ? s[key].filter((x) => x !== v) : [...s[key], v] })
  const filtersOn = s.interior_style.length + s.booking_purpose.length + s.tags.length > 0

  // «Сбросить» очищает только доп. фильтры; город и даты остаются
  const reset = () => {
    update({ interior_style: [], booking_purpose: [], tags: [], sort: 'price_asc' })
    api('/analytics/events', {
      method: 'POST',
      body: { name: 'reset_filters', city: s.city, check_in: s.check_in, check_out: s.check_out },
    }).catch(() => {})
  }

  const total = q.data?.total ?? 0
  const pages = Math.max(1, Math.ceil(total / 20))
  const nights = nightsBetween(s.check_in, s.check_out)
  const dq = datesParams(s).toString()

  return (
    <div className="space-y-5">
      <SearchForm key={s.check_in + s.check_out + s.city} initial={s} onSubmit={(n) => setSp(toParams(n))} />
      <div className="grid gap-5 lg:grid-cols-[17rem_1fr]">
        <aside className="h-fit space-y-5 rounded-2xl bg-white p-5">
          <div>
            <div className="mb-2 font-bold">Сортировка</div>
            <select className={inputCls} value={s.sort} onChange={(e) => update({ sort: e.target.value as Sort })}>
              <option value="price_asc">Сначала дешёвые</option>
              <option value="price_desc">Сначала дорогие</option>
              <option value="rating_desc">По рейтингу</option>
              <option value="name">По названию</option>
            </select>
          </div>
          <FilterGroup title="Стиль интерьера">
            {filters.data?.interior_styles.map((o) => (
              <Chip key={o.code} active={s.interior_style.includes(o.code)} onClick={() => toggle('interior_style', o.code)}>{o.name}</Chip>
            ))}
          </FilterGroup>
          <FilterGroup title="Цель поездки">
            {filters.data?.booking_purposes.map((o) => (
              <Chip key={o.code} active={s.booking_purpose.includes(o.code)} onClick={() => toggle('booking_purpose', o.code)}>{o.name}</Chip>
            ))}
          </FilterGroup>
          <FilterGroup title="Удобства">
            {TAGS.map(([code, name]) => (
              <Chip key={code} active={s.tags.includes(code)} onClick={() => toggle('tags', code)}>{name}</Chip>
            ))}
          </FilterGroup>
          <Button variant="secondary" className="w-full" onClick={reset} disabled={!filtersOn && s.sort === 'price_asc'}>Сбросить фильтры</Button>
        </aside>

        <section className="space-y-4">
          {q.isLoading ? <Spinner /> : q.isError ? <ErrorBox error={q.error} /> : (
            <>
              <h1 className="text-2xl font-bold">
                {s.city}: {total} {plural(total, ['вариант', 'варианта', 'вариантов'])}
                <span className="ml-2 text-base font-normal text-muted">{nightsText(nights)}</span>
              </h1>
              {total === 0 ? (
                <Empty
                  title="Ничего не нашли"
                  text="Попробуйте другие даты, меньше гостей или уберите часть фильтров."
                  action={filtersOn ? <Button onClick={reset}>Сбросить фильтры</Button> : undefined}
                />
              ) : (
                <div className={`space-y-4 transition-opacity ${q.isPlaceholderData ? 'opacity-60' : ''}`}>
                  {q.data!.items.map((h) => <HotelCard key={h.hotel_id} hotel={h} query={dq} />)}
                </div>
              )}
              {pages > 1 && (
                <div className="flex items-center justify-center gap-3 pt-2">
                  <Button variant="secondary" disabled={s.page <= 1} onClick={() => { update({ page: s.page - 1 }); scrollTo(0, 0) }}>Назад</Button>
                  <span className="text-sm text-muted">{s.page} из {pages}</span>
                  <Button variant="secondary" disabled={s.page >= pages} onClick={() => { update({ page: s.page + 1 }); scrollTo(0, 0) }}>Дальше</Button>
                </div>
              )}
            </>
          )}
        </section>
      </div>
    </div>
  )
}

const FilterGroup = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <div>
    <div className="mb-2 font-bold">{title}</div>
    <div className="flex flex-wrap gap-2">{children}</div>
  </div>
)

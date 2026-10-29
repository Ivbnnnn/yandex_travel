import { useState, type FormEvent } from 'react'
import { addDays, todayISO } from '../lib/format'
import type { SearchState } from '../lib/search'
import { Button } from '../ui'

const field = 'block rounded-xl px-4 py-2 transition-colors hover:bg-surface-2 focus-within:bg-surface-2'
const input = 'mt-0.5 w-full bg-transparent text-[15px] font-semibold outline-none'

export function SearchForm({
  initial, onSubmit, showCity = true, submitText = 'Найти',
}: {
  initial: SearchState
  onSubmit: (s: SearchState) => void
  showCity?: boolean
  submitText?: string
}) {
  const [s, setS] = useState(initial)
  const [error, setError] = useState('')
  const set = <K extends keyof SearchState>(k: K, v: SearchState[K]) => setS((p) => ({ ...p, [k]: v }))

  function submit(e: FormEvent) {
    e.preventDefault()
    if (showCity && !s.city.trim()) return setError('Укажите город')
    if (s.check_in < todayISO()) return setError('Дата заезда не может быть в прошлом')
    if (s.check_out <= s.check_in) return setError('Дата выезда должна быть позже заезда')
    setError('')
    onSubmit({ ...s, city: s.city.trim(), page: 1 })
  }

  return (
    <form onSubmit={submit}>
      <div className={`grid gap-1 rounded-2xl bg-white p-2 shadow-sm ${showCity ? 'lg:grid-cols-[1.6fr_1fr_1fr_.7fr_.7fr_auto]' : 'lg:grid-cols-[1fr_1fr_.7fr_.7fr_auto]'} sm:grid-cols-2`}>
        {showCity && (
          <label className={field}>
            <span className="text-xs text-muted">Куда</span>
            <input className={input} list="cities" placeholder="Город" value={s.city} onChange={(e) => set('city', e.target.value)} />
            <datalist id="cities">
              <option value="Москва" />
              <option value="Санкт-Петербург" />
              <option value="Казань" />
            </datalist>
          </label>
        )}
        <label className={field}>
          <span className="text-xs text-muted">Заезд</span>
          <input
            type="date" className={input} min={todayISO()} value={s.check_in}
            onChange={(e) => setS((p) => ({
              ...p, check_in: e.target.value,
              check_out: p.check_out <= e.target.value ? addDays(e.target.value, 1) : p.check_out,
            }))}
          />
        </label>
        <label className={field}>
          <span className="text-xs text-muted">Выезд</span>
          <input type="date" className={input} min={addDays(s.check_in, 1)} value={s.check_out} onChange={(e) => set('check_out', e.target.value)} />
        </label>
        <label className={field}>
          <span className="text-xs text-muted">Гости</span>
          <input type="number" className={input} min={1} max={100} value={s.guests_count} onChange={(e) => set('guests_count', Math.max(1, +e.target.value || 1))} />
        </label>
        <label className={field}>
          <span className="text-xs text-muted">Номера</span>
          <input type="number" className={input} min={1} max={20} value={s.rooms_count} onChange={(e) => set('rooms_count', Math.max(1, +e.target.value || 1))} />
        </label>
        <Button type="submit" size="lg" className="sm:col-span-2 lg:col-span-1">{submitText}</Button>
      </div>
      {error && <p className="mt-2 text-sm font-medium text-red-700" role="alert">{error}</p>}
    </form>
  )
}

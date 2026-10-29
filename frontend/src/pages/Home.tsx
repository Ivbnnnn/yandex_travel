import { useNavigate, useSearchParams } from 'react-router-dom'
import { SearchForm } from '../components/SearchForm'
import { parseSearch, toParams } from '../lib/search'

const CITIES = [
  ['Москва', 'Парки, музеи и поздние рестораны'],
  ['Санкт-Петербург', 'Белые ночи и набережные'],
  ['Казань', 'Кремль и татарская кухня'],
]

export default function Home() {
  const nav = useNavigate()
  const [sp] = useSearchParams()
  const initial = parseSearch(sp)
  return (
    <div className="pt-6 sm:pt-12">
      <h1 className="max-w-2xl text-4xl font-extrabold tracking-tight sm:text-5xl">Отели для любой поездки</h1>
      <p className="mt-3 max-w-xl text-lg text-muted">Выберите город и даты — покажем свободные номера и итоговую цену.</p>
      <div className="mt-8">
        <SearchForm initial={initial} onSubmit={(s) => nav(`/search?${toParams(s)}`)} />
      </div>
      <h2 className="mt-14 mb-4 text-2xl font-bold">Популярные направления</h2>
      <div className="grid gap-4 sm:grid-cols-3">
        {CITIES.map(([city, text], i) => (
          <button
            key={city}
            onClick={() => nav(`/search?${toParams({ ...initial, city })}`)}
            className="cursor-pointer rounded-2xl p-6 text-left transition-transform hover:-translate-y-0.5"
            style={{ background: `linear-gradient(135deg, hsl(${50 + i * 70} 90% 88%), hsl(${80 + i * 70} 80% 78%))` }}
          >
            <div className="text-xl font-bold">{city}</div>
            <div className="mt-1 text-sm text-ink/70">{text}</div>
          </button>
        ))}
      </div>
    </div>
  )
}

import type { Dec } from '../api/types'

export const num = (v: Dec | null | undefined) => Number(v ?? 0)

export const money = (v: Dec, currency = 'RUB') =>
  new Intl.NumberFormat('ru-RU', { style: 'currency', currency, maximumFractionDigits: 0 }).format(num(v))

const pad = (n: number) => String(n).padStart(2, '0')
export const toISO = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
export const todayISO = () => toISO(new Date())
const parts = (s: string) => s.split('-').map(Number) as [number, number, number]

export function addDays(iso: string, n: number) {
  const [y, m, d] = parts(iso)
  return toISO(new Date(y, m - 1, d + n))
}
export function nightsBetween(a: string, b: string) {
  const t = (s: string) => Date.UTC(...(([y, m, d]) => [y, m - 1, d] as [number, number, number])(parts(s)))
  return Math.round((t(b) - t(a)) / 86400000)
}
export function dateRu(iso: string, withYear = false) {
  const [y, m, d] = parts(iso)
  return new Date(y, m - 1, d).toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'short',
    ...(withYear ? { year: 'numeric' } : {}),
  })
}
export function plural(n: number, f: [string, string, string]) {
  const a = Math.abs(n) % 100
  const b = a % 10
  return a > 10 && a < 20 ? f[2] : b === 1 ? f[0] : b >= 2 && b <= 4 ? f[1] : f[2]
}
export const nightsText = (n: number) => `${n} ${plural(n, ['ночь', 'ночи', 'ночей'])}`

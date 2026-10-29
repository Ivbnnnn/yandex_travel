import {
  createContext, useCallback, useContext, useState,
  type ButtonHTMLAttributes, type ReactNode,
} from 'react'
import { ApiError } from './api/client'
import type { BookingStatus, Dec } from './api/types'
import { num } from './lib/format'

export const inputCls =
  'h-11 w-full rounded-xl border border-line bg-white px-3.5 text-[15px] outline-none transition-colors focus:border-ink'

type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
}
export function Button({ variant = 'primary', size = 'md', className = '', ...p }: BtnProps) {
  const v = {
    primary: 'bg-accent hover:bg-accent-hover text-ink',
    secondary: 'bg-surface-2 hover:bg-line text-ink',
    ghost: 'hover:bg-surface-2 text-ink',
    danger: 'bg-red-50 hover:bg-red-100 text-red-700',
  }[variant]
  const s = { sm: 'h-9 px-4 text-sm', md: 'h-11 px-5 text-[15px]', lg: 'h-14 px-7 text-base' }[size]
  return (
    <button
      {...p}
      className={`inline-flex cursor-pointer items-center justify-center gap-2 rounded-xl font-semibold whitespace-nowrap transition-colors disabled:pointer-events-none disabled:opacity-50 ${v} ${s} ${className}`}
    />
  )
}

export const Card = ({ className = '', children }: { className?: string; children: ReactNode }) => (
  <div className={`rounded-2xl bg-white ${className}`}>{children}</div>
)

export function Chip({ active, onClick, children }: { active?: boolean; onClick?: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`cursor-pointer rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors ${
        active ? 'bg-ink text-white' : 'bg-surface-2 text-ink hover:bg-line'
      }`}
    >
      {children}
    </button>
  )
}

export const Tag = ({ children }: { children: ReactNode }) => (
  <span className="rounded-md bg-surface-2 px-2 py-0.5 text-xs text-muted">{children}</span>
)

export const Spinner = () => (
  <div className="flex justify-center py-16" role="status" aria-label="Загрузка">
    <div className="size-8 animate-spin rounded-full border-[3px] border-line border-t-ink" />
  </div>
)

export function ErrorBox({ error }: { error: unknown }) {
  const msg = error instanceof ApiError ? error.message : 'Не удалось загрузить данные. Проверьте, что бэк запущен.'
  return <div className="rounded-2xl bg-red-50 p-5 text-red-800">{msg}</div>
}

export function Empty({ title, text, action }: { title: string; text?: string; action?: ReactNode }) {
  return (
    <div className="rounded-2xl bg-white px-6 py-14 text-center">
      <div className="text-lg font-semibold">{title}</div>
      {text && <p className="mx-auto mt-1 max-w-md text-muted">{text}</p>}
      {action && <div className="mt-5 flex justify-center">{action}</div>}
    </div>
  )
}

export function Rating({ value }: { value: Dec }) {
  const v = num(value)
  if (!v) return <span className="text-sm text-muted">Нет оценок</span>
  return (
    <span className="inline-flex items-center gap-1 rounded-lg bg-accent px-2 py-0.5 text-sm font-bold">
      <Star /> {v.toFixed(1)}
    </span>
  )
}

export function Photo({ src, seed, className = '', alt = '' }: { src?: string | null; seed: string; className?: string; alt?: string }) {
  const [bad, setBad] = useState(false)
  if (src && !bad) {
    return <img src={src} alt={alt} loading="lazy" onError={() => setBad(true)} className={`object-cover ${className}`} />
  }
  const h = [...seed].reduce((a, c) => (a * 31 + c.charCodeAt(0)) % 360, 7)
  return (
    <div
      aria-hidden
      className={`grid place-items-center text-4xl ${className}`}
      style={{ background: `linear-gradient(135deg, hsl(${h} 70% 90%), hsl(${(h + 50) % 360} 75% 80%))` }}
    >
      🏨
    </div>
  )
}

const STATUS: Record<BookingStatus, [string, string]> = {
  pending: ['Ожидает оплаты', 'bg-amber-100 text-amber-900'],
  paid: ['Оплачено', 'bg-green-100 text-green-800'],
  confirmed: ['Подтверждено', 'bg-green-100 text-green-800'],
  cancelled: ['Отменено', 'bg-surface-2 text-muted'],
  failed: ['Не оплачено', 'bg-red-100 text-red-800'],
}
export const StatusBadge = ({ status }: { status: BookingStatus }) => (
  <span className={`rounded-lg px-2.5 py-1 text-sm font-semibold ${STATUS[status][1]}`}>{STATUS[status][0]}</span>
)

const ico = { width: 18, height: 18, viewBox: '0 0 24 24', 'aria-hidden': true } as const
export const Star = () => (
  <svg {...ico} width={14} height={14} fill="currentColor"><path d="m12 2 3.1 6.3 6.9 1-5 4.9 1.2 6.8-6.2-3.3-6.2 3.3L8 14.2 3 9.3l6.9-1z" /></svg>
)
export const Heart = ({ filled }: { filled?: boolean }) => (
  <svg {...ico} width={22} height={22} fill={filled ? '#e5484d' : 'none'} stroke={filled ? '#e5484d' : 'currentColor'} strokeWidth={2}>
    <path d="M12 21s-7.5-4.6-9.5-9.2C1.2 8.6 3 5 6.5 5c2 0 3.5 1.1 5.5 3 2-1.9 3.5-3 5.5-3C21 5 22.8 8.6 21.5 11.8 19.5 16.4 12 21 12 21z" />
  </svg>
)
export const Pin = () => (
  <svg {...ico} width={16} height={16} fill="none" stroke="currentColor" strokeWidth={2}><path d="M12 22s7-6.2 7-12a7 7 0 1 0-14 0c0 5.8 7 12 7 12z" /><circle cx="12" cy="10" r="2.5" /></svg>
)

// ---- уведомления ----
const ToastCtx = createContext<(msg: string, kind?: 'ok' | 'error') => void>(() => {})
export const useToast = () => useContext(ToastCtx)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<{ id: number; msg: string; kind: string }[]>([])
  const push = useCallback((msg: string, kind: 'ok' | 'error' = 'ok') => {
    const id = Math.random()
    setItems((x) => [...x, { id, msg, kind }])
    setTimeout(() => setItems((x) => x.filter((i) => i.id !== id)), 5000)
  }, [])
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="fixed right-4 bottom-4 z-50 flex max-w-sm flex-col gap-2" aria-live="polite">
        {items.map((i) => (
          <div key={i.id} className={`rounded-xl px-4 py-3 text-sm font-medium shadow-lg ${i.kind === 'error' ? 'bg-red-600 text-white' : 'bg-ink text-white'}`}>
            {i.msg}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  )
}

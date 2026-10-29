import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api, errMsg } from '../api/client'
import { useBooking } from '../api/hooks'
import type { Booking, Payment } from '../api/types'
import { dateRu, money, nightsBetween, nightsText } from '../lib/format'
import { Button, Card, ErrorBox, Spinner, StatusBadge, useToast } from '../ui'

type Token = 'success' | 'fail' | 'timeout'
const TOKENS: [Token, string, string][] = [
  ['success', 'Успешная оплата', 'Платёж пройдёт сразу'],
  ['fail', 'Отказ банка', 'Платёж отклонят, номер останется за вами до конца таймера'],
  ['timeout', 'Долгое подтверждение', 'Статус «в обработке», подтверждение придёт через пару секунд'],
]

function useCountdown(iso: string, onEnd: () => void) {
  const end = new Date(iso).getTime()
  const [left, setLeft] = useState(Math.max(0, end - Date.now()))
  const fired = useRef(false)
  useEffect(() => {
    const t = setInterval(() => {
      const l = Math.max(0, end - Date.now())
      setLeft(l)
      if (l === 0 && !fired.current) {
        fired.current = true
        onEnd()
      }
    }, 1000)
    return () => clearInterval(t)
  })
  const s = Math.ceil(left / 1000)
  return { left, text: `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}` }
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))

function PayPanel({ booking }: { booking: Booking }) {
  const qc = useQueryClient()
  const toast = useToast()
  const [token, setToken] = useState<Token>('success')
  const [note, setNote] = useState('')
  const refetch = () => {
    qc.invalidateQueries({ queryKey: ['booking', booking.booking_id] })
    qc.invalidateQueries({ queryKey: ['bookings'] })
  }
  const timer = useCountdown(booking.expires_at, refetch)

  const pay = useMutation({
    mutationFn: async () => {
      setNote('')
      // у каждой попытки свой Idempotency-Key: тот же ключ с другим телом даст 409
      let p = await api<Payment>('/payments', {
        method: 'POST',
        body: { booking_id: booking.booking_id, payment_method: 'demo', payment_token: token },
        idempotencyKey: crypto.randomUUID(),
      })
      // 202 / pending: опрашиваем статус платежа
      for (let i = 0; p.status === 'pending' && i < 20; i++) {
        setNote('Платёж обрабатывается…')
        await sleep(1000)
        p = await api<Payment>(`/payments/${p.payment_id}`)
      }
      return p
    },
    onSuccess: (p) => {
      if (p.status === 'failed') toast('Платёж отклонён. Можно попробовать ещё раз', 'error')
      else toast('Оплата прошла, бронь подтверждена')
      setNote('')
      refetch()
    },
    onError: (e) => {
      setNote('')
      toast(errMsg(e), 'error')
      refetch()
    },
  })

  return (
    <Card className="space-y-4 p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-xl font-bold">Оплата</h2>
        <span className="rounded-lg bg-amber-100 px-3 py-1 text-sm font-semibold text-amber-900">Номер удерживается ещё {timer.text}</span>
      </div>
      <p className="text-sm text-muted">Демо-режим: деньги не списываются, данные карты не нужны. Выберите, как «пройдёт» платёж.</p>
      <div className="grid gap-2 sm:grid-cols-3">
        {TOKENS.map(([v, title, text]) => (
          <label key={v} className={`cursor-pointer rounded-xl border-2 p-3 transition-colors ${token === v ? 'border-ink' : 'border-line hover:border-muted'}`}>
            <input type="radio" name="token" className="sr-only" checked={token === v} onChange={() => setToken(v)} />
            <div className="font-semibold">{title}</div>
            <div className="mt-0.5 text-xs text-muted">{text}</div>
          </label>
        ))}
      </div>
      <Button size="lg" className="w-full sm:w-auto" disabled={pay.isPending || timer.left === 0} onClick={() => pay.mutate()}>
        {pay.isPending ? note || 'Оплачиваем…' : `Оплатить ${money(booking.total_price, booking.currency)}`}
      </Button>
    </Card>
  )
}

export default function BookingPage() {
  const { id = '' } = useParams()
  const q = useBooking(id)
  const qc = useQueryClient()
  const toast = useToast()
  const cancel = useMutation({
    mutationFn: () => api<Booking>(`/bookings/${id}/cancel`, { method: 'POST' }),
    onSuccess: () => {
      toast('Бронь отменена')
      qc.invalidateQueries({ queryKey: ['booking', id] })
      qc.invalidateQueries({ queryKey: ['bookings'] })
    },
    onError: (e) => toast(errMsg(e), 'error'),
  })
  if (q.isLoading) return <Spinner />
  if (q.isError) return <ErrorBox error={q.error} />
  const b = q.data!
  const sn = b.snapshot
  const canPay = b.status === 'pending' && new Date(b.expires_at) > new Date()
  const refunded = b.payments?.some((p) => p.status === 'refunded')

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-3xl font-extrabold tracking-tight">
          {b.status === 'confirmed' ? 'Бронь подтверждена' : 'Бронирование'}
        </h1>
        <StatusBadge status={b.status} />
      </div>
      <Card className="space-y-3 p-6">
        <div className="text-sm text-muted">Номер брони: {b.booking_id}</div>
        <div className="text-xl font-bold">{sn.hotel_name}</div>
        <div className="text-muted">{sn.address}</div>
        <div className="grid gap-1 pt-2">
          <div>{sn.room_name}, тариф «{sn.rate_name}»</div>
          <div>{dateRu(b.check_in, true)} — {dateRu(b.check_out, true)} · {nightsText(nightsBetween(b.check_in, b.check_out))}</div>
          <div>{b.guests_count} гост., {b.rooms_count} ном.</div>
          <div className="text-sm text-muted">{sn.cancellation_policy}</div>
        </div>
        <div className="flex items-end justify-between border-t border-line pt-3">
          <span className="text-muted">Итого</span>
          <span className="text-2xl font-extrabold">{money(b.total_price, b.currency)}</span>
        </div>
        {refunded && <p className="text-sm text-muted">Оплата возвращена (демо-возврат).</p>}
      </Card>

      {canPay && <PayPanel booking={b} />}
      {b.status === 'pending' && !canPay && <ErrorBox error={new Error('Время удержания номера истекло. Выберите номер заново.')} />}
      {b.status === 'failed' && <ErrorBox error={new Error('Бронь не была оплачена вовремя и закрыта.')} />}

      <div className="flex flex-wrap gap-3">
        <Link to="/bookings"><Button variant="secondary">Все мои брони</Button></Link>
        {(b.status === 'confirmed' || b.status === 'pending') && (
          <Button variant="danger" disabled={cancel.isPending} onClick={() => confirm('Отменить бронь?') && cancel.mutate()}>Отменить бронь</Button>
        )}
      </div>
    </div>
  )
}

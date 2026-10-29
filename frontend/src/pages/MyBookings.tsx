import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api, errMsg } from '../api/client'
import { useMyBookings } from '../api/hooks'
import type { Booking } from '../api/types'
import { dateRu, money, todayISO } from '../lib/format'
import { Button, Card, Empty, ErrorBox, Spinner, StatusBadge, inputCls, useToast } from '../ui'

function ReviewForm({ b, onDone }: { b: Booking; onDone: () => void }) {
  const toast = useToast()
  const qc = useQueryClient()
  const [rating, setRating] = useState(5)
  const [text, setText] = useState('')
  const m = useMutation({
    mutationFn: () => api(`/hotels/${b.hotel_id}/reviews`, { method: 'POST', body: { booking_id: b.booking_id, rating, text } }),
    onSuccess: () => { toast('Спасибо за отзыв!'); qc.invalidateQueries({ queryKey: ['hotel'] }); onDone() },
    onError: (e) => toast(errMsg(e), 'error'),
  })
  return (
    <div className="mt-4 space-y-3 border-t border-line pt-4">
      <div className="flex gap-1" role="radiogroup" aria-label="Оценка">
        {[1, 2, 3, 4, 5].map((n) => (
          <button key={n} type="button" aria-label={`${n} из 5`} onClick={() => setRating(n)} className={`cursor-pointer text-3xl ${n <= rating ? 'text-accent-hover' : 'text-line'}`}>★</button>
        ))}
      </div>
      <textarea className={`${inputCls} h-24 py-2`} placeholder="Как прошла поездка?" value={text} onChange={(e) => setText(e.target.value)} maxLength={3000} />
      <Button size="sm" disabled={!text.trim() || m.isPending} onClick={() => m.mutate()}>Отправить отзыв</Button>
    </div>
  )
}

export default function MyBookings() {
  const q = useMyBookings()
  const [reviewing, setReviewing] = useState('')
  if (q.isLoading) return <Spinner />
  if (q.isError) return <ErrorBox error={q.error} />
  const items = [...q.data!.items].reverse()
  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-extrabold tracking-tight">Мои брони</h1>
      {items.length === 0 ? (
        <Empty title="Броней пока нет" text="Найдите отель и забронируйте номер — история появится здесь." action={<Link to="/"><Button>Найти отель</Button></Link>} />
      ) : (
        items.map((b) => (
          <Card key={b.booking_id} className="p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <Link to={`/bookings/${b.booking_id}`} className="text-lg font-bold hover:underline">{b.snapshot.hotel_name}</Link>
                <div className="text-sm text-muted">{b.snapshot.room_name} · {dateRu(b.check_in, true)} — {dateRu(b.check_out, true)}</div>
              </div>
              <div className="flex items-center gap-3">
                <span className="font-bold">{money(b.total_price, b.currency)}</span>
                <StatusBadge status={b.status} />
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <Link to={`/bookings/${b.booking_id}`}><Button size="sm" variant="secondary">{b.status === 'pending' ? 'Оплатить' : 'Подробнее'}</Button></Link>
              {b.status === 'confirmed' && b.check_out <= todayISO() && (
                <Button size="sm" variant="secondary" onClick={() => setReviewing(reviewing === b.booking_id ? '' : b.booking_id)}>Оставить отзыв</Button>
              )}
            </div>
            {reviewing === b.booking_id && <ReviewForm b={b} onDone={() => setReviewing('')} />}
          </Card>
        ))
      )}
    </div>
  )
}

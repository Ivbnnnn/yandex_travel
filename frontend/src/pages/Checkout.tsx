import { Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { api, errMsg, idemKey } from '../api/client'
import { useHotel } from '../api/hooks'
import type { Booking } from '../api/types'
import { dateRu, money, nightsBetween, nightsText, num } from '../lib/format'
import { Button, Card, ErrorBox, Spinner, useToast } from '../ui'

export default function Checkout() {
  const [sp] = useSearchParams()
  const nav = useNavigate()
  const toast = useToast()
  const hotelId = sp.get('hotel') ?? ''
  const roomId = sp.get('room') ?? ''
  const rateId = sp.get('rate') ?? ''
  const check_in = sp.get('check_in') ?? ''
  const check_out = sp.get('check_out') ?? ''
  const guests_count = Number(sp.get('guests_count') ?? 1)
  const rooms_count = Number(sp.get('rooms_count') ?? 1)
  const valid = hotelId && roomId && rateId && check_in && check_out
  // Цена и доступность каждый раз запрашиваются с сервера
  const q = useHotel(hotelId, new URLSearchParams({ check_in, check_out, guests_count: String(guests_count), rooms_count: String(rooms_count) }).toString())

  const book = useMutation({
    mutationFn: async () => {
      const body = { hotel_id: hotelId, room_id: roomId, rate_id: rateId, check_in, check_out, guests_count, rooms_count }
      const post = (fresh: boolean) =>
        api<Booking>('/bookings', { method: 'POST', body, idempotencyKey: idemKey('booking', body, fresh) })
      let b = await post(false)
      // тот же ключ мог вернуть старую (истёкшую/отменённую) бронь — создаём новую
      if (b.status !== 'pending') b = await post(true)
      return b
    },
    onSuccess: (b) => nav(`/bookings/${b.booking_id}`),
    onError: (e) => toast(errMsg(e), 'error'),
  })

  if (!valid) return <Navigate to="/" replace />
  if (q.isLoading) return <Spinner />
  if (q.isError) return <ErrorBox error={q.error} />
  const hotel = q.data!
  const room = hotel.rooms.find((r) => r.room_id === roomId)
  const rate = room?.rates.find((r) => r.rate_id === rateId)
  if (!room || !rate) return <ErrorBox error={null} />

  const nights = nightsBetween(check_in, check_out)
  const total = num(rate.price) * nights * rooms_count
  const problem = !room.can_book ? 'Номер больше недоступен на эти даты или не вмещает всех гостей. Вернитесь и выберите другой вариант.' : ''

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <h1 className="text-3xl font-extrabold tracking-tight">Проверьте бронирование</h1>
      <Card className="space-y-4 p-6">
        <div>
          <div className="text-xl font-bold">{hotel.name}</div>
          <div className="text-muted">{hotel.address}</div>
        </div>
        <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
          <Row k="Номер" v={room.name} />
          <Row k="Тариф" v={rate.name} />
          <Row k="Заезд" v={dateRu(check_in, true)} />
          <Row k="Выезд" v={dateRu(check_out, true)} />
          <Row k="Срок" v={nightsText(nights)} />
          <Row k="Гости и номера" v={`${guests_count} гост., ${rooms_count} ном.`} />
          <Row k="Питание" v={rate.breakfast_included ? 'Завтрак включён' : 'Без питания'} />
          <Row k="Отмена" v={rate.cancellation_policy} />
        </dl>
        <div className="flex items-end justify-between border-t border-line pt-4">
          <div className="text-muted">{money(rate.price, rate.currency)} × {nights} × {rooms_count}</div>
          <div className="text-3xl font-extrabold">{money(total, rate.currency)}</div>
        </div>
      </Card>
      {problem && <ErrorBox error={new Error(problem)} />}
      <p className="text-sm text-muted">После нажатия номер закрепляется за вами на 15 минут — за это время нужно оплатить.</p>
      <Button size="lg" className="w-full sm:w-auto" disabled={!!problem || book.isPending} onClick={() => book.mutate()}>
        {book.isPending ? 'Бронируем…' : 'Забронировать и перейти к оплате'}
      </Button>
    </div>
  )
}

const Row = ({ k, v }: { k: string; v: string }) => (
  <div><dt className="text-sm text-muted">{k}</dt><dd className="font-semibold">{v}</dd></div>
)

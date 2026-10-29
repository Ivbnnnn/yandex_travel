import { Link } from 'react-router-dom'
import { useFavorites } from '../api/hooks'
import { FavButton } from '../components/HotelCard'
import { Button, Empty, ErrorBox, Photo, Pin, Rating, Spinner } from '../ui'

export default function Favorites() {
  const q = useFavorites()
  if (q.isLoading) return <Spinner />
  if (q.isError) return <ErrorBox error={q.error} />
  const items = q.data!.items
  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-extrabold tracking-tight">Избранное</h1>
      {items.length === 0 ? (
        <Empty title="Здесь пока пусто" text="Нажмите на сердечко у отеля, чтобы он появился в этом списке." action={<Link to="/"><Button>Найти отель</Button></Link>} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map(({ favorite_id, hotel: h }) => (
            <article key={favorite_id} className="overflow-hidden rounded-2xl bg-white">
              <div className="relative">
                <Link to={`/hotels/${h.hotel_id}`}><Photo seed={h.hotel_id} alt={h.name} className="h-44 w-full" /></Link>
                <div className="absolute top-3 right-3"><FavButton hotelId={h.hotel_id} /></div>
              </div>
              <div className="space-y-1.5 p-4">
                <Link to={`/hotels/${h.hotel_id}`} className="text-lg font-bold hover:underline">{h.name}</Link>
                <Rating value={h.rating} />
                <p className="flex items-center gap-1 text-sm text-muted"><Pin /> {h.address}</p>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  )
}

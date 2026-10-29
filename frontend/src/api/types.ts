// Типы выведены из app/services/* бэка: public() переименовывает id в hotel_id, room_id и т.д.
// Decimal может прийти числом или строкой — читаем через num().
export type Dec = number | string

export interface User {
  user_id: string
  email: string
  name: string
  phone: string | null
  role: 'user' | 'admin'
  notifications_enabled: boolean
}
export interface Photo { photo_id: string; url: string; sort_order: number }
export interface Hotel {
  hotel_id: string
  name: string
  description: string
  city: string
  address: string
  latitude: Dec | null
  longitude: Dec | null
  rating: Dec
  tags: string[]
}
export interface HotelListItem extends Hotel {
  min_price: Dec
  currency: string
  preview_photo_url: string | null
}
export interface SearchResult { items: HotelListItem[]; total: number; page: number; limit: number }
export interface Rate {
  rate_id: string
  room_id: string
  name: string
  price: Dec
  currency: string
  breakfast_included: boolean
  cancellation_policy: string
  conditions: Record<string, unknown>
}
export interface Room {
  room_id: string
  hotel_id: string
  name: string
  description: string
  capacity: number
  stock: number
  price: Dec
  tags: string[]
  interior_styles: string[]
  booking_purposes: string[]
  rates: Rate[]
  photos: Photo[]
  available_count: number | null
  can_book: boolean
}
export interface Review {
  review_id: string
  user_id: string
  hotel_id: string
  booking_id: string
  rating: number
  text: string
  created_at: string
}
export interface HotelDetail extends Hotel { rooms: Room[]; photos: Photo[]; reviews: Review[] }
export interface FilterOption { id: string; kind: string; code: string; name: string }
export interface Filters { interior_styles: FilterOption[]; booking_purposes: FilterOption[] }

export type BookingStatus = 'pending' | 'paid' | 'confirmed' | 'cancelled' | 'failed'
export interface Payment {
  payment_id: string
  booking_id: string
  amount: Dec
  status: 'pending' | 'success' | 'failed' | 'refunded'
  payment_method: string
}
export interface Booking {
  booking_id: string
  hotel_id: string
  room_id: string
  rate_id: string
  check_in: string
  check_out: string
  guests_count: number
  rooms_count: number
  total_price: Dec
  currency: string
  status: BookingStatus
  expires_at: string
  snapshot: {
    hotel_name: string
    address: string
    room_name: string
    rate_name: string
    price_per_night: string
    cancellation_policy: string
    breakfast_included: boolean
  }
  payments?: Payment[]
}
export interface Favorite { favorite_id: string; hotel_id: string; hotel: Hotel }
export interface Notification {
  notification_id: string
  booking_id: string
  type: string
  message: string
  sent_at: string
  read_at: string | null
}

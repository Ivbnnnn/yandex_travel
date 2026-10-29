import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { api } from './client'
import type { Booking, Favorite, Filters, HotelDetail, Notification, SearchResult } from './types'
import { useAuth } from '../auth'

export const useFilters = () =>
  useQuery({ queryKey: ['filters'], queryFn: () => api<Filters>('/filters'), staleTime: Infinity })

export const useSearch = (qs: string, enabled: boolean) =>
  useQuery({
    queryKey: ['search', qs],
    queryFn: () => api<SearchResult>(`/hotels/search?${qs}&limit=20`),
    enabled,
    placeholderData: keepPreviousData,
  })

export const useHotel = (id: string, qs: string) =>
  useQuery({ queryKey: ['hotel', id, qs], queryFn: () => api<HotelDetail>(`/hotels/${id}?${qs}`) })

export const useBooking = (id: string) =>
  useQuery({ queryKey: ['booking', id], queryFn: () => api<Booking>(`/bookings/${id}`) })

export const useMyBookings = () =>
  useQuery({ queryKey: ['bookings'], queryFn: () => api<{ items: Booking[] }>('/users/me/bookings') })

export const useNotifications = () =>
  useQuery({
    queryKey: ['notifications'],
    queryFn: () => api<{ items: Notification[] }>('/users/me/notifications'),
  })

export function useFavorites() {
  const { user } = useAuth()
  return useQuery({
    queryKey: ['favorites'],
    queryFn: () => api<{ items: Favorite[] }>('/users/me/favorites'),
    enabled: !!user,
  })
}

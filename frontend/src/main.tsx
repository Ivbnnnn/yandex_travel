import '@fontsource-variable/inter'
import './index.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createBrowserRouter } from 'react-router-dom'
import { ApiError } from './api/client'
import { AuthProvider } from './auth'
import { CompareProvider } from './compare'
import { ToastProvider } from './ui'
import { Layout, RequireAuth } from './components/Layout'
import Home from './pages/Home'
import Search from './pages/Search'
import HotelPage from './pages/Hotel'
import Login from './pages/Login'
import Compare from './pages/Compare'
import Checkout from './pages/Checkout'
import BookingPage from './pages/Booking'
import MyBookings from './pages/MyBookings'
import Favorites from './pages/Favorites'
import Profile from './pages/Profile'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: (n, e) => !(e instanceof ApiError && e.status < 500) && n < 2,
    },
  },
})

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { index: true, element: <Home /> },
      { path: 'search', element: <Search /> },
      { path: 'hotels/:id', element: <HotelPage /> },
      { path: 'compare', element: <Compare /> },
      { path: 'login', element: <Login /> },
      {
        element: <RequireAuth />,
        children: [
          { path: 'checkout', element: <Checkout /> },
          { path: 'bookings', element: <MyBookings /> },
          { path: 'bookings/:id', element: <BookingPage /> },
          { path: 'favorites', element: <Favorites /> },
          { path: 'profile', element: <Profile /> },
        ],
      },
    ],
  },
])

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <AuthProvider>
          <CompareProvider>
            <RouterProvider router={router} />
          </CompareProvider>
        </AuthProvider>
      </ToastProvider>
    </QueryClientProvider>
  </StrictMode>,
)

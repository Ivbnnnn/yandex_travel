import { createContext, useContext, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError, api } from './api/client'
import type { User } from './api/types'

interface AuthValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (d: { email: string; password: string; name: string; phone?: string | null }) => Promise<void>
  logout: () => Promise<void>
}
const Ctx = createContext<AuthValue>(null!)
export const useAuth = () => useContext(Ctx)

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient()
  // Статус «залогинен» определяем запросом /users/me: 401 = гость
  const me = useQuery({
    queryKey: ['me'],
    queryFn: async () => {
      try {
        return await api<User>('/users/me')
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) return null
        throw e
      }
    },
    retry: false,
    staleTime: Infinity,
  })

  const resetUserData = () =>
    qc.removeQueries({ predicate: (q) => q.queryKey[0] !== 'me' && q.queryKey[0] !== 'filters' })

  const login = async (email: string, password: string) => {
    const user = await api<User>('/auth/login', { method: 'POST', body: { email, password } })
    resetUserData()
    qc.setQueryData(['me'], user)
  }
  const register: AuthValue['register'] = async (d) => {
    await api('/auth/register', { method: 'POST', body: { ...d, phone: d.phone || null } })
    await login(d.email, d.password)
  }
  const logout = async () => {
    try {
      await api('/auth/logout', { method: 'POST' })
    } finally {
      resetUserData()
      qc.setQueryData(['me'], null)
    }
  }

  return (
    <Ctx.Provider value={{ user: me.data ?? null, loading: me.isLoading, login, register, logout }}>
      {children}
    </Ctx.Provider>
  )
}

import { useState, type FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api, errMsg } from '../api/client'
import { useNotifications } from '../api/hooks'
import type { User } from '../api/types'
import { useAuth } from '../auth'
import { Button, Card, Spinner, inputCls, useToast } from '../ui'

export default function Profile() {
  const { user } = useAuth()
  const qc = useQueryClient()
  const toast = useToast()
  const [f, setF] = useState({ name: user!.name, phone: user!.phone ?? '', notifications_enabled: user!.notifications_enabled })
  const save = useMutation({
    mutationFn: () => api<User>('/users/me', { method: 'PATCH', body: { ...f, phone: f.phone || null } }),
    onSuccess: (u) => { qc.setQueryData(['me'], u); toast('Профиль сохранён') },
    onError: (e) => toast(errMsg(e), 'error'),
  })
  const notes = useNotifications()
  const read = useMutation({
    mutationFn: (id: string) => api(`/notifications/${id}/read`, { method: 'PATCH' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }),
  })
  const submit = (e: FormEvent) => { e.preventDefault(); save.mutate() }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-3xl font-extrabold tracking-tight">Профиль</h1>
      <form onSubmit={submit} className="space-y-3 rounded-2xl bg-white p-6">
        <div className="text-sm text-muted">{user!.email}</div>
        <input className={inputCls} required placeholder="Имя" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
        <input className={inputCls} type="tel" placeholder="Телефон" value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value })} />
        <label className="flex cursor-pointer items-center gap-2">
          <input type="checkbox" className="size-4 accent-black" checked={f.notifications_enabled} onChange={(e) => setF({ ...f, notifications_enabled: e.target.checked })} />
          Присылать уведомления о бронировании
        </label>
        <Button type="submit" disabled={save.isPending}>Сохранить</Button>
      </form>

      <h2 className="text-2xl font-bold">Уведомления</h2>
      {notes.isLoading ? <Spinner /> : notes.data?.items.length === 0 ? (
        <p className="text-muted">Уведомлений пока нет.</p>
      ) : (
        <div className="space-y-2">
          {notes.data?.items.map((n) => (
            <Card key={n.notification_id} className={`flex items-center justify-between gap-3 p-4 ${n.read_at ? 'opacity-60' : ''}`}>
              <div>
                <div>{n.message}</div>
                <div className="text-xs text-muted">{new Date(n.sent_at).toLocaleString('ru-RU')}</div>
              </div>
              {!n.read_at && <Button size="sm" variant="secondary" onClick={() => read.mutate(n.notification_id)}>Прочитано</Button>}
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

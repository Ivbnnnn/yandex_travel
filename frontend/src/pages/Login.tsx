import { useState, type FormEvent } from 'react'
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { errMsg } from '../api/client'
import { useAuth } from '../auth'
import { Button, inputCls } from '../ui'

export default function Login() {
  const { user, login, register } = useAuth()
  const nav = useNavigate()
  const [sp] = useSearchParams()
  const next = sp.get('next')?.startsWith('/') ? sp.get('next')! : '/'
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [f, setF] = useState({ email: '', password: '', name: '', phone: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  if (user) return <Navigate to={next} replace />

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      if (mode === 'login') await login(f.email, f.password)
      else await register(f)
      nav(next, { replace: true })
    } catch (err) {
      setError(errMsg(err))
    } finally {
      setBusy(false)
    }
  }
  const bind = (k: keyof typeof f) => ({ value: f[k], onChange: (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value }) })

  return (
    <div className="mx-auto max-w-md pt-6">
      <div className="mb-5 grid grid-cols-2 gap-1 rounded-xl bg-surface-2 p-1">
        {(['login', 'register'] as const).map((m) => (
          <button key={m} onClick={() => setMode(m)} className={`h-10 cursor-pointer rounded-lg font-semibold ${mode === m ? 'bg-white shadow-sm' : 'text-muted'}`}>
            {m === 'login' ? 'Вход' : 'Регистрация'}
          </button>
        ))}
      </div>
      <form onSubmit={submit} className="space-y-3 rounded-2xl bg-white p-6">
        <h1 className="text-2xl font-bold">{mode === 'login' ? 'Войти в аккаунт' : 'Создать аккаунт'}</h1>
        {mode === 'register' && <input className={inputCls} required placeholder="Имя" {...bind('name')} />}
        <input className={inputCls} type="email" required placeholder="Email" autoComplete="email" {...bind('email')} />
        <input
          className={inputCls} type="password" required minLength={mode === 'register' ? 8 : 1}
          placeholder={mode === 'register' ? 'Пароль (от 8 символов)' : 'Пароль'}
          autoComplete={mode === 'login' ? 'current-password' : 'new-password'} {...bind('password')}
        />
        {mode === 'register' && <input className={inputCls} type="tel" placeholder="Телефон (необязательно)" {...bind('phone')} />}
        {error && <p className="text-sm font-medium text-red-700" role="alert">{error}</p>}
        <Button type="submit" size="lg" className="w-full" disabled={busy}>
          {busy ? 'Подождите…' : mode === 'login' ? 'Войти' : 'Зарегистрироваться'}
        </Button>
      </form>
    </div>
  )
}

import { Link, NavLink, Outlet, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { useCompare } from '../compare'
import { Button, Spinner } from '../ui'

export function Layout() {
  const { user, logout } = useAuth()
  const { ids, clear } = useCompare()
  const nav = useNavigate()
  const link = ({ isActive }: { isActive: boolean }) =>
    `rounded-lg px-3 py-2 text-[15px] font-medium transition-colors hover:bg-surface-2 ${isActive ? 'bg-surface-2' : ''}`
  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b border-line bg-white">
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-2 px-4">
          <Link to="/" className="mr-4 flex items-center gap-2 text-lg font-extrabold tracking-tight">
            <span className="grid size-8 place-items-center rounded-lg bg-accent">П</span>
            Путешествия
          </Link>
          <nav className="flex flex-1 items-center gap-1">
            <NavLink to="/favorites" className={link}>Избранное</NavLink>
            <NavLink to="/bookings" className={link}>Мои брони</NavLink>
          </nav>
          {user ? (
            <>
              <NavLink to="/profile" className={link}>{user.name}</NavLink>
              <Button variant="secondary" size="sm" onClick={() => logout().then(() => nav('/'))}>Выйти</Button>
            </>
          ) : (
            <Button size="sm" onClick={() => nav('/login')}>Войти</Button>
          )}
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">
        <Outlet />
      </main>
      {ids.length > 0 && (
        <div className="sticky bottom-4 z-30 mx-auto mb-4 flex w-fit items-center gap-3 rounded-2xl bg-ink px-5 py-3 text-white shadow-xl">
          <span className="text-sm">Выбрано для сравнения: {ids.length} из 3</span>
          <Button size="sm" disabled={ids.length < 2} onClick={() => nav('/compare')}>Сравнить</Button>
          <button className="cursor-pointer text-sm text-white/70 hover:text-white" onClick={clear}>Сбросить</button>
        </div>
      )}
      <footer className="border-t border-line bg-white py-6 text-center text-sm text-muted">
        Учебный проект. Оплата демонстрационная — деньги не списываются.
      </footer>
    </div>
  )
}

// Закрытые страницы: гостя отправляем на вход и возвращаем обратно (выбор номера лежит в URL)
export function RequireAuth() {
  const { user, loading } = useAuth()
  const loc = useLocation()
  if (loading) return <Spinner />
  if (!user) return <Navigate to={`/login?next=${encodeURIComponent(loc.pathname + loc.search)}`} replace />
  return <Outlet />
}

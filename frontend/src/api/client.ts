const BASE = '/api/v1'

export interface FieldError { loc: (string | number)[]; msg: string }

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public fields?: FieldError[],
  ) {
    super(message)
  }
}

// csrf_token — не httpOnly cookie, бэк требует то же значение в заголовке X-CSRF-Token
const csrf = () => {
  const m = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/)
  return m ? decodeURIComponent(m[1]) : ''
}

// Refresh ротирует токен: параллельные 401 должны делить один запрос refresh
let refreshing: Promise<boolean> | null = null
function refresh(): Promise<boolean> {
  refreshing ??= fetch(`${BASE}/auth/refresh`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'X-CSRF-Token': csrf() },
  })
    .then((r) => r.ok)
    .catch(() => false)
    .finally(() => {
      refreshing = null
    })
  return refreshing
}

export interface Req {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  body?: unknown
  idempotencyKey?: string
}

export async function api<T>(path: string, o: Req = {}, retried = false): Promise<T> {
  const method = o.method ?? 'GET'
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (o.body !== undefined) headers['Content-Type'] = 'application/json'
  if (method !== 'GET') headers['X-CSRF-Token'] = csrf()
  if (o.idempotencyKey) headers['Idempotency-Key'] = o.idempotencyKey

  const res = await fetch(BASE + path, {
    method,
    headers,
    credentials: 'include',
    body: o.body !== undefined ? JSON.stringify(o.body) : undefined,
  })

  // access жив 15 минут: на 401 один раз обновляем токены и повторяем запрос
  if (res.status === 401 && !retried && !path.startsWith('/auth/') && csrf() && (await refresh())) {
    return api<T>(path, o, true)
  }

  if (!res.ok) {
    const e = await res.json().catch(() => ({}))
    throw new ApiError(
      res.status,
      e.code ?? 'error',
      typeof e.detail === 'string' ? e.detail : res.statusText,
      e.errors,
    )
  }
  return (res.status === 204 ? undefined : await res.json()) as T
}

export function errMsg(e: unknown): string {
  if (e instanceof ApiError) {
    const first = e.fields?.[0]
    return first ? `${first.loc.slice(1).join('.')}: ${first.msg}` : e.message
  }
  return 'Не удалось выполнить запрос. Проверьте, что бэк запущен.'
}

// Один и тот же запрос брони → тот же Idempotency-Key (повтор не создаст дубль)
export function idemKey(scope: string, body: unknown, fresh = false): string {
  const k = `idem:${scope}:${JSON.stringify(body)}`
  let v = fresh ? null : sessionStorage.getItem(k)
  if (!v) {
    v = crypto.randomUUID()
    sessionStorage.setItem(k, v)
  }
  return v
}

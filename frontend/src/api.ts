import { useAuth } from './store'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T = any>(method: string, path: string, body?: unknown, isForm = false): Promise<T> {
  const token = useAuth.getState().token
  const headers: Record<string, string> = {}
  if (token) headers.Authorization = `Bearer ${token}`
  let payload: BodyInit | undefined
  if (isForm) {
    payload = new URLSearchParams(body as Record<string, string>)
    headers['Content-Type'] = 'application/x-www-form-urlencoded'
  } else if (body !== undefined) {
    payload = JSON.stringify(body)
    headers['Content-Type'] = 'application/json'
  }
  const r = await fetch(`/api${path}`, { method, headers, body: payload })
  if (r.status === 401 && path !== '/auth/login') {
    useAuth.getState().logout()
  }
  if (!r.ok) {
    let msg = r.statusText
    try {
      const j = await r.json()
      msg = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail)
    } catch {
      /* ignore */
    }
    throw new ApiError(r.status, msg)
  }
  const ct = r.headers.get('content-type') || ''
  return (ct.includes('application/json') ? r.json() : (r.blob() as any)) as T
}

export const api = {
  get: <T = any>(p: string) => request<T>('GET', p),
  post: <T = any>(p: string, b?: unknown) => request<T>('POST', p, b),
  put: <T = any>(p: string, b?: unknown) => request<T>('PUT', p, b),
  del: <T = any>(p: string) => request<T>('DELETE', p),
  login: (username: string, password: string) =>
    request<{ access_token: string }>('POST', '/auth/login', { username, password }, true),
}

export async function download(path: string, filename: string, body?: unknown) {
  const blob: Blob = await request(body === undefined ? 'GET' : 'POST', path, body)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

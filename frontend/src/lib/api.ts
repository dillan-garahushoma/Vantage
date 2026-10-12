import type { RegisterRequest } from './contract'
import type { AuthResponse, CurrentUser, EstateAccessList } from './types'

/**
 * Thin typed wrapper around the VALORA API.
 *
 * Two rules this file exists to enforce:
 *  1. The JWT is the only proof of identity — never a client-supplied user id.
 *  2. `estate_id` is a *scope selector*, not proof of access. The server resolves
 *     the caller's memberships; we only pass along the estate the user picked.
 */

const RAW_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
export const API_BASE = RAW_BASE.replace(/\/$/, '')

const TOKEN_KEY = 'valora.token'
const USER_KEY = 'valora.user'

export class ApiError extends Error {
  readonly status: number
  readonly code?: string
  readonly requestId?: string

  constructor(status: number, message: string, code?: string, requestId?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.requestId = requestId
  }

  get isUnauthorized(): boolean {
    return this.status === 401
  }

  get isForbidden(): boolean {
    return this.status === 403
  }
}

export const session = {
  token(): string | null {
    return localStorage.getItem(TOKEN_KEY)
  },
  user(): CurrentUser | null {
    const raw = localStorage.getItem(USER_KEY)
    if (!raw) return null
    try {
      return JSON.parse(raw) as CurrentUser
    } catch {
      return null
    }
  },
  save(auth: AuthResponse) {
    localStorage.setItem(TOKEN_KEY, auth.access_token)
    localStorage.setItem(USER_KEY, JSON.stringify(auth.user))
  },
  saveUser(user: CurrentUser) {
    localStorage.setItem(USER_KEY, JSON.stringify(user))
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  },
}

let onUnauthorized: (() => void) | null = null
export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler
}

type Params = Record<string, string | number | boolean | undefined | null>

function buildUrl(path: string, params?: Params): string {
  const url = new URL(`${API_BASE}${path}`)
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined || value === null || value === '') continue
      url.searchParams.set(key, String(value))
    }
  }
  return url.toString()
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  params?: Params
  body?: unknown
  /** Skip the Authorization header (login/register). */
  anonymous?: boolean
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', params, body, anonymous } = options
  const headers: Record<string, string> = { Accept: 'application/json' }

  if (!anonymous) {
    const token = session.token()
    if (token) headers.Authorization = `Bearer ${token}`
  }
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  let response: Response
  try {
    response = await fetch(buildUrl(path, params), {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError(0, 'Cannot reach the VALORA API. Is the backend running?')
  }

  if (response.status === 204) return undefined as T

  const text = await response.text()
  let payload: unknown = null
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      payload = text
    }
  }

  if (!response.ok) {
    const detail = (payload as { detail?: unknown } | null)?.detail
    const shaped =
      detail && typeof detail === 'object'
        ? (detail as { message?: string; code?: string; request_id?: string })
        : undefined

    const message =
      shaped?.message ??
      (typeof detail === 'string' ? detail : undefined) ??
      (Array.isArray(detail) && detail.length > 0
        ? String((detail[0] as { msg?: string }).msg ?? 'The request was rejected.')
        : undefined) ??
      `Request failed (${response.status}).`

    if (response.status === 401) {
      session.clear()
      onUnauthorized?.()
    }
    throw new ApiError(response.status, message, shaped?.code, shaped?.request_id)
  }

  return payload as T
}

export const api = {
  get: <T>(path: string, params?: Params) => request<T>(path, { params }),
  post: <T>(path: string, body?: unknown, params?: Params) =>
    request<T>(path, { method: 'POST', body, params }),
  patch: <T>(path: string, body?: unknown, params?: Params) =>
    request<T>(path, { method: 'PATCH', body, params }),
  remove: <T>(path: string, params?: Params) => request<T>(path, { method: 'DELETE', params }),
  login: (email: string, password: string) =>
    request<AuthResponse>('/api/v1/auth/login', {
      method: 'POST',
      body: { email, password },
      anonymous: true,
    }),
  /**
   * The registration contract, taken from the generated types: `account_type`
   * decides what else must be sent (an estate for an administrator, a trade and
   * phone for a provider) — there is deliberately no `role` field to send.
   */
  register: (payload: RegisterRequest) =>
    request<AuthResponse>('/api/v1/auth/register', {
      method: 'POST',
      body: payload,
      anonymous: true,
    }),
  me: () => request<CurrentUser>('/api/v1/auth/me'),
  myEstates: () => request<EstateAccessList>('/api/v1/auth/estates'),
}

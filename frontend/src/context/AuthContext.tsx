import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { api, ApiError, session, setUnauthorizedHandler } from '../lib/api'
import type { RegisterRequest } from '../lib/contract'
import type { CurrentUser } from '../lib/types'

interface AuthValue {
  user: CurrentUser | null
  /** True until the stored token has been checked against the API. */
  checking: boolean
  login: (email: string, password: string) => Promise<CurrentUser>
  register: (payload: RegisterRequest) => Promise<CurrentUser>
  logout: () => void
}

const AuthContext = createContext<AuthValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(() => session.user())
  const [checking, setChecking] = useState(() => session.token() !== null)

  const logout = useCallback(() => {
    session.clear()
    setUser(null)
  }, [])

  useEffect(() => {
    setUnauthorizedHandler(() => setUser(null))
  }, [])

  useEffect(() => {
    if (!session.token()) {
      setChecking(false)
      return
    }
    let cancelled = false
    api
      .me()
      .then((me) => {
        if (cancelled) return
        session.saveUser(me)
        setUser(me)
      })
      .catch(() => {
        if (cancelled) return
        logout()
      })
      .finally(() => {
        if (!cancelled) setChecking(false)
      })
    return () => {
      cancelled = true
    }
  }, [logout])

  const login = useCallback(async (email: string, password: string) => {
    const auth = await api.login(email, password)
    session.save(auth)
    setUser(auth.user)
    return auth.user
  }, [])

  const register = useCallback(async (payload: RegisterRequest) => {
      const auth = await api.register(payload)
      session.save(auth)
      setUser(auth.user)
      return auth.user
    },
    [],
  )

  const value = useMemo<AuthValue>(
    () => ({ user, checking, login, register, logout }),
    [user, checking, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside <AuthProvider>.')
  return value
}

export { ApiError }

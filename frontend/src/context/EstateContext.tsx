import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { api, ApiError } from '../lib/api'
import type { EstateAccess } from '../lib/types'
import { useAuth } from './AuthContext'

const ACTIVE_KEY = 'valora.estate'

interface EstateValue {
  estates: EstateAccess[]
  active: EstateAccess | null
  loading: boolean
  error: ApiError | null
  /** Registered, but no HOA has provisioned a membership yet. */
  awaitingProvisioning: boolean
  selectEstate: (estateId: number) => void
  reload: () => void
}

const EstateContext = createContext<EstateValue | null>(null)

export function EstateProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const [estates, setEstates] = useState<EstateAccess[]>([])
  const [activeId, setActiveId] = useState<number | null>(() => {
    const raw = localStorage.getItem(ACTIVE_KEY)
    return raw ? Number(raw) : null
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<ApiError | null>(null)
  const [nonce, setNonce] = useState(0)

  const reload = useCallback(() => setNonce((n) => n + 1), [])

  useEffect(() => {
    if (!user) {
      setEstates([])
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    api
      .myEstates()
      .then((result) => {
        if (cancelled) return
        setEstates(result.estates)
      })
      .catch((cause: unknown) => {
        if (cancelled) return
        setEstates([])
        setError(
          cause instanceof ApiError
            ? cause
            : new ApiError(0, cause instanceof Error ? cause.message : 'Could not load your estates.'),
        )
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [user, nonce])

  // Keep the selection valid: fall back to the first estate the user can access.
  const active = useMemo(() => {
    if (estates.length === 0) return null
    const chosen = estates.find((estate) => estate.estate_id === activeId)
    return chosen ?? estates[0]
  }, [estates, activeId])

  useEffect(() => {
    if (active && active.estate_id !== activeId) {
      setActiveId(active.estate_id)
    }
  }, [active, activeId])

  const selectEstate = useCallback((estateId: number) => {
    localStorage.setItem(ACTIVE_KEY, String(estateId))
    setActiveId(estateId)
  }, [])

  const value = useMemo<EstateValue>(
    () => ({
      estates,
      active,
      loading,
      error,
      awaitingProvisioning: !loading && !error && estates.length === 0,
      selectEstate,
      reload,
    }),
    [estates, active, loading, error, selectEstate, reload],
  )

  return <EstateContext.Provider value={value}>{children}</EstateContext.Provider>
}

export function useEstate(): EstateValue {
  const value = useContext(EstateContext)
  if (!value) throw new Error('useEstate must be used inside <EstateProvider>.')
  return value
}

/**
 * Convenience hook for estate-scoped screens. `estateId` is only a scope
 * selector — the server still enforces membership on every request.
 */
export function useEstateScope() {
  const { active, ...rest } = useEstate()
  return { ...rest, estateId: active?.estate_id ?? null, estate: active }
}

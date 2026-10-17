import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { api, ApiError } from '../lib/api'
import { getLivingScore, getLivingScoreHistory } from '../lib/analytics'
import { pillarBand } from '../lib/display'
import type { EstateAccess } from '../lib/types'
import { useAuth } from './AuthContext'

const ACTIVE_KEY = 'valora.estate'

/**
 * The estate's Living Score, as the sidebar and page headers need it.
 *
 * Every field is read from a stored snapshot: `value` is the engine's published
 * figure, `label` is a presentation band over it, and `trend` — when there are
 * two stored snapshots — is the *difference between two published numbers*, not a
 * calculation of a score. There is deliberately no formula here: the pillar
 * weights, the rolling window and the composite all live in the backend service.
 */
export interface EstateLivingScore {
  /** The stored figure, or null when the estate has no publishable score. */
  value: number | null
  /** Points between the two most recent stored snapshots. */
  trend: number | null
  /** The written status: the band label, plus where the pillars are not healthy. */
  label: string
  /** The status the engine stored on the snapshot, verbatim. */
  status: string | null
  /** Stored scores, oldest first, for a trajectory line. */
  history: number[]
  /** When the newest stored snapshot was calculated. */
  calculatedAt: string | null
  loading: boolean
}

const NO_LIVING_SCORE: EstateLivingScore = {
  value: null,
  trend: null,
  label: 'Not enough data yet',
  status: null,
  history: [],
  calculatedAt: null,
  loading: false,
}

interface EstateValue {
  estates: EstateAccess[]
  active: EstateAccess | null
  loading: boolean
  error: ApiError | null
  /** Registered, but no HOA has provisioned a membership yet. */
  awaitingProvisioning: boolean
  /** The selected estate's stored Living Score. Never recalculated here. */
  livingScore: EstateLivingScore
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

  /*
    The Living Score shown in the shell.

    Two reads per estate: the newest stored snapshot (with its pillar breakdown,
    for the written status) and a two-row history slice (for the trajectory). A
    404 means the estate has never been scored — a real state that renders as “not
    enough data yet”, never as a zero — and any other failure is swallowed into the
    same empty state, because a missing score must not break the navigation.
  */
  const [livingScore, setLivingScore] = useState<EstateLivingScore>(NO_LIVING_SCORE)

  useEffect(() => {
    if (!active) {
      setLivingScore(NO_LIVING_SCORE)
      return
    }
    const estateId = active.estate_id
    let cancelled = false
    setLivingScore({ ...NO_LIVING_SCORE, loading: true })

    Promise.all([
      getLivingScore(estateId).catch(() => null),
      getLivingScoreHistory(estateId, 2).catch(() => null),
    ])
      .then(([snapshot, history]) => {
        if (cancelled) return

        const rows = [...(history?.snapshots ?? [])].reverse()
        const storedValues = rows
          .map((row) => (row.overall_score === null ? null : Number(row.overall_score)))
          .filter((value): value is number => value !== null && Number.isFinite(value))

        const value =
          snapshot && snapshot.overall_score !== null && snapshot.status === 'scored'
            ? Number(snapshot.overall_score)
            : (storedValues.at(-1) ?? null)

        if (value === null || !Number.isFinite(value)) {
          setLivingScore({
            ...NO_LIVING_SCORE,
            status: snapshot?.status ?? null,
            calculatedAt: snapshot?.calculated_at ?? null,
          })
          return
        }

        const previous = storedValues.length > 1 ? storedValues[storedValues.length - 2] : null
        const band = pillarBand(value)

        // “Healthy, with watch areas” — the band for the composite, qualified by
        // the pillars the engine itself marked as measured but not healthy.
        const flagged = (snapshot?.components ?? []).filter(
          (component) =>
            component.status === 'measured' &&
            component.score !== null &&
            pillarBand(Number(component.score)).tone !== 'positive',
        )
        const suffix =
          flagged.length === 0
            ? ''
            : band.tone === 'positive'
              ? ', with watch areas'
              : ', with pillars to recover'

        setLivingScore({
          value,
          trend: previous === null ? null : Math.round((value - previous) * 10) / 10,
          label: `${band.label}${suffix}`,
          status: snapshot?.status ?? null,
          history: storedValues,
          calculatedAt: snapshot?.calculated_at ?? null,
          loading: false,
        })
      })
      .catch(() => {
        if (!cancelled) setLivingScore(NO_LIVING_SCORE)
      })

    return () => {
      cancelled = true
    }
  }, [active])

  const value = useMemo<EstateValue>(
    () => ({
      estates,
      active,
      loading,
      error,
      awaitingProvisioning: !loading && !error && estates.length === 0,
      livingScore,
      selectEstate,
      reload,
    }),
    [estates, active, loading, error, livingScore, selectEstate, reload],
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

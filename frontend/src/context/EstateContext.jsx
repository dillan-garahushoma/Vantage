import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api, ApiError } from '../lib/api';
import { getLivingScore, getLivingScoreHistory } from '../lib/analytics';
import { pillarBand } from '../lib/display';
import { useAuth } from './AuthContext';
const ACTIVE_KEY = 'valora.estate';
const NO_LIVING_SCORE = {
    value: null,
    trend: null,
    label: 'Not enough data yet',
    status: null,
    history: [],
    calculatedAt: null,
    loading: false,
};
const EstateContext = createContext(null);
export function EstateProvider({ children }) {
    const { user } = useAuth();
    const [estates, setEstates] = useState([]);
    const [activeId, setActiveId] = useState(() => {
        const raw = localStorage.getItem(ACTIVE_KEY);
        return raw ? Number(raw) : null;
    });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [nonce, setNonce] = useState(0);
    const reload = useCallback(() => setNonce((n) => n + 1), []);
    useEffect(() => {
        if (!user) {
            setEstates([]);
            setLoading(false);
            return;
        }
        let cancelled = false;
        setLoading(true);
        setError(null);
        api
            .myEstates()
            .then((result) => {
            if (cancelled)
                return;
            setEstates(result.estates);
        })
            .catch((cause) => {
            if (cancelled)
                return;
            setEstates([]);
            setError(cause instanceof ApiError
                ? cause
                : new ApiError(0, cause instanceof Error ? cause.message : 'Could not load your estates.'));
        })
            .finally(() => {
            if (!cancelled)
                setLoading(false);
        });
        return () => {
            cancelled = true;
        };
    }, [user, nonce]);
    // Keep the selection valid: fall back to the first estate the user can access.
    const active = useMemo(() => {
        if (estates.length === 0)
            return null;
        const chosen = estates.find((estate) => estate.estate_id === activeId);
        return chosen ?? estates[0];
    }, [estates, activeId]);
    useEffect(() => {
        if (active && active.estate_id !== activeId) {
            setActiveId(active.estate_id);
        }
    }, [active, activeId]);
    const selectEstate = useCallback((estateId) => {
        localStorage.setItem(ACTIVE_KEY, String(estateId));
        setActiveId(estateId);
    }, []);
    /*
      The Living Score shown in the shell.
  
      Two reads per estate: the newest stored snapshot (with its pillar breakdown,
      for the written status) and a two-row history slice (for the trajectory). A
      404 means the estate has never been scored — a real state that renders as “not
      enough data yet”, never as a zero — and any other failure is swallowed into the
      same empty state, because a missing score must not break the navigation.
    */
    const [livingScore, setLivingScore] = useState(NO_LIVING_SCORE);
    useEffect(() => {
        if (!active) {
            setLivingScore(NO_LIVING_SCORE);
            return;
        }
        const estateId = active.estate_id;
        let cancelled = false;
        setLivingScore({ ...NO_LIVING_SCORE, loading: true });
        Promise.all([
            getLivingScore(estateId).catch(() => null),
            getLivingScoreHistory(estateId, 2).catch(() => null),
        ])
            .then(([snapshot, history]) => {
            if (cancelled)
                return;
            const rows = [...(history?.snapshots ?? [])].reverse();
            const storedValues = rows
                .map((row) => (row.overall_score === null ? null : Number(row.overall_score)))
                .filter((value) => value !== null && Number.isFinite(value));
            const value = snapshot && snapshot.overall_score !== null && snapshot.status === 'scored'
                ? Number(snapshot.overall_score)
                : (storedValues.at(-1) ?? null);
            if (value === null || !Number.isFinite(value)) {
                setLivingScore({
                    ...NO_LIVING_SCORE,
                    status: snapshot?.status ?? null,
                    calculatedAt: snapshot?.calculated_at ?? null,
                });
                return;
            }
            const previous = storedValues.length > 1 ? storedValues[storedValues.length - 2] : null;
            const band = pillarBand(value);
            // “Healthy, with watch areas” — the band for the composite, qualified by
            // the pillars the engine itself marked as measured but not healthy.
            const flagged = (snapshot?.components ?? []).filter((component) => component.status === 'measured' &&
                component.score !== null &&
                pillarBand(Number(component.score)).tone !== 'positive');
            const suffix = flagged.length === 0
                ? ''
                : band.tone === 'positive'
                    ? ', with watch areas'
                    : ', with pillars to recover';
            setLivingScore({
                value,
                trend: previous === null ? null : Math.round((value - previous) * 10) / 10,
                label: `${band.label}${suffix}`,
                status: snapshot?.status ?? null,
                history: storedValues,
                calculatedAt: snapshot?.calculated_at ?? null,
                loading: false,
            });
        })
            .catch(() => {
            if (!cancelled)
                setLivingScore(NO_LIVING_SCORE);
        });
        return () => {
            cancelled = true;
        };
    }, [active]);
    const value = useMemo(() => ({
        estates,
        active,
        loading,
        error,
        awaitingProvisioning: !loading && !error && estates.length === 0,
        livingScore,
        selectEstate,
        reload,
    }), [estates, active, loading, error, livingScore, selectEstate, reload]);
    return <EstateContext.Provider value={value}>{children}</EstateContext.Provider>;
}
export function useEstate() {
    const value = useContext(EstateContext);
    if (!value)
        throw new Error('useEstate must be used inside <EstateProvider>.');
    return value;
}
/**
 * Convenience hook for estate-scoped screens. `estateId` is only a scope
 * selector — the server still enforces membership on every request.
 */
export function useEstateScope() {
    const { active, ...rest } = useEstate();
    return { ...rest, estateId: active?.estate_id ?? null, estate: active };
}

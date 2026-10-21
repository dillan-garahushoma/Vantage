import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError } from './api';
/**
 * Loads data for a screen. Deliberately small: no cache, no retries — a page
 * either shows the data, a clear error, or a loading state.
 */
export function useAsync(loader, deps) {
    const [data, setData] = useState(null);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(true);
    const [nonce, setNonce] = useState(0);
    const latest = useRef(0);
    const reload = useCallback(() => setNonce((n) => n + 1), []);
    useEffect(() => {
        const run = ++latest.current;
        let cancelled = false;
        setLoading(true);
        setError(null);
        loader()
            .then((result) => {
            if (cancelled || run !== latest.current)
                return;
            setData(result);
        })
            .catch((cause) => {
            if (cancelled || run !== latest.current)
                return;
            setData(null);
            setError(cause instanceof ApiError
                ? cause
                : new ApiError(0, cause instanceof Error ? cause.message : 'Something went wrong.'));
        })
            .finally(() => {
            if (cancelled || run !== latest.current)
                return;
            setLoading(false);
        });
        return () => {
            cancelled = true;
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [...deps, nonce]);
    return { data, error, loading, reload };
}

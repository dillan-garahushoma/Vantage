import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api, ApiError, session, setUnauthorizedHandler } from '../lib/api';
const AuthContext = createContext(null);
export function AuthProvider({ children }) {
    const [user, setUser] = useState(() => session.user());
    const [checking, setChecking] = useState(() => session.token() !== null);
    const logout = useCallback(() => {
        session.clear();
        setUser(null);
    }, []);
    useEffect(() => {
        setUnauthorizedHandler(() => setUser(null));
    }, []);
    useEffect(() => {
        if (!session.token()) {
            setChecking(false);
            return;
        }
        let cancelled = false;
        api
            .me()
            .then((me) => {
            if (cancelled)
                return;
            session.saveUser(me);
            setUser(me);
        })
            .catch(() => {
            if (cancelled)
                return;
            logout();
        })
            .finally(() => {
            if (!cancelled)
                setChecking(false);
        });
        return () => {
            cancelled = true;
        };
    }, [logout]);
    const login = useCallback(async (email, password) => {
        const auth = await api.login(email, password);
        session.save(auth);
        setUser(auth.user);
        return auth.user;
    }, []);
    const register = useCallback(async (payload) => {
        const auth = await api.register(payload);
        session.save(auth);
        setUser(auth.user);
        return auth.user;
    }, []);
    const value = useMemo(() => ({ user, checking, login, register, logout }), [user, checking, login, register, logout]);
    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export function useAuth() {
    const value = useContext(AuthContext);
    if (!value)
        throw new Error('useAuth must be used inside <AuthProvider>.');
    return value;
}
export { ApiError };

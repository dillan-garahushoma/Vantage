/**
 * Thin JavaScript wrapper around the VALORA API.
 *
 * Two rules this file exists to enforce:
 *  1. The JWT is the only proof of identity — never a client-supplied user id.
 *  2. `estate_id` is a *scope selector*, not proof of access. The server resolves
 *     the caller's memberships; we only pass along the estate the user picked.
 */
const configuredBase = typeof import.meta.env.VITE_API_BASE_URL === 'string'
    ? import.meta.env.VITE_API_BASE_URL.trim()
    : '';
// Local development gets a convenient origin; production must be configured
// with the deployed API host at build time. Never ship a browser call to the
// visitor's own localhost when Pages has no API environment variable.
const RAW_BASE = configuredBase || (import.meta.env.DEV ? 'http://localhost:8000' : '');
export const API_BASE = RAW_BASE.replace(/\/$/, '');
export const API_CONFIGURED = Boolean(API_BASE);
const TOKEN_KEY = 'valora.token';
const USER_KEY = 'valora.user';
export class ApiError extends Error {
    status;
    code;
    requestId;
    constructor(status, message, code, requestId) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.code = code;
        this.requestId = requestId;
    }
    get isUnauthorized() {
        return this.status === 401;
    }
    get isForbidden() {
        return this.status === 403;
    }
}
export const session = {
    token() {
        return localStorage.getItem(TOKEN_KEY);
    },
    user() {
        const raw = localStorage.getItem(USER_KEY);
        if (!raw)
            return null;
        try {
            return JSON.parse(raw);
        }
        catch {
            return null;
        }
    },
    save(auth) {
        localStorage.setItem(TOKEN_KEY, auth.access_token);
        localStorage.setItem(USER_KEY, JSON.stringify(auth.user));
    },
    saveUser(user) {
        localStorage.setItem(USER_KEY, JSON.stringify(user));
    },
    clear() {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
    },
};
let onUnauthorized = null;
export function setUnauthorizedHandler(handler) {
    onUnauthorized = handler;
}
function buildUrl(path, params) {
    if (!API_BASE) {
        throw new ApiError(
            0,
            'VALORA could not connect because this deployment has no API address configured. Set VITE_API_BASE_URL to the deployed backend URL in the frontend hosting settings, then rebuild.',
            'API_BASE_URL_MISSING',
        );
    }
    const url = new URL(`${API_BASE}${path}`);
    if (params) {
        for (const [key, value] of Object.entries(params)) {
            if (value === undefined || value === null || value === '')
                continue;
            url.searchParams.set(key, String(value));
        }
    }
    return url.toString();
}
async function request(path, options = {}) {
    if (!API_CONFIGURED) {
        throw new ApiError(
            0,
            'VALORA could not connect because this deployment has no API address configured. Set VITE_API_BASE_URL to the deployed backend URL in the frontend hosting settings, then rebuild.',
            'API_BASE_URL_MISSING',
        );
    }
    const { method = 'GET', params, body, anonymous } = options;
    const headers = { Accept: 'application/json' };
    if (!anonymous) {
        const token = session.token();
        if (token)
            headers.Authorization = `Bearer ${token}`;
    }
    if (body !== undefined)
        headers['Content-Type'] = 'application/json';
    let response;
    try {
        response = await fetch(buildUrl(path, params), {
            method,
            headers,
            body: body === undefined ? undefined : JSON.stringify(body),
        });
    }
    catch {
        throw new ApiError(0, 'Cannot reach the VALORA API. Is the backend running?');
    }
    if (response.status === 204)
        return undefined;
    const text = await response.text();
    let payload = null;
    if (text) {
        try {
            payload = JSON.parse(text);
        }
        catch {
            payload = text;
        }
    }
    if (!response.ok) {
        const detail = payload?.detail;
        const shaped = detail && typeof detail === 'object'
            ? detail
            : undefined;
        const message = shaped?.message ??
            (typeof detail === 'string' ? detail : undefined) ??
            (Array.isArray(detail) && detail.length > 0
                ? String(detail[0].msg ?? 'The request was rejected.')
                : undefined) ??
            `Request failed (${response.status}).`;
        if (response.status === 401) {
            session.clear();
            onUnauthorized?.();
        }
        throw new ApiError(response.status, message, shaped?.code, shaped?.request_id);
    }
    return payload;
}
export const api = {
    contact: (payload) => request('/api/v1/contact', {
        method: 'POST', body: payload, anonymous: true,
    }),
    get: (path, params) => request(path, { params }),
    post: (path, body, params) => request(path, { method: 'POST', body, params }),
    patch: (path, body, params) => request(path, { method: 'PATCH', body, params }),
    remove: (path, params) => request(path, { method: 'DELETE', params }),
    login: (email, password) => request('/api/v1/auth/login', {
        method: 'POST',
        body: { email, password },
        anonymous: true,
    }),
    /** Public registration creates resident accounts only. */
    register: (payload) => request('/api/v1/auth/register', {
        method: 'POST',
        body: payload,
        anonymous: true,
    }),
    /** Estate onboarding creates a new estate and its first administrator. */
    registerEstate: (payload) => request('/api/v1/auth/register-estate', {
        method: 'POST',
        body: payload,
        anonymous: true,
    }),
    applyAsProvider: (payload) => request('/api/v1/provider-applications', {
        method: 'POST',
        body: payload,
        anonymous: true,
    }),
    acceptProviderInvitation: (token, password) => request('/api/v1/auth/provider-invitations/accept', {
        method: 'POST',
        body: password ? { token, password } : { token },
        anonymous: true,
    }),
    me: () => request('/api/v1/auth/me'),
    myEstates: () => request('/api/v1/auth/estates'),
};

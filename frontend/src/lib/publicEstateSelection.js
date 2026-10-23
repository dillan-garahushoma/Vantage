const SELECTION_KEY = 'valora.public-estate-selection';

/**
 * Keep a visitor's directory choice through registration or sign-in. This is
 * navigation context only: the request and join APIs still resolve access on
 * the server and never trust this browser value as proof of membership.
 */
export function rememberPublicEstate(estate) {
  if (!estate?.estate_id || typeof window === 'undefined') return;
  window.sessionStorage.setItem(
    SELECTION_KEY,
    JSON.stringify({
      estate_id: Number(estate.estate_id),
      name: String(estate.name ?? ''),
      location: [estate.suburb, estate.city, estate.province].filter(Boolean).join(', '),
    }),
  );
}

export function selectedPublicEstate() {
  if (typeof window === 'undefined') return null;
  try {
    const value = JSON.parse(window.sessionStorage.getItem(SELECTION_KEY) ?? 'null');
    return value && Number.isInteger(value.estate_id) && value.estate_id > 0 ? value : null;
  } catch {
    return null;
  }
}

export function clearSelectedPublicEstate() {
  if (typeof window !== 'undefined') window.sessionStorage.removeItem(SELECTION_KEY);
}

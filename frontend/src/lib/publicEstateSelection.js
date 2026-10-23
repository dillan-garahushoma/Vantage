const SELECTION_KEY = 'valora.public-estate-selection';

/**
 * Preserve a visitor's estate choice during registration and access requests.
 * This object is only onboarding context; the API revalidates the estate, unit,
 * and membership and never treats session storage as proof of access.
 */
export function rememberPublicEstate(estate, unitNo = '') {
  if (!estate?.estate_id || typeof window === 'undefined') return;
  const estateId = Number(estate.estate_id);
  if (!Number.isSafeInteger(estateId) || estateId <= 0) return;

  try {
    window.sessionStorage.setItem(
      SELECTION_KEY,
      JSON.stringify({
        estate_id: estateId,
        name: String(estate.name ?? ''),
        location: String(
          estate.location ??
            [estate.suburb, estate.city, estate.province].filter(Boolean).join(', '),
        ),
        unit_no: String(unitNo ?? '').trim().slice(0, 10),
      }),
    );
  } catch {
    // Storage can be blocked by browser privacy settings. The user can still
    // select the estate again on the access-request screen.
  }
}

export function selectedPublicEstate() {
  if (typeof window === 'undefined') return null;
  try {
    const value = JSON.parse(window.sessionStorage.getItem(SELECTION_KEY) ?? 'null');
    if (!value || !Number.isSafeInteger(Number(value.estate_id)) || Number(value.estate_id) <= 0) {
      return null;
    }
    return {
      estate_id: Number(value.estate_id),
      name: String(value.name ?? ''),
      location: String(value.location ?? ''),
      unit_no: String(value.unit_no ?? '').trim().slice(0, 10),
    };
  } catch {
    return null;
  }
}

export function clearSelectedPublicEstate() {
  if (typeof window !== 'undefined') {
    try {
      window.sessionStorage.removeItem(SELECTION_KEY);
    } catch {
      // Storage may be unavailable; nothing else relies on this client context.
    }
  }
}

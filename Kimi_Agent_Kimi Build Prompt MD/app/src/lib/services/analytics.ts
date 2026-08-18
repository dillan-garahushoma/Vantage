/**
 * Analytics abstraction — no vendor hard-coded.
 * Connect GA4/another provider later by implementing `track`.
 * Never include PII (names, phone numbers, addresses) in payloads.
 */
type AnalyticsPayload = Record<string, string | number | boolean | undefined>;

export const analytics = {
  track(event: string, payload: AnalyticsPayload = {}) {
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.debug(`[analytics] ${event}`, payload);
    }
    // Future: forward to GA4 / server-side endpoint.
    void event;
    void payload;
  },
};

declare global {
  interface Window {
    dataLayer?: unknown[];
  }
}

/**
 * Push a custom event to the GTM dataLayer.
 * GTM only loads on *.myvoya.ai (production/staging), so this is a no-op locally.
 *
 * `P` is constrained to `Record<string, unknown>` so typed analytics payloads (e.g.
 * `HotelRoomSelectedEventPayload`) can be passed without assertions.
 */
export function trackEvent<P extends Record<string, unknown> = Record<string, unknown>>(
  event: string,
  properties?: P
): void {
  if (typeof window !== 'undefined' && window.dataLayer) {
    window.dataLayer.push({ event, ...(properties ?? {}) });
  }
}

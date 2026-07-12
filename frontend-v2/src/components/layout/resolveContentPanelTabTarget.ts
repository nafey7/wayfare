/**
 * Resolve tab chip navigation targets for the current route tree (authenticated vs `/public/chat`).
 *
 * **Stored paths are not always auth-scoped.** `ContentPanel` syncs `pathname + search` into Redux
 * (`lastFlightPath`, `lastHotelPath`, `lastItineraryPath`) as the user browses. If the user was
 * last on a public chat URL, those values can be `/public/chat/flights/search?...` (or other
 * public-prefixed paths). If they were on authenticated routes, values are `/flights/search?...`.
 * Other code (e.g. itinerary sync) may also write auth-scoped paths while the UI is under
 * `/public/chat`. This helper normalizes so chip clicks stay in the correct tree.
 */
export function resolveTarget(
  storedPath: string | null | undefined,
  fallback: string,
  prefix: string
): string {
  if (!storedPath) return fallback;
  if (prefix === '') {
    return storedPath.startsWith('/public/chat') ? fallback : storedPath;
  }
  if (storedPath.startsWith(prefix)) return storedPath;
  if (
    storedPath.startsWith('/itinerary') ||
    storedPath.startsWith('/flights') ||
    storedPath.startsWith('/hotels')
  ) {
    return `${prefix}${storedPath}`;
  }
  return fallback;
}

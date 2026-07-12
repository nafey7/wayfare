/**
 * Fallback when the API omits platform fee percentage on flight fares.
 * Matches backend `FLIGHTS_DISCOUNT_PERCENTAGE` (see `backend_python/app/domains/flight/pricing.py`).
 */
export const DEFAULT_FLIGHT_PLATFORM_FEE_PERCENTAGE = 5;

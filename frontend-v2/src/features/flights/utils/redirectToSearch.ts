import type { FlightSearchFormParams } from '@/store/slices/flightBookingSlice';
import { convertFormParamsToUI, serializeSearchParamsToUrl } from './urlParams';

/**
 * Build target path for redirect when required state is missing.
 * Uses Redux searchFormParams to preserve user's search results in URL.
 */
export function buildFlightSearchRedirectTarget(
  searchFormParams: FlightSearchFormParams,
  prefix = '',
): string {
  const hasValidParams = searchFormParams.from?.trim() && searchFormParams.to?.trim();
  if (!hasValidParams) return `${prefix}/flights/search`;
  const encoded = serializeSearchParamsToUrl(convertFormParamsToUI(searchFormParams));
  return encoded
    ? `${prefix}/flights/search?q=${encodeURIComponent(encoded)}`
    : `${prefix}/flights/search`;
}

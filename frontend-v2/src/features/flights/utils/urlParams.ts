import type { FlightSearchParamsUI } from '@/types/flights';
import type { FlightSearchFormParams } from '@/store/slices/flightBookingSlice';
import type { ChatFlightFilters } from '@/features/chat/utils/chatSearchParamsToUI';

/**
 * Serialize search params to base64-encoded JSON for URL
 */
function toSerializableAirport(a?: { iata: string; name: string; city: string; state?: string; country: string; isCityOption?: boolean } | null) {
  return a ? { iata: a.iata, name: a.name, city: a.city, state: a.state, country: a.country, isCityOption: a.isCityOption } : undefined;
}

export function serializeSearchParamsToUrl(params: FlightSearchParamsUI): string {
  try {
    const serializable: Record<string, unknown> = {
      tripType: params.tripType,
      from: params.from,
      to: params.to,
      date: params.date ? params.date.toISOString() : null,
      returnDate: params.returnDate ? params.returnDate.toISOString() : null,
      segments: params.segments?.map((seg) => ({
        from: seg.from,
        to: seg.to,
        date: seg.date ? seg.date.toISOString() : null,
        fromAirport: toSerializableAirport(seg.fromAirport ?? undefined),
        toAirport: toSerializableAirport(seg.toAirport ?? undefined),
      })),
      travellers: params.travellers,
      fromAirport: toSerializableAirport(params.fromAirport),
      toAirport: toSerializableAirport(params.toAirport),
    };
    if (params.originIsCity !== undefined) serializable.originIsCity = params.originIsCity;
    if (params.destinationIsCity !== undefined) serializable.destinationIsCity = params.destinationIsCity;
    if (params.originIata) serializable.originIata = params.originIata;
    if (params.destinationIata) serializable.destinationIata = params.destinationIata;

    const json = JSON.stringify(serializable);
    return btoa(json);
  } catch (error) {
    console.error('Error serializing search params:', error);
    return '';
  }
}

/**
 * Deserialize search params from base64-encoded JSON in URL
 */
export function deserializeSearchParamsFromUrl(encoded: string): FlightSearchParamsUI | null {
  if (!encoded) return null;
  try {
    const json = atob(encoded);
    const parsed = JSON.parse(json);

    const result: FlightSearchParamsUI = {
      tripType: parsed.tripType,
      from: parsed.from,
      to: parsed.to,
      date: parsed.date ? new Date(parsed.date) : null,
      returnDate: parsed.returnDate ? new Date(parsed.returnDate) : null,
      segments: parsed.segments?.map(
        (seg: {
          from: string;
          to: string;
          date: string | null;
          fromAirport?: unknown;
          toAirport?: unknown;
        }) => ({
          from: seg.from,
          to: seg.to,
          date: seg.date ? new Date(seg.date) : null,
          fromAirport: (seg.fromAirport as FlightSearchParamsUI['fromAirport']) ?? null,
          toAirport: (seg.toAirport as FlightSearchParamsUI['toAirport']) ?? null,
        })
      ),
      travellers: parsed.travellers,
      fromAirport: parsed.fromAirport ?? null,
      toAirport: parsed.toAirport ?? null,
    };
    if (parsed.originIsCity !== undefined) result.originIsCity = parsed.originIsCity;
    if (parsed.destinationIsCity !== undefined) result.destinationIsCity = parsed.destinationIsCity;
    if (parsed.originIata) result.originIata = parsed.originIata;
    if (parsed.destinationIata) result.destinationIata = parsed.destinationIata;
    return result;
  } catch (error) {
    console.error('Error deserializing search params:', error);
    return null;
  }
}

/**
 * Convert FlightSearchParamsUI to FlightSearchFormParams for Redux
 */
export function convertUIToFormParams(uiParams: FlightSearchParamsUI): FlightSearchFormParams {
  return {
    tripType: uiParams.tripType,
    from: uiParams.from,
    to: uiParams.to,
    date: uiParams.date ? uiParams.date.toISOString() : null,
    returnDate: uiParams.returnDate ? uiParams.returnDate.toISOString() : null,
    segments: uiParams.segments?.map((seg) => ({
      from: seg.from,
      to: seg.to,
      date: seg.date ? seg.date.toISOString() : null,
      fromAirport: toSerializableAirport(seg.fromAirport ?? undefined),
      toAirport: toSerializableAirport(seg.toAirport ?? undefined),
    })),
    travellers: uiParams.travellers,
    fromAirport: toSerializableAirport(uiParams.fromAirport),
    toAirport: toSerializableAirport(uiParams.toAirport),
    originIsCity: uiParams.originIsCity,
    destinationIsCity: uiParams.destinationIsCity,
  };
}

/**
 * Convert FlightSearchFormParams to FlightSearchParamsUI for component
 */
export function convertFormParamsToUI(formParams: FlightSearchFormParams): FlightSearchParamsUI {
  return {
    tripType: formParams.tripType,
    from: formParams.from,
    to: formParams.to,
    date: formParams.date ? new Date(formParams.date) : null,
    returnDate: formParams.returnDate ? new Date(formParams.returnDate) : null,
    segments: formParams.segments?.map((seg) => ({
      from: seg.from,
      to: seg.to,
      date: seg.date ? new Date(seg.date) : null,
      fromAirport: seg.fromAirport ?? null,
      toAirport: seg.toAirport ?? null,
    })),
    travellers: formParams.travellers,
    fromAirport: formParams.fromAirport ?? null,
    toAirport: formParams.toAirport ?? null,
    originIsCity: formParams.originIsCity,
    destinationIsCity: formParams.destinationIsCity,
  };
}

/**
 * Serialize ChatFlightFilters to base64-encoded JSON for the ?f= URL param
 */
export function serializeChatFiltersToUrl(filters: ChatFlightFilters): string {
  try {
    return btoa(JSON.stringify(filters));
  } catch (error) {
    console.error('Error serializing chat filters:', error);
    return '';
  }
}

/**
 * Deserialize ChatFlightFilters from base64-encoded JSON in the ?f= URL param
 */
export function deserializeChatFiltersFromUrl(encoded: string): ChatFlightFilters | null {
  try {
    const json = atob(encoded);
    const parsed = JSON.parse(json);

    return {
      priceMin: parsed.priceMin ?? null,
      priceMax: parsed.priceMax ?? null,
      directOnly: parsed.directOnly ?? false,
      airlines: Array.isArray(parsed.airlines) ? parsed.airlines : [],
      outboundDurationMax: parsed.outboundDurationMax ?? null,
      inboundDurationMax: parsed.inboundDurationMax ?? null,
    };
  } catch (error) {
    console.error('Error deserializing chat filters:', error);
    return null;
  }
}

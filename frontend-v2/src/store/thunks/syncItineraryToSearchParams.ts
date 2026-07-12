import { addDays, format, parseISO } from 'date-fns';
import type { AppThunk } from '@/store';
import { setSearchFormParams as setFlightSearchFormParams } from '@/store/slices/flightBookingSlice';
import type { FlightSearchFormParams } from '@/store/slices/flightBookingSlice';
import type { SerializableAirportOption } from '@/store/slices/flightBookingSlice';
import { setLastFlightPath, setLastHotelPath } from '@/store/slices/uiSlice';
import {
  setSearchFormParams as setHotelSearchFormParams,
  setTripType as setHotelTripType,
} from '@/store/slices/hotelBookingSlice';
import { mapCabinClass } from '@/features/chat/utils/chatSearchParamsToUI';
import type { HotelSearchFormParams } from '@/types/hotels';
import { buildFlightSearchRedirectTarget } from '@/features/flights/utils/redirectToSearch';
import { serializeHotelSearchParamsToUrl } from '@/features/hotels/utils/urlParams';
import { ROUTES } from '@/features/routing';

export interface SyncItineraryPayload {
  origin?: string;
  destination?: string;
  departure_date?: string | null;
  return_date?: string | null;
  origin_iata?: string;
  destination_iata?: string;
  origin_name?: string;
  destination_name?: string;
  adults?: number;
  children?: number;
  infants?: number;
  trip_type?: 'round_trip' | 'one_way' | 'multi_city';
  cabin_class?: string;
  /** Skip hotel params update — used when multistay chain hydration handles hotels instead. */
  skipHotelSync?: boolean;
}

function toSerializableAirport(
  iata: string,
  name: string,
  city: string
): SerializableAirportOption {
  return {
    iata: iata.trim().toUpperCase(),
    name: name || city,
    city: city || '',
    country: '',
    isCityOption: true,
  };
}

export function syncItineraryToSearchParams(payload: SyncItineraryPayload): AppThunk {
  return (dispatch, getState) => {
    const { origin, destination, departure_date, return_date } = payload;
    const originIata = payload.origin_iata?.trim();
    const destinationIata = payload.destination_iata?.trim();
    const originName = payload.origin_name ?? origin ?? '';
    const destinationName = payload.destination_name ?? destination ?? '';
    const adults = payload.adults ?? 1;
    const children = payload.children ?? 0;
    const infants = payload.infants ?? 0;
    // Itinerary payloads aren't guaranteed to carry cabin_class; fall back to
    // Economy so the flights nav-bar chip never stays on the "Cabin" placeholder
    // after an itinerary hydrates.
    const cabinClass = mapCabinClass(payload.cabin_class);
    const tripTypeFromPayload =
      payload.trip_type === 'round_trip'
        ? 'round-trip'
        : payload.trip_type === 'one_way'
          ? 'one-way'
          : payload.trip_type === 'multi_city'
            ? 'multi-city'
            : return_date
              ? 'round-trip'
              : 'one-way';

    const state = getState();
    const currentFlightParams = state.flightBooking?.searchFormParams;
    const currentHotelParams = state.hotelBooking?.searchFormParams;
    // Don't override hotel params when multistay results are already loaded.
    const hotelIsMultistay =
      state.hotelBooking?.tripType === 'multi-stay' &&
      (state.hotelBooking?.multistayLegs ?? []).some(
        (l: { hotels: unknown[] }) => l.hotels.length > 0
      );
    // Flight: update whenever the itinerary carries a destination. Origin may
    // be empty (e.g. itineraries the user requested without naming a departure
    // city) — we still want to overwrite the form so a previous itinerary's
    // origin doesn't bleed into the new one. The user fills the gap.
    if (destination != null && destination !== '') {
      const flightParams: FlightSearchFormParams = {
        ...(currentFlightParams ?? {
          tripType: 'round-trip',
          from: '',
          to: '',
          date: null,
          returnDate: null,
          travellers: { adults: 1, children: 0, infants: 0, cabinClass: 'Economy' },
        }),
        from: origin ?? '',
        to: destination,
        // Discard the previous itinerary's fromAirport when the new itinerary
        // doesn't carry one — otherwise the "From" chip silently keeps the old
        // IATA option even though `from` is now empty.
        fromAirport: undefined,
        toAirport: undefined,
        date: departure_date ?? null,
        returnDate: return_date ?? null,
        tripType: tripTypeFromPayload,
        travellers: {
          ...(currentFlightParams?.travellers ?? {
            adults: 1,
            children: 0,
            infants: 0,
            cabinClass: 'Economy',
          }),
          adults,
          children,
          infants,
          cabinClass,
        },
        originIsCity: Boolean(origin),
        destinationIsCity: true,
      };

      if (originIata && originIata.length === 3 && origin) {
        flightParams.fromAirport = toSerializableAirport(
          originIata,
          originName,
          origin
        );
      }
      if (destinationIata && destinationIata.length === 3) {
        flightParams.toAirport = toSerializableAirport(
          destinationIata,
          destinationName,
          destination
        );
      }

      // Chat → nav-bar sync rule (see docs/CHAT_NAV_BAR_SYNC.md):
      // Always overwrite the form with the itinerary's trip. Whether the page
      // shows the cache or refetches is governed by the slice's `trusted` flag
      // — set by live-chat hydrators when they store cache from a chat payload,
      // and reset by `clearCachedFlightResults` / page-side fetches.
      dispatch(setFlightSearchFormParams(flightParams));

      // Re-read state here so we don't trust a stale snapshot — callers may
      // dispatch the trust-setting action (commitItineraryRichResultToUiState)
      // after this thunk, and the captured `state` would still see trusted=false.
      const flightTrusted =
        getState().flightBooking?.cachedFlightResultsTrusted === true;
      if (import.meta.env.DEV) {
        console.log('[ChatNavSync] flight branch', {
          payloadOrigin: origin,
          payloadDestination: destination,
          originIsEmpty: !origin,
          itineraryFlightParams: flightParams,
          flightCacheTrusted: flightTrusted,
        });
      }
      // Trusted cache → clean path so the page's mount-only effect runs and
      // honors the trust flag (renders cache, no API). Otherwise emit an
      // encoded `?q=` path that triggers the URL-restoration search.
      if (flightTrusted) {
        dispatch(setLastFlightPath(ROUTES.FLIGHTS_SEARCH));
      } else {
        dispatch(setLastFlightPath(buildFlightSearchRedirectTarget(flightParams)));
      }
    }

    // Hotel: skip if multistay results are already loaded OR caller requested skip.
    if (!payload.skipHotelSync && !hotelIsMultistay && destination != null && destination !== '') {
      // Itinerary results are always single-stay; promote tripType from null
      // (fresh-state) so the hotels nav-bar chip shows "Single stay" instead of
      // the "Stay type" placeholder.
      dispatch(setHotelTripType('single'));
      const childAge = children > 0 ? Array.from({ length: children }, () => 5) : [0];
      let checkout = return_date ?? null;
      if (departure_date && (!checkout || String(checkout).trim() === '')) {
        try {
          const d = parseISO(String(departure_date).slice(0, 10));
          if (!Number.isNaN(d.getTime())) {
            checkout = format(addDays(d, 1), 'yyyy-MM-dd');
          }
        } catch {
          // keep checkout as null
        }
      }
      const hotelParams: HotelSearchFormParams = {
        ...(currentHotelParams ?? {
          destination: '',
          checkin: null,
          checkout: null,
          rooms: [{ roomNo: 1, adult: 1, child: 0, childAge: [0] }],
          nationality: 'US',
        }),
        destination,
        checkin: departure_date ?? null,
        checkout,
        rooms: [{ roomNo: 1, adult: adults, child: children, childAge }],
      };

      // Always overwrite form. Cache trust is decided by the slice flag —
      // same model as the flight branch.
      dispatch(setHotelSearchFormParams(hotelParams));

      // Re-read state for the same reason as the flight branch above — the
      // trust flag may be set by a sibling dispatch that runs after this thunk.
      const hotelTrusted =
        getState().hotelBooking?.cachedHotelResultsTrusted === true;
      if (import.meta.env.DEV) {
        console.log('[ChatNavSync] hotel branch', {
          itineraryHotelParams: hotelParams,
          hotelCacheTrusted: hotelTrusted,
        });
      }

      if (hotelTrusted) {
        dispatch(setLastHotelPath(ROUTES.HOTELS_SEARCH));
      } else if (
        hotelParams.destination?.trim() &&
        hotelParams.checkin &&
        hotelParams.checkout
      ) {
        const encoded = serializeHotelSearchParamsToUrl(hotelParams);
        if (encoded) {
          dispatch(setLastHotelPath(`/hotels/search?q=${encodeURIComponent(encoded)}`));
        }
      }
    }
  };
}

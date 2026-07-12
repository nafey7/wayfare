/**
 * Cross-populate the *opposite* unified-nav-bar search-form params when chat
 * returns a flight-only or hotel-only result.
 *
 * - Flight result in chat → also pre-fill the hotel nav bar (destination,
 *   check-in/out, rooms). Gaps stay empty for the user to complete.
 * - Hotel result in chat → also pre-fill the flight nav bar (to, dates,
 *   travellers). Origin / cabin class stay empty for the user to complete.
 *
 * Cache rule (see `docs/CHAT_NAV_BAR_SYNC.md`): we never touch the opposite
 * slice's cache from here. Whether the opposite tab renders cached results or
 * fetches is governed by that slice's `cachedXxxResultsTrusted` flag, which is
 * set by live-chat hydrators when they store the cache. Helpers no-op when
 * the source payload lacks a destination so the fresh-state defaults (null
 * trip type, empty travellers, etc.) survive on a new chat.
 */
import { addDays, format, parseISO } from 'date-fns';
import type { AppThunk } from '@/store';
import {
  setSearchFormParams as setFlightSearchFormParams,
  type FlightSearchFormParams,
} from '@/store/slices/flightBookingSlice';
import {
  setSearchFormParams as setHotelSearchFormParams,
  setTripType as setHotelTripType,
} from '@/store/slices/hotelBookingSlice';
import { mapCabinClass } from '@/features/chat/utils/chatSearchParamsToUI';
import type {
  FlightSearchParams,
  HotelSearchParams,
} from '@/types/api.helpers';
import type { RoomOccupancy } from '@/types/hotels';

function nonEmpty(value: string | null | undefined): string {
  return typeof value === 'string' ? value.trim() : '';
}

function nextDayIso(iso: string | null | undefined): string | null {
  const checkin = nonEmpty(iso);
  if (!checkin) return null;
  try {
    const d = parseISO(checkin.slice(0, 10));
    if (Number.isNaN(d.getTime())) return null;
    return format(addDays(d, 1), 'yyyy-MM-dd');
  } catch {
    return null;
  }
}

function buildRooms(adults: number, children: number): RoomOccupancy[] {
  return [
    {
      roomNo: 1,
      adult: Math.max(1, adults),
      child: Math.max(0, children),
      childAge:
        children > 0 ? Array<number>(children).fill(5) : [0],
    },
  ];
}

/**
 * Populate the hotel nav bar from a flight chat result. No-op when the flight
 * params lack a destination.
 */
export function crossPopulateHotelFromFlightParams(
  flightParams: FlightSearchParams | null | undefined
): AppThunk {
  return (dispatch) => {
    if (!flightParams) return;
    const destination = nonEmpty(
      flightParams.destination_city ?? flightParams.destination
    );
    if (!destination) return;

    const checkin = nonEmpty(flightParams.departure_date) || null;
    const checkout =
      nonEmpty(flightParams.return_date) || nextDayIso(checkin);
    const adults = flightParams.passengers?.adults ?? 1;
    const children = flightParams.passengers?.children ?? 0;

    dispatch(
      setHotelSearchFormParams({
        destination,
        checkin,
        checkout,
        rooms: buildRooms(adults, children),
        nationality: 'US',
      })
    );
    dispatch(setHotelTripType('single'));
  };
}

/**
 * Variant of `crossPopulateHotelFromFlightParams` used by multicity chat
 * payloads where origin / destination / dates are carried per-leg.
 */
export function crossPopulateHotelFromTripBounds(bounds: {
  destination: string;
  checkin: string | null | undefined;
  checkout: string | null | undefined;
  adults?: number;
  children?: number;
}): AppThunk {
  return (dispatch) => {
    const destination = nonEmpty(bounds.destination);
    if (!destination) return;

    const checkin = nonEmpty(bounds.checkin) || null;
    const checkout = nonEmpty(bounds.checkout) || nextDayIso(checkin);
    const adults = bounds.adults ?? 1;
    const children = bounds.children ?? 0;

    dispatch(
      setHotelSearchFormParams({
        destination,
        checkin,
        checkout,
        rooms: buildRooms(adults, children),
        nationality: 'US',
      })
    );
    dispatch(setHotelTripType('single'));
  };
}

/**
 * Populate the flight nav bar from a hotel chat result. Origin (`from`) is
 * intentionally left empty for the user to fill. Cabin class defaults to
 * Economy.
 */
export function crossPopulateFlightFromHotelParams(
  hotelParams: HotelSearchParams | null | undefined
): AppThunk {
  return (dispatch) => {
    if (!hotelParams) return;
    const destination = nonEmpty(
      hotelParams.destination_city ??
        hotelParams.city_name ??
        hotelParams.destination
    );
    if (!destination) return;

    const date =
      nonEmpty(hotelParams.check_in_date) || nonEmpty(hotelParams.checkin) || null;
    const returnDate =
      nonEmpty(hotelParams.check_out_date) ||
      nonEmpty(hotelParams.checkout) ||
      null;
    const adults = hotelParams.adults ?? 1;
    const children = hotelParams.children ?? 0;

    // NOTE: This intentionally replaces the flight search form wholesale rather
    // than merging with state.flightBooking.searchFormParams. As a result, any
    // user-set origin (`from`) is cleared and cabin class is reset to Economy,
    // since the hotel payload carries no equivalent fields. Origin is left
    // empty by design so the user is prompted to fill it; if we ever want to
    // preserve prior origin/cabin selections (mirroring how
    // syncItineraryToSearchParams composes flight params), merge with the
    // current flight searchFormParams here instead of replacing.
    const flightFormParams: FlightSearchFormParams = {
      tripType: returnDate ? 'round-trip' : 'one-way',
      from: '',
      to: destination,
      date,
      returnDate,
      travellers: {
        adults: Math.max(1, adults),
        children: Math.max(0, children),
        infants: 0,
        cabinClass: mapCabinClass(undefined),
      },
      destinationIsCity: true,
    };

    dispatch(setFlightSearchFormParams(flightFormParams));
  };
}

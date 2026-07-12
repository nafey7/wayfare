/**
 * Maps POST /hotels/trip-details (or a synthetic post-booking payload) to HotelBookingDetailsPanel props.
 * Shared by HotelBookingDetailsPage and HotelConfirmationPage for identical layout.
 */
import { differenceInCalendarDays, format, isValid } from 'date-fns';
import type { HotelBookingDetailsPanelProps } from '@/features/hotels/components/HotelBookingDetailsPanel';
import type { HotelBookingResponse, HotelTripDetailsResponse } from '@/types/hotels';
import { ROUTES } from '@/features/routing';
import {
  pickStr,
  parseDateLoose,
  formatStayDateLine,
  collectHotelImages,
  buildMapsHref,
  mapGuests,
  deriveShowPaymentApprovedChip,
  type HotelNextStepItem,
} from '@/features/hotels/utils/hotelBookingDetailsUtils';

export type HotelBookingDetailsPanelRestProps = Omit<
  HotelBookingDetailsPanelProps,
  'onShareReservation' | 'onDownloadInvoice' | 'onGoToHotelWebsite'
>;

export const DEFAULT_HOTEL_BOOKING_NEXT_STEPS: HotelNextStepItem[] = [
  { id: 'checkin-window', text: 'Check-in opens 24 hours before your stay', tone: 'default' },
  { id: 'reminders', text: "We'll send you reminders before your trip", tone: 'default' },
  {
    id: 'hotel-direct',
    text: 'Manage rooms and amenities directly with the hotels',
    tone: 'muted',
  },
];

function formatTripDetailPrice(amount: unknown, currency: string): string {
  if (amount == null) return '—';
  const n = typeof amount === 'number' ? amount : parseFloat(String(amount));
  return Number.isFinite(n) ? `${currency} ${n.toFixed(2)}` : String(amount);
}

/** Parses supplier `days` / `nights` strings; supports locale decimals like "1,0". Returns null for non-numeric text (e.g. "overnight"). */
function parseNightsCountFromDaysStr(daysStr: string): number | null {
  const trimmed = daysStr.trim();
  let n = Number(trimmed);
  if (!Number.isFinite(n)) {
    const normalized = trimmed.replace(/\s/g, '').replace(/,/g, '.');
    n = parseFloat(normalized);
  }
  return Number.isFinite(n) ? n : null;
}

/**
 * Build a trip-details-shaped payload from the immediate book-hotel response so the confirmation
 * screen can render the same panel before trip-details returns (or if it fails).
 */
export function syntheticTripDetailsFromBookingResult(
  br: HotelBookingResponse,
): HotelTripDetailsResponse {
  const h = br.hotel;
  const guestsForBd = (br.guests ?? []).map((g) => ({
    title: g.title,
    firstName: g.firstName,
    lastName: g.lastName,
    email: g.email,
    phone: g.phone,
  }));

  const imgList =
    h?.images && h.images.length > 0
      ? h.images
      : h?.imageUrl
        ? [h.imageUrl]
        : [];

  const bd: Record<string, unknown> = {
    hotelName: h?.name ?? 'Hotel',
    city: h?.city ?? '',
    address: h?.address ?? '',
    latitude: h?.latitude,
    longitude: h?.longitude,
    description: h?.description,
    images: imgList.length ? imgList : undefined,
    image: h?.imageUrl,
    checkIn: br.checkin,
    checkOut: br.checkout,
    // HotelBookingResponse.totalAmount is minor units (cents); major units would require removing /100.
    totalPrice: br.totalAmount != null ? br.totalAmount / 100 : undefined,
    currency: br.currency ?? 'USD',
    guests: guestsForBd,
    rooms: br.roomName ? [{ name: br.roomName }] : [],
    paymentMethod: 'Card',
    paymentDate: new Date().toISOString(),
    paymentStatus: 'succeeded',
  };

  return {
    success: true,
    voyaBookingReference: br.voyaBookingReference,
    bookingStatus: 'BOOKED',
    bookingDetails: bd,
    errors: null,
  };
}

export function hotelTripDetailsToPanelProps(
  detail: HotelTripDetailsResponse,
  bookingRef: string,
  nextStepsItems: HotelNextStepItem[] = DEFAULT_HOTEL_BOOKING_NEXT_STEPS,
): HotelBookingDetailsPanelRestProps | null {
  const bd = detail?.bookingDetails ?? {};
  const hasDetails = detail?.success && Object.keys(bd).length > 0;
  if (!hasDetails) return null;

  const checkIn = pickStr(bd, 'checkIn', 'check_in', 'checkInDate', 'check_in_date');
  const checkOut = pickStr(bd, 'checkOut', 'check_out', 'checkOutDate', 'check_out_date');
  const daysStr = pickStr(bd, 'days', 'nights');
  const currency = (bd.currency ?? bd.Currency ?? 'USD') as string;
  const totalPrice = bd.totalPrice ?? bd.total_price ?? bd.netPrice ?? bd.NetPrice;
  const hotelName =
    pickStr(bd, 'hotelName', 'hotel_name', 'name', 'Name') ?? 'Hotel';
  const city = pickStr(bd, 'city', 'hotelCity') ?? '';
  const addressOnly = pickStr(bd, 'address', 'hotelAddress', 'hotel_address');
  const distance = pickStr(bd, 'distanceFromCentre', 'distance_from_centre', 'distance');
  const addressLine = [addressOnly, distance ? `${distance} from centre` : null]
    .filter(Boolean)
    .join(', ');
  const description =
    pickStr(bd, 'description', 'hotelDescription', 'hotel_description') ?? null;
  const rooms = bd.rooms as Array<Record<string, unknown>> | undefined;
  const firstRoom = Array.isArray(rooms) && rooms.length > 0 ? rooms[0] : undefined;
  const roomTypeName = firstRoom
    ? String(firstRoom.name ?? firstRoom.roomName ?? firstRoom.roomType ?? 'Room')
    : pickStr(bd, 'roomType', 'room_type') ?? '—';
  const board = firstRoom
    ? (firstRoom.boardType ?? firstRoom.board_type ?? firstRoom.mealPlan)
    : null;
  const roomAmenityChip =
    board != null && board !== '' ? String(board) : pickStr(bd, 'mealPlan', 'meal_plan');

  const adultsRaw = bd.adults ?? bd.numberOfAdults ?? bd.number_of_adults;
  const adults =
    typeof adultsRaw === 'number'
      ? adultsRaw
      : adultsRaw != null
        ? parseInt(String(adultsRaw), 10)
        : null;
  const nightsAdultsParts: string[] = [];
  if (daysStr) {
    const n = parseNightsCountFromDaysStr(daysStr);
    if (n != null) {
      nightsAdultsParts.push(`${daysStr} ${n === 1 ? 'night' : 'nights'}`);
    } else {
      nightsAdultsParts.push(daysStr.trim());
    }
  } else if (checkIn && checkOut) {
    const d0 = parseDateLoose(checkIn);
    const d1 = parseDateLoose(checkOut);
    if (d0 && d1) {
      const nightCount = differenceInCalendarDays(d1, d0);
      nightsAdultsParts.push(`${nightCount} ${nightCount === 1 ? 'night' : 'nights'}`);
    }
  }
  if (adults != null && Number.isFinite(adults)) nightsAdultsParts.push(`${adults} adults`);
  const nightsAdultsLine = nightsAdultsParts.join('・') || '—';

  const confirmationEmail = pickStr(
    bd,
    'confirmationEmail',
    'confirmation_email',
    'email',
    'contactEmail',
    'contact_email',
    'guestEmail',
  );
  const reservationCode = (detail?.voyaBookingReference ?? bookingRef).toUpperCase();

  const paymentMethod =
    pickStr(bd, 'paymentMethod', 'payment_method', 'payment_type') ?? 'Payment';
  const paidAt = pickStr(bd, 'paymentDate', 'payment_date', 'paidAt', 'paid_at');
  const paymentTimestamp = paidAt
    ? (() => {
        const d = parseDateLoose(paidAt);
        return d && isValid(d) ? format(d, 'MMM d, yyyy, h:mm:ss a') : paidAt;
      })()
    : '';
  const paymentAmountFormatted = formatTripDetailPrice(totalPrice, currency);

  const hotelWebsiteUrl = pickStr(
    bd,
    'hotelWebsite',
    'hotel_website',
    'website',
    'hotel_url',
  );

  const showPaymentApprovedChip = deriveShowPaymentApprovedChip(detail, bd);

  return {
    headlineCity: city || hotelName,
    confirmationEmail,
    viewItineraryTo: ROUTES.ITINERARY,
    destinationTitle: city || hotelName,
    stayDateLine: formatStayDateLine(checkIn, checkOut, daysStr),
    hotelImageUrls: collectHotelImages(bd),
    hotelCity: city || null,
    hotelName,
    addressLine: addressLine ?? '',
    showOnMapHref: buildMapsHref(bd),
    hotelDescription: description,
    nightsAdultsLine,
    roomTypeName,
    roomAmenityChip,
    reservationCode,
    guests: mapGuests(bd),
    paymentMethodLabel: paymentMethod,
    paymentTimestamp,
    paymentAmountFormatted,
    paymentApproved: showPaymentApprovedChip,
    showPaymentSection: totalPrice != null,
    hotelWebsiteUrl,
    nextStepsItems,
  };
}

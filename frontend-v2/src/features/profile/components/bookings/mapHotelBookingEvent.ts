import type { HotelMyBookingListItem } from '@/types/hotels';
import {
  formatBookingAction,
  formatDateShort,
  formatHotelStayLabel,
  formatListAmountMajor,
  parseIso,
  type BookingListAction,
} from '@/features/profile/components/bookings/listFormatters';

export interface ProfileHotelBookingRowModel {
  reference: string | null;
  hotelImageUrl: string | null;
  /** Raw API name/city for Google Places fallback (same as hotel search cards). */
  hotelNameRaw: string | null;
  hotelCityRaw: string | null;
  summaryLine: string;
  locationLine: string | null;
  statusLabel: string;
  dateLabel: string | null;
  amountLabel: string | null;
  hotelNights: number | null;
  canNavigate: boolean;
  action: BookingListAction;
}

export function mapHotelMyBookingToRow(item: HotelMyBookingListItem): ProfileHotelBookingRowModel {
  const ref = item.voyaBookingReference ?? null;
  const name = item.hotelName?.trim();
  const city = item.hotelCity?.trim();
  const summaryLine = name && name.length > 0 ? name : 'Hotel booking';
  const locationLine = city && city.length > 0 ? city : null;
  const hotelNameRaw = name && name.length > 0 ? name : null;
  const hotelCityRaw = city && city.length > 0 ? city : null;

  const stayLabel = formatHotelStayLabel(
    item.hotelCheckInDate,
    item.hotelCheckOutDate,
    item.hotelNights,
  );
  const bookedAt = parseIso(item.dateBooked) ?? parseIso(item.timestamp);
  const bookedShort = bookedAt ? formatDateShort(bookedAt) : null;
  const dateLabel = stayLabel ?? bookedShort;

  return {
    reference: ref,
    hotelImageUrl: item.hotelImageUrl?.trim() ? item.hotelImageUrl : null,
    hotelNameRaw,
    hotelCityRaw,
    summaryLine,
    locationLine,
    statusLabel: formatBookingAction(item.action),
    dateLabel,
    amountLabel: formatListAmountMajor(item.amount),
    hotelNights: item.hotelNights ?? null,
    canNavigate: Boolean(ref && ref.length > 0),
    action: item.action,
  };
}

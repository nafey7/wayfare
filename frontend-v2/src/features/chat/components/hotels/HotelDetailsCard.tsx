import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Notification } from '@mantine/core';
import { zIndex } from '@/theme';
import { HotelCard } from '@/features/hotels/components/HotelCard';
import { useSelectHotelMutation, useGetRoomRatesMutation } from '@/api/hotelsApi';
import { useAppDispatch } from '@/store';
import {
  setSearchFormParams,
  setSessionId,
  setSelectedHotel,
  setRoomRatesResponse,
} from '@/store/slices/hotelBookingSlice';
import { clearActiveSavedItineraryIdForBooking } from '@/store/slices/uiSlice';
import { chatHotelSearchParamsToUI } from '@/features/hotels/utils/urlParams';
import { persistHotelRoomsContext } from '@/features/hotels/utils/hotelRoomsContextStorage';
import { usePublicChatConversionGate } from '@/features/chat/hooks/usePublicChatConversionGate';
import type { MappedHotel } from '@/features/chat/utils/hotelUtils';
import type { HotelItinerary } from '@/types/hotels';

export interface HotelSearchParams {
  check_in_date?: string;
  check_out_date?: string;
  checkout?: string;
  checkin?: string;
  rooms?: number;
  adults?: number;
  children?: number;
  destination_city?: string;
  city_name?: string;
  country?: string;
  country_name?: string;
}

function mappedHotelToHotelItinerary(m: MappedHotel): HotelItinerary {
  const perNight = m.per_night_price ?? m.total_price ?? 0;
  return {
    id: m.hotel_id,
    tokenId: m.token_id,
    name: m.hotel_name,
    address: m.address ?? '',
    city: m.city ?? '',
    country: m.country ?? '',
    starRating: m.hotel_rating ?? 0,
    latitude: 0,
    longitude: 0,
    startingPrice: {
      currency: m.currency ?? 'GBP',
      amount: m.total_price ?? 0,
      perNight,
    },
    thumbnailUrl: m.thumbnail_url ?? undefined,
    imageUrl: m.thumbnail_url ?? undefined,
    total: m.total_price,
    originalTotal: m.original_total_fare ?? undefined,
    platformFeePercentage: m.platform_fee_percentage ?? undefined,
    propertyType: m.property_type ?? undefined,
    fareType: m.fare_type ?? undefined,
    productId: m.product_id ?? undefined,
  };
}

function calculateNights(searchParams: HotelSearchParams): number {
  const checkIn = searchParams.check_in_date ?? searchParams.checkin;
  const checkOut = searchParams.check_out_date ?? searchParams.checkout;
  if (checkIn && checkOut) {
    const diff = Math.round(
      (new Date(checkOut).getTime() - new Date(checkIn).getTime()) / (1000 * 60 * 60 * 24)
    );
    return diff > 0 ? diff : 1;
  }
  return 1;
}

interface HotelDetailsCardProps {
  hotel: MappedHotel;
  searchParams?: HotelSearchParams;
  valueBadge?: string;
}

export function HotelDetailsCard({
  hotel,
  searchParams: searchParamsProp = {},
  valueBadge,
}: HotelDetailsCardProps) {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const [error, setError] = useState({ open: false, message: '' });
  const [isLoading, setIsLoading] = useState(false);
  const { ensureAuthenticated } = usePublicChatConversionGate();
  const [selectHotel] = useSelectHotelMutation();
  const [getRoomRates] = useGetRoomRatesMutation();

  const handleBookNow = async () => {
    if (!ensureAuthenticated('hotel_book_now')) return;
    dispatch(clearActiveSavedItineraryIdForBooking());
    const hotelId = hotel.hotel_id;
    const tokenId = hotel.token_id;
    const productId = hotel.product_id;
    if (!hotelId || !tokenId || !productId) {
      setError({ open: true, message: 'Hotel ID is missing. Please search for hotels again.' });
      return;
    }

    const sessionId = localStorage.getItem('hotelSessionId') ?? '';
    if (!sessionId) {
      setError({ open: true, message: 'Search session expired. Please run a new hotel search.' });
      return;
    }

    const selectedHotelDisplay: Record<string, unknown> = {};
    if (hotel.hotel_name) selectedHotelDisplay.hotel_name = hotel.hotel_name;
    if (hotel.address) selectedHotelDisplay.address = hotel.address;
    if (hotel.city) selectedHotelDisplay.city = hotel.city;
    if (hotel.country) selectedHotelDisplay.country = hotel.country;
    if (hotel.hotel_rating != null) selectedHotelDisplay.hotel_rating = hotel.hotel_rating;
    if (hotel.property_type) selectedHotelDisplay.property_type = hotel.property_type;
    if (hotel.thumbnail_url) selectedHotelDisplay.thumbnail_url = hotel.thumbnail_url;

    const searchParams: Record<string, unknown> = {};
    const checkIn = searchParamsProp.check_in_date ?? searchParamsProp.checkin;
    const checkOut = searchParamsProp.check_out_date ?? searchParamsProp.checkout;
    if (checkIn) searchParams.check_in_date = checkIn;
    if (checkOut) searchParams.check_out_date = checkOut;
    if (searchParamsProp.rooms != null) searchParams.rooms = searchParamsProp.rooms;
    if (searchParamsProp.adults != null) searchParams.adults = searchParamsProp.adults;
    if (searchParamsProp.children != null) searchParams.children = searchParamsProp.children;
    const dest = searchParamsProp.destination_city ?? searchParamsProp.city_name;
    if (dest) searchParams.destination_city = dest;
    const country = searchParamsProp.country ?? searchParamsProp.country_name;
    if (country) searchParams.country = country;

    setIsLoading(true);
    try {
      await selectHotel({
        sessionId,
        tokenId,
        productId,
        hotelId,
        selectedHotelDisplay: Object.keys(selectedHotelDisplay).length > 0 ? selectedHotelDisplay : undefined,
        searchParams: Object.keys(searchParams).length > 0 ? searchParams : undefined,
      }).unwrap();

      const uiParams = chatHotelSearchParamsToUI(searchParamsProp);
      dispatch(setSearchFormParams(uiParams));
      dispatch(setSessionId(sessionId));

      const hotelItinerary = mappedHotelToHotelItinerary(hotel);
      dispatch(setSelectedHotel({ hotel: hotelItinerary, tokenId, productId, hotelId }));

      const roomRatesResult = await getRoomRates({ sessionId, tokenId, productId, hotelId }).unwrap();
      dispatch(setRoomRatesResponse(roomRatesResult));

      persistHotelRoomsContext({
        tokenId,
        sessionId,
        productId,
        hotelId,
        selectedHotel: mappedHotelToHotelItinerary(hotel),
        searchFormParams: uiParams,
      });

      navigate(`/hotels/rooms/${encodeURIComponent(tokenId)}`);
    } catch (err) {
      const errorMessage =
        (err as { data?: { detail?: string } })?.data?.detail ||
        'Unable to book this hotel. Please try again.';
      setError({ open: true, message: errorMessage });
    } finally {
      setIsLoading(false);
    }
  };

  const hotelItinerary = mappedHotelToHotelItinerary(hotel);
  const nights = calculateNights(searchParamsProp);

  return (
    <>
      {error.open && (
        <Notification
          color="red"
          title="Error"
          onClose={() => setError({ open: false, message: '' })}
          withCloseButton
          style={{
            position: 'fixed',
            top: 16,
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: zIndex.detailModal,
            maxWidth: 480,
          }}
        >
          {error.message}
        </Notification>
      )}
      <HotelCard
        hotel={hotelItinerary}
        nights={nights}
        onSelect={() => { void handleBookNow(); }}
        isSelecting={isLoading}
        valueBadge={valueBadge}
        tripAdvisorRating={hotel.trip_advisor_rating ?? null}
        tripAdvisorReviews={hotel.trip_advisor_reviews ?? null}
      />
    </>
  );
}

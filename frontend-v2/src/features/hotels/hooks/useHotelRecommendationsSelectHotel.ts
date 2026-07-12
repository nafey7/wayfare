import { useCallback, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGetRoomRatesMutation } from '@/api/hotelsApi';
import { useAppDispatch } from '@/store';
import {
  setRoomRatesResponse,
  setSearchFormParams,
  setSelectedHotel,
  setSessionId,
} from '@/store/slices/hotelBookingSlice';
import { showErrorToastFromError } from '@/utils/toast';
import type { ExtractedHotelSearchData } from '@/types/api.helpers';
import type { Hotel, HotelItinerary } from '@/types/hotels';
import { chatHotelSearchParamsToUI } from '@/features/hotels/utils/urlParams';
import { persistHotelRoomsContext } from '@/features/hotels/utils/hotelRoomsContextStorage';

/**
 * Shared hotel-select flow for recommendations map (desktop and mobile overlay).
 * Handles getRoomRates, Redux dispatch, persist context, and navigation.
 */
export function useHotelRecommendationsSelectHotel(hotelSearchData: ExtractedHotelSearchData) {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const [getRoomRates] = useGetRoomRatesMutation();
  const [selectingTokenId, setSelectingTokenId] = useState<string | null>(null);

  const searchFormParams = useMemo(
    () =>
      chatHotelSearchParamsToUI(
        hotelSearchData.data.search_params as Record<string, unknown>
      ),
    [hotelSearchData]
  );

  const handleSelectHotel = useCallback(
    async (hotel: Hotel | HotelItinerary) => {
      const sessionId = hotelSearchData.session_id?.trim() ?? '';
      const it = hotel as HotelItinerary;
      const tokenId = hotel.tokenId ?? hotel.id;
      const productId = it.productId ?? '';
      const hotelId = hotel.id;
      if (!sessionId || !productId || !hotelId) {
        showErrorToastFromError(
          new Error('Missing session or hotel details. Please run the search again from chat.')
        );
        return;
      }
      setSelectingTokenId(tokenId);
      try {
        const roomRatesResult = await getRoomRates({
          sessionId,
          tokenId,
          productId,
          hotelId,
        }).unwrap();
        dispatch(setSearchFormParams(searchFormParams));
        dispatch(setSessionId(sessionId));
        dispatch(
          setSelectedHotel({
            hotel: it,
            tokenId,
            productId: it.productId ?? null,
            hotelId,
          })
        );
        dispatch(setRoomRatesResponse(roomRatesResult));
        persistHotelRoomsContext({
          tokenId,
          sessionId,
          productId,
          hotelId,
          selectedHotel: it,
          searchFormParams,
        });
        navigate(`/hotels/rooms/${encodeURIComponent(tokenId)}`);
      } catch (err) {
        showErrorToastFromError(err);
      } finally {
        setSelectingTokenId(null);
      }
    },
    [dispatch, getRoomRates, hotelSearchData.session_id, navigate, searchFormParams]
  );

  return { handleSelectHotel, selectingTokenId };
}

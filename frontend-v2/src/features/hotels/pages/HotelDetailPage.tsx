import { useCallback, useEffect, useRef, useState } from 'react';
import { trackEvent } from '@/utils/gtm';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { Alert, Box, Container, Group, Loader, Stack } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';

import { useAppDispatch, useAppSelector } from '@/store';
import {
  setStep,
  setSelectedRoom,
  setRateRules,
  setInternalSessionId,
  setError,
  setSessionId,
  setSelectedHotel,
  setRoomRatesResponse,
  setSearchFormParams,
  setMultistayLegSelection,
  selectSelectedHotel,
  selectHotelSessionId,
  selectHotelProductId,
  selectHotelId,
  selectHotelTokenId,
  selectHotelSearchFormParams,
  selectHotelInternalSessionId,
  selectHotelBookingError,
  selectRoomRatesResponse,
  selectMultistayLegs,
} from '@/store/slices/hotelBookingSlice';
import { useGetRateRulesMutation, useGetRoomRatesMutation } from '@/api/hotelsApi';
import { showErrorToastFromError } from '@/utils/toast';
import { devLog } from '@/utils/devLog';
import { loadHotelRoomsContext } from '../utils/hotelRoomsContextStorage';
import { formatHotelDate, getHotelStayNights } from '../utils';
import type { RoomRate } from '@/types/hotels';

import {
  HotelDetailHeader,
  ImageGallery,
  HotelAmenities,
  HotelReserveCard,
  HotelLocationMap,
  HotelDetailNavBar,
  HOTEL_DETAIL_NAV_SECTION_IDS,
  HOTEL_DETAIL_NAV_SCROLL_IDS,
  HotelRoomsSection,
  type HotelDetailNavSectionId,
} from '../components/hotelDetail';
import {
  amenityStringsToColumns,
  buildGalleryImageList,
  buildRoomsAndGuestsLabel,
  buildStayPriceRangeLabel,
  getHotelDisplayName,
  hotelSearchFacilityLabels,
} from '../components/hotelDetail/hotelDetailDisplayUtils';
import { buildHotelRoomSelectedEventPayload } from '../components/hotelDetail/hotelDetailBookingAnalytics';

/**
 * Hotel detail + room selection for a hotel.
 * Route: /hotels/rooms/:tokenId
 */
export function HotelDetailPage() {
  const { tokenId: tokenIdParam } = useParams<{ tokenId: string }>();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const [searchParams] = useSearchParams();
  const multistayLegIndex = searchParams.get('leg') !== null ? Number(searchParams.get('leg')) : null;
  const isMultistay = multistayLegIndex !== null && !Number.isNaN(multistayLegIndex);
  const multistayLegs = useAppSelector(selectMultistayLegs);

  const selectedHotel = useAppSelector(selectSelectedHotel);
  const sessionId = useAppSelector(selectHotelSessionId);
  const productId = useAppSelector(selectHotelProductId);
  const hotelId = useAppSelector(selectHotelId);
  const tokenId = useAppSelector(selectHotelTokenId);
  const searchFormParams = useAppSelector(selectHotelSearchFormParams);
  const internalSessionId = useAppSelector(selectHotelInternalSessionId);
  const bookingError = useAppSelector(selectHotelBookingError);
  const roomRatesResponse = useAppSelector(selectRoomRatesResponse);

  const [getRateRules, { isLoading: isValidatingRate }] = useGetRateRulesMutation();
  const [getRoomRates] = useGetRoomRatesMutation();
  const isLg = useMediaQuery('(min-width: 1200px)') ?? false;

  const [selectingRateBasisId, setSelectingRateBasisId] = useState<string | null>(null);
  const refetchStartedRef = useRef(false);
  const hotelSelectedTrackedRef = useRef(false);

  /** New route token → allow a fresh room-rates fetch (avoids stale `refetchStartedRef` from a prior token). */
  useEffect(() => {
    refetchStartedRef.current = false;
  }, [tokenIdParam]);

  /** New token or hotel → fire `hotel_selected` again when rates are ready. */
  useEffect(() => {
    hotelSelectedTrackedRef.current = false;
  }, [tokenIdParam, hotelId]);

  const [activeSectionId, setActiveSectionId] = useState<HotelDetailNavSectionId>(
    HOTEL_DETAIL_NAV_SECTION_IDS.overview,
  );

  /** Sync tab underline with scroll position (last section whose top is above the activation line). */
  useEffect(() => {
    if (HOTEL_DETAIL_NAV_SCROLL_IDS.length === 0) return;
    const firstId = HOTEL_DETAIL_NAV_SCROLL_IDS[0];
    if (!firstId) return;

    const topActivationLinePx = 120;
    const updateActiveFromScroll = () => {
      let next: HotelDetailNavSectionId = firstId;
      for (const id of HOTEL_DETAIL_NAV_SCROLL_IDS) {
        const el = document.getElementById(id);
        if (!el) continue;
        if (el.getBoundingClientRect().top <= topActivationLinePx) {
          next = id;
        }
      }
      setActiveSectionId((prev) => (prev === next ? prev : next));
    };
    window.addEventListener('scroll', updateActiveFromScroll, { passive: true });
    window.addEventListener('resize', updateActiveFromScroll);
    const raf = window.requestAnimationFrame(updateActiveFromScroll);
    return () => {
      window.cancelAnimationFrame(raf);
      window.removeEventListener('scroll', updateActiveFromScroll);
      window.removeEventListener('resize', updateActiveFromScroll);
    };
  }, []);

  const checkin = searchFormParams.checkin;
  const checkout = searchFormParams.checkout;
  const nights = getHotelStayNights(checkin, checkout);

  const hasRequiredContext =
    selectedHotel &&
    sessionId &&
    productId &&
    hotelId &&
    tokenIdParam &&
    tokenId === tokenIdParam;

  const hasCachedRoomRates =
    hasRequiredContext &&
    roomRatesResponse?.tokenId === tokenIdParam &&
    roomRatesResponse?.sessionId === sessionId;

  useEffect(() => {
    if (!hasRequiredContext || !hasCachedRoomRates || !selectedHotel || hotelSelectedTrackedRef.current)
      return;
    hotelSelectedTrackedRef.current = true;
    trackEvent('hotel_selected', {
      hotel_name: getHotelDisplayName(selectedHotel, ''),
      nights,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `nights` intentionally omitted: one-shot when hotel becomes viewable; ref prevents duplicate events; including `nights` only re-runs without changing tracking behavior
  }, [hasRequiredContext, hasCachedRoomRates, selectedHotel]);

  useEffect(() => {
    if (hasRequiredContext && hasCachedRoomRates) {
      dispatch(setStep('rooms'));
      dispatch(setError(null));
      return;
    }

    if (!tokenIdParam) {
      navigate('/hotels/search', { replace: true });
      return;
    }

    if (!hasRequiredContext) {
      const ctx = loadHotelRoomsContext(tokenIdParam);
      if (!ctx) {
        navigate('/hotels/search', { replace: true });
        return;
      }
      dispatch(setSessionId(ctx.sessionId));
      dispatch(
        setSelectedHotel({
          hotel: ctx.selectedHotel,
          tokenId: ctx.tokenId,
          productId: ctx.productId,
          hotelId: ctx.hotelId,
        }),
      );
      dispatch(setSearchFormParams(ctx.searchFormParams));
      refetchStartedRef.current = true;
      getRoomRates({
        sessionId: ctx.sessionId,
        tokenId: ctx.tokenId,
        productId: ctx.productId,
        hotelId: ctx.hotelId,
      })
        .unwrap()
        .then((result) => {
          dispatch(setRoomRatesResponse(result));
          dispatch(setStep('rooms'));
          dispatch(setError(null));
        })
        .catch(() => {
          showErrorToastFromError(new Error('Session expired. Please search again.'));
          navigate('/hotels/search', { replace: true });
        });
      return;
    }

    if (!hasCachedRoomRates && sessionId && productId && hotelId && !refetchStartedRef.current) {
      refetchStartedRef.current = true;
      getRoomRates({
        sessionId,
        tokenId: tokenIdParam,
        productId,
        hotelId,
      })
        .unwrap()
        .then((result) => {
          dispatch(setRoomRatesResponse(result));
          dispatch(setStep('rooms'));
          dispatch(setError(null));
        })
        .catch(() => {
          showErrorToastFromError(new Error('Could not load room rates. Please try again.'));
          navigate('/hotels/search', { replace: true });
        });
      return;
    }

    if (refetchStartedRef.current) return;

    navigate('/hotels/search', { replace: true });
  }, [
    hasRequiredContext,
    hasCachedRoomRates,
    tokenIdParam,
    sessionId,
    productId,
    hotelId,
    navigate,
    dispatch,
    getRoomRates,
  ]);

  const handleSelectRoom = useCallback(
    async (room: RoomRate) => {
      if (!sessionId || !tokenIdParam || !productId) return;
      const rateBasisId = room.rateBasisId;
      devLog('hotel booking (select room, before getRateRules)', {
        rateBasisId,
        sessionId,
        productId,
      });
      setSelectingRateBasisId(rateBasisId);
      dispatch(setError(null));

      const internalId = internalSessionId ?? crypto.randomUUID();

      try {
        const result = await getRateRules({
          sessionId,
          tokenId: tokenIdParam,
          productId,
          rateBasisId,
          internalSessionId: internalId,
        }).unwrap();
        devLog('hotel booking (stored in Redux after rate rules ok)', {
          rateBasisId,
          sessionId,
          productId,
        });
        trackEvent(
          'hotel_room_selected',
          buildHotelRoomSelectedEventPayload(room, nights),
        );

        if (isMultistay && multistayLegIndex !== null && selectedHotel) {
          // Multi-stay: store per-leg selection and return to search results
          const leg = multistayLegs[multistayLegIndex];
          dispatch(
            setMultistayLegSelection({
              legIndex: multistayLegIndex,
              hotel: selectedHotel,
              tokenId: tokenIdParam,
              productId,
              hotelId: hotelId ?? '',
              room,
              rateRules: result,
              internalSessionId: internalId,
              roomRatesResponse: roomRatesResponse ?? null,
              currency: leg?.currency ?? result.currency ?? 'USD',
            })
          );
          navigate('/hotels/search');
        } else {
          // Single stay: normal flow
          dispatch(setSelectedRoom(room));
          dispatch(setRateRules(result));
          if (!internalSessionId) {
            dispatch(setInternalSessionId(internalId));
          }
          navigate('/hotels/guest-info');
        }
      } catch (err) {
        showErrorToastFromError(err);
        dispatch(setError('Rate no longer available. Please select another room.'));
      } finally {
        setSelectingRateBasisId(null);
      }
    },
    [sessionId, tokenIdParam, productId, hotelId, internalSessionId, getRateRules, dispatch, navigate, nights, isMultistay, multistayLegIndex, selectedHotel, multistayLegs, roomRatesResponse],
  );

  const handleNavigate = useCallback((sectionId: HotelDetailNavSectionId) => {
    setActiveSectionId(sectionId);
    document.getElementById(sectionId)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, []);

  if (!hasRequiredContext || !hasCachedRoomRates) {
    return (
      <Container size="lg" py="xl">
        <Loader />
      </Container>
    );
  }

  const rooms: RoomRate[] = roomRatesResponse?.rooms ?? [];

  const displayName = getHotelDisplayName(selectedHotel);
  const amenityLabels = hotelSearchFacilityLabels(selectedHotel);
  const { columnOne, columnTwo } = amenityStringsToColumns(amenityLabels);
  const galleryImageList = buildGalleryImageList(selectedHotel, rooms);
  const galleryImages = galleryImageList.slice(0, 5);
  const extraPhotoCount = Math.max(0, galleryImageList.length - 5);

  return (
    <Box
      py="sm"
      px="sm"
      style={{
        minHeight: '100vh',
        backgroundColor: 'var(--mantine-color-body)',
      }}
    >
      <Stack gap="md" mx="auto" style={{ maxWidth: 1100 }}>
        <HotelDetailHeader hotelName={displayName} />

        <HotelDetailNavBar activeSectionId={activeSectionId} onNavigate={handleNavigate} />

        <Stack gap="md">
          <Stack component="section" id={HOTEL_DETAIL_NAV_SECTION_IDS.overview} gap="md">
            <ImageGallery
              id={HOTEL_DETAIL_NAV_SECTION_IDS.photos}
              images={galleryImages}
              hotelName={displayName}
              city={selectedHotel.city}
              address={selectedHotel.address}
              morePhotosLabel={extraPhotoCount > 0 ? `${extraPhotoCount}+` : 'Photos'}
              onMorePhotosClick={
                extraPhotoCount > 0
                  ? () =>
                      document
                        .getElementById(HOTEL_DETAIL_NAV_SECTION_IDS.photos)
                        ?.scrollIntoView({ behavior: 'smooth', block: 'start' })
                  : undefined
              }
            />

            <Group align="flex-start" gap="md" wrap="wrap">
              <Stack gap="md" style={{ flex: 1, minWidth: 0 }}>
                <Box component="section" id={HOTEL_DETAIL_NAV_SECTION_IDS.amenities}>
                  <HotelAmenities
                    columnOneItems={columnOne}
                    columnTwoItems={columnTwo}
                    totalAmenityCount={amenityLabels.length}
                  />
                </Box>
              </Stack>
              <Box
                style={{
                  width: '100%',
                  minWidth: 0,
                  flex: isLg ? '0 0 40%' : 'none',
                  alignSelf: isLg ? 'flex-start' : 'stretch',
                }}
              >
                <HotelReserveCard
                  checkInDate={formatHotelDate(checkin)}
                  checkOutDate={formatHotelDate(checkout)}
                  roomsAndGuestsLabel={buildRoomsAndGuestsLabel(searchFormParams.rooms)}
                  priceSectionTitle={rooms.length > 1 ? 'Price range:' : 'Price:'}
                  priceRangeLabel={buildStayPriceRangeLabel(rooms, nights)}
                  onEditDetails={() => navigate('/hotels/search')}
                />
              </Box>
            </Group>
          </Stack>

          <Box component="section" id={HOTEL_DETAIL_NAV_SECTION_IDS.location}>
            <HotelLocationMap
              latitude={selectedHotel.latitude}
              longitude={selectedHotel.longitude}
              markerTitle={displayName}
            />
          </Box>

          <Box component="section" id={HOTEL_DETAIL_NAV_SECTION_IDS.rooms}>
            {bookingError ? (
              <Alert color="red" mb="sm" withCloseButton onClose={() => dispatch(setError(null))}>
                {bookingError}
              </Alert>
            ) : null}
            <HotelRoomsSection
              rooms={rooms}
              stayNights={nights}
              onSelectRoom={handleSelectRoom}
              selectingRateBasisId={selectingRateBasisId}
              isValidatingRate={isValidatingRate}
            />
          </Box>
        </Stack>
      </Stack>
    </Box>
  );
}

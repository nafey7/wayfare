/**
 * Hotel confirmation page — booking confirmed.
 * Route: /hotels/confirmation
 * Uses the same layout as /hotels/bookings/:bookingRef (HotelBookingDetailsPanel).
 */
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Alert, Badge, Box, Button, Group, Loader, Stack, Text, Title } from '@mantine/core';
import { ArrowLeft } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { selectIsAuthenticated } from '@/store/slices/authSlice';
import {
  selectHotelBookingResult,
  clearConfirmationSession,
  selectHotelTripType,
  selectMultistayLegBookingResults,
} from '@/store/slices/hotelBookingSlice';
import { useGetHotelTripDetailsMutation } from '@/api/hotelsApi';
import type { HotelTripDetailsResponse } from '@/types/hotels';
import { HotelBookingDetailsPanel } from '@/features/hotels/components/HotelBookingDetailsPanel';
import {
  hotelTripDetailsToPanelProps,
  syntheticTripDetailsFromBookingResult,
} from '@/features/hotels/utils/hotelTripDetailsToPanelProps';
import { ROUTES } from '@/features/routing';

export function HotelConfirmationPage() {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const bookingResult = useAppSelector(selectHotelBookingResult);
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const tripType = useAppSelector(selectHotelTripType);
  const multistayLegBookingResults = useAppSelector(selectMultistayLegBookingResults);
  const isMultistay = tripType === 'multi-stay' && multistayLegBookingResults.length > 0;

  const [getTripDetails, { isLoading, isUninitialized }] = useGetHotelTripDetailsMutation();
  const [tripDetail, setTripDetail] = useState<HotelTripDetailsResponse | null>(null);

  const shouldFetchTrip = Boolean(
    bookingResult?.voyaBookingReference && isAuthenticated,
  );

  useEffect(() => {
    dispatch(clearConfirmationSession());
    try {
      sessionStorage.removeItem('hotelSessionId');
      sessionStorage.removeItem('hotelInternalSessionId');
    } catch {
      // Ignore
    }
  }, [dispatch]);

  useEffect(() => {
    if (!shouldFetchTrip || !bookingResult?.voyaBookingReference) {
      setTripDetail(null);
      return;
    }
    let cancelled = false;
    getTripDetails({ voyaBookingReference: bookingResult.voyaBookingReference })
      .unwrap()
      .then((res) => {
        if (!cancelled) setTripDetail(res ?? null);
      })
      .catch(() => {
        if (!cancelled) setTripDetail(null);
      });
    return () => {
      cancelled = true;
    };
  }, [shouldFetchTrip, bookingResult?.voyaBookingReference, getTripDetails]);

  useEffect(() => {
    if (!isMultistay && !bookingResult) {
      navigate('/hotels/search', { replace: true });
    }
  }, [isMultistay, bookingResult, navigate]);

  const panelProps = useMemo(() => {
    if (!bookingResult?.voyaBookingReference) return null;

    const ref = bookingResult.voyaBookingReference;
    const synthetic = syntheticTripDetailsFromBookingResult(bookingResult);

    if (!shouldFetchTrip) {
      return hotelTripDetailsToPanelProps(synthetic, ref);
    }

    const bd = tripDetail?.bookingDetails ?? {};
    const tripHasDetails =
      Boolean(tripDetail?.success) && bd && Object.keys(bd).length > 0;

    const source = tripHasDetails && tripDetail ? tripDetail : synthetic;
    return hotelTripDetailsToPanelProps(source, ref);
  }, [bookingResult, shouldFetchTrip, tripDetail]);

  // Multi-stay confirmation
  if (isMultistay) {
    return (
      <Box py="xl" mx="auto" style={{ width: '100%', maxWidth: 720 }}>
        <Title order={2} fw={700}>
          Booking Confirmed!
        </Title>
        <Text c="dimmed" mb="md">
          Your multi-stay booking is confirmed. All hotels have been reserved.
        </Text>
        <Stack gap="md" mb="xl">
          {multistayLegBookingResults.map((leg) => (
            <Box
              key={leg.legIndex}
              p="md"
              style={{
                borderRadius: 8,
                border: '1px solid var(--mantine-color-green-6)',
                backgroundColor: 'var(--mantine-color-green-1)',
              }}
            >
              <Text fw={700}>
                Stay {leg.legIndex + 1}{leg.hotelName ? `: ${leg.hotelName}` : ''}
              </Text>
              {leg.hotelCity && (
                <Text size="sm" c="dimmed">
                  {leg.hotelCity}
                </Text>
              )}
              <Group gap="xs" wrap="wrap" mt="xs">
                <Badge size="sm" color="green" variant="outline">
                  {`Booking ref: ${leg.voyaBookingReference}`}
                </Badge>
                {leg.externalBookingReference && (
                  <Badge size="sm" variant="outline">
                    {`Confirmation: ${leg.externalBookingReference}`}
                  </Badge>
                )}
              </Group>
            </Box>
          ))}
        </Stack>
        <Group gap="md" wrap="wrap">
          <Button component={Link} to={ROUTES.HOME}>
            Back to home
          </Button>
          <Button variant="outline" onClick={() => navigate('/hotels/search')}>
            Search more hotels
          </Button>
        </Group>
      </Box>
    );
  }

  if (!bookingResult) {
    return null;
  }

  const loadingTripDetails = shouldFetchTrip && (isUninitialized || isLoading);
  if (loadingTripDetails) {
    return (
      <Box py="xl" style={{ width: '100%' }}>
        <Group justify="center" py="xl">
          <Loader />
        </Group>
      </Box>
    );
  }

  if (!panelProps) {
    return (
      <Box py="xl" style={{ width: '100%' }}>
        <Alert color="yellow">
          We could not load your booking confirmation details. Try refreshing the page. If the
          problem continues, use Back to home and open your booking from the itinerary.
        </Alert>
        <Button
          component={Link}
          to={ROUTES.HOME}
          leftSection={<ArrowLeft size={16} />}
          variant="subtle"
          mt="md"
        >
          Back to home
        </Button>
      </Box>
    );
  }

  return (
    <Box py="xl" style={{ width: '100%' }}>
      <HotelBookingDetailsPanel {...panelProps} />
    </Box>
  );
}

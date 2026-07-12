/**
 * Hotel booking details page — view booking (e.g. from email link).
 * Route: /hotels/bookings/:bookingRef
 * Mirrors FlightBookingDetailsPage: auth_token exchange, ownership check, then load details.
 */
import { useEffect, useRef, useState } from 'react';
import { Link, useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { Alert, Box, Button, Group, Loader, Text } from '@mantine/core';
import { ArrowLeft } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { selectIsAuthenticated, setTokens, setUser } from '@/store/slices/authSlice';
import { useGetHotelTripDetailsMutation, useExchangeHotelBookingTokenMutation } from '@/api/hotelsApi';
import { useLazyGetMeQuery } from '@/api/usersApi';
import type { HotelTripDetailsResponse } from '@/types/hotels';
import { HotelBookingDetailsPanel } from '@/features/hotels/components/HotelBookingDetailsPanel';
import { hotelTripDetailsToPanelProps } from '@/features/hotels/utils/hotelTripDetailsToPanelProps';
import { ROUTES } from '@/features/routing';

const BackButton = () => (
  <Button
    component={Link}
    to={ROUTES.HOME}
    leftSection={<ArrowLeft size={16} />}
    variant="subtle"
  >
    Back to home
  </Button>
);

export function HotelBookingDetailsPage() {
  const { bookingRef } = useParams<{ bookingRef: string }>();
  const [searchParams] = useSearchParams();
  const authTokenFromUrl = searchParams.get('auth_token');
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const emailLinkExchangedRef = useRef(false);
  const [linkForDifferentAccount, setLinkForDifferentAccount] = useState(false);

  const [getTripDetails, { isLoading, error, isUninitialized }] = useGetHotelTripDetailsMutation();
  const [exchangeBookingToken] = useExchangeHotelBookingTokenMutation();
  const [getMe] = useLazyGetMeQuery();
  const [detail, setDetail] = useState<HotelTripDetailsResponse | null>(null);

  const isEmailLinkMode = Boolean(authTokenFromUrl);

  useEffect(() => {
    if (!isEmailLinkMode || !authTokenFromUrl || emailLinkExchangedRef.current) return;
    emailLinkExchangedRef.current = true;
    exchangeBookingToken({ authToken: authTokenFromUrl })
      .unwrap()
      .then((res) => {
        dispatch(setTokens({ accessToken: res.accessToken, refreshToken: res.refreshToken }));
        return getMe().unwrap();
      })
      .then((user) => {
        dispatch(setUser(user));
      })
      .catch((err: { status?: number }) => {
        if (err?.status === 403) {
          setLinkForDifferentAccount(true);
        }
      });
  }, [isEmailLinkMode, authTokenFromUrl, exchangeBookingToken, dispatch, getMe]);

  useEffect(() => {
    if (!isEmailLinkMode && !isAuthenticated) {
      navigate('/', { replace: true });
    }
  }, [isEmailLinkMode, isAuthenticated, navigate]);

  useEffect(() => {
    if (!bookingRef) return;
    if (linkForDifferentAccount) return;
    if (isEmailLinkMode && authTokenFromUrl && !isAuthenticated) return;
    if (!isEmailLinkMode && !isAuthenticated) return;

    let cancelled = false;
    getTripDetails({
      voyaBookingReference: bookingRef,
      ...(isEmailLinkMode && authTokenFromUrl ? { authToken: authTokenFromUrl } : {}),
    })
      .unwrap()
      .then((res) => {
        if (!cancelled) setDetail(res ?? null);
      })
      .catch(() => {
        if (!cancelled) setDetail(null);
      });

    return () => {
      cancelled = true;
    };
  }, [
    bookingRef,
    isEmailLinkMode,
    authTokenFromUrl,
    isAuthenticated,
    linkForDifferentAccount,
    getTripDetails,
  ]);

  if (!bookingRef) {
    return (
      <Box py="xl" style={{ width: '100%' }}>
        <Alert color="yellow">Missing booking reference.</Alert>
        <Box mt="md">
          <BackButton />
        </Box>
      </Box>
    );
  }

  if (isEmailLinkMode && authTokenFromUrl && !isAuthenticated) {
    return (
      <Box py="xl" style={{ width: '100%' }}>
        <Loader />
        <Text size="sm" c="dimmed" mt="md">
          Verifying your link…
        </Text>
        <Box mt="md">
          <BackButton />
        </Box>
      </Box>
    );
  }

  if (linkForDifferentAccount) {
    return (
      <Box py="xl" style={{ width: '100%' }}>
        <Alert color="yellow" mb="md">
          This link is for a different account. Sign out and open the link again, or use your own
          bookings.
        </Alert>
        <BackButton />
      </Box>
    );
  }

  const bd = detail?.bookingDetails ?? {};
  const hasDetails = detail?.success && Object.keys(bd).length > 0;
  const hasErrors = (detail?.errors?.length ?? 0) > 0;

  const panelRestProps =
    detail && bookingRef && hasDetails ? hotelTripDetailsToPanelProps(detail, bookingRef) : null;

  return (
    <Box py="xl" style={{ width: '100%' }}>
      {isUninitialized || isLoading ? (
        <Group justify="center" py="xl">
          <Loader />
        </Group>
      ) : error ? (
        <>
          <Alert color="red" mt="md">
            Failed to load booking. This reference may be invalid or not yet available.
          </Alert>
          <Box mt="md">
            <BackButton />
          </Box>
        </>
      ) : hasErrors && !hasDetails ? (
        <>
          <Alert color="yellow" mt="md">
            {detail?.errors?.[0] ?? 'Booking details returned errors.'}
          </Alert>
          <Box mt="md">
            <BackButton />
          </Box>
        </>
      ) : panelRestProps ? (
        <HotelBookingDetailsPanel {...panelRestProps} />
      ) : (
        <>
          <Alert color="yellow" mt="md">
            We could not display details for this booking.
          </Alert>
          <Box mt="md">
            <BackButton />
          </Box>
        </>
      )}
    </Box>
  );
}

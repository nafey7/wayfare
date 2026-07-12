import { useEffect, useMemo, useState } from 'react';
import { Link, useParams, useNavigate, useSearchParams, useLocation } from 'react-router-dom';
import {
  Alert,
  Badge,
  Box,
  Button,
  Card,
  Container,
  Divider,
  Group,
  Loader,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { ArrowLeft } from 'lucide-react';
import { useAppSelector } from '@/store/hooks';
import { selectIsAuthenticated } from '@/store/slices/authSlice';
import { useEmailLinkAuth } from '@/hooks/useEmailLinkAuth';
import {
  useGetTripDetailsMutation,
  useExchangeBookingTokenMutation,
  useGetMulticityBookingContextQuery,
} from '@/api/flightsApi';
import { useLazyGetMeQuery } from '@/api/usersApi';
import {
  formatCurrency,
  tripDetailsSegmentOutboundReturnLabels,
} from '../utils/flightUtils';
import { BookingDetailsRefCard } from '../components/booking/BookingDetailsRefCard';
import { BookingDetailsSegmentsCard } from '../components/booking/BookingDetailsSegmentsCard';

import type { TripDetailsSegmentCamel } from '@/types/flightBackend';

/** Trip details response (camelCase from API) */
interface TripDetailsFlightCamel {
  success?: boolean;
  voyaBookingReference?: string | null;
  /** Present when this booking is a multicity leg (from Mongo); avoids an extra multicity-context query when absent. */
  parentVoyaBookingReference?: string | null;
  externalBookingReference?: string;
  bookingStatus?: string;
  ticketStatus?: string;
  origin?: { iataCode?: string; airportName?: string; cityName?: string };
  destination?: { iataCode?: string; airportName?: string; cityName?: string };
  segments?: TripDetailsSegmentCamel[];
  pricing?: {
    fareTotals?: {
      totalFare?: { amount?: number | string; currency?: string };
      originalTotalFare?: { amount?: number | string; currency?: string };
    };
  };
  passengers?: Array<{ personalInfo?: { name?: { firstName?: string; lastName?: string } } }>;
  errors?: unknown[];
}

function parseFareAmount(amount: number | string | undefined | null): number {
  if (amount == null) return 0;
  if (typeof amount === 'number') return amount;
  const n = parseFloat(String(amount));
  return Number.isFinite(n) ? n : 0;
}

const BACK_BUTTON = (
  <Button
    component={Link}
    to="/home"
    leftSection={<ArrowLeft size={16} />}
    variant="subtle"
    px={0}
  >
    Back to home
  </Button>
);

/**
 * User-facing page: view flight booking details by VOYA reference.
 * Used for /flights/bookings/:bookingRef (e.g. from email link, with optional ?auth_token=...).
 */
export function FlightBookingDetailsPage() {
  const { bookingRef } = useParams<{ bookingRef: string }>();
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const authTokenFromUrl = searchParams.get('auth_token');
  const navigate = useNavigate();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);

  const [getTripDetails, { isLoading, error, isUninitialized }] = useGetTripDetailsMutation();
  const [exchangeBookingToken] = useExchangeBookingTokenMutation();
  const [getMe] = useLazyGetMeQuery();
  const [detail, setDetail] = useState<TripDetailsFlightCamel | null>(null);

  const navMulticity = location.state as {
    multicityGroupReference?: string;
    multicityLegBookingResults?: Array<{
      legIndex: number;
      voyaBookingReference: string;
      externalBookingReference?: string;
    }>;
  } | null;

  const isEmailLinkMode = Boolean(authTokenFromUrl);
  const { wrongAccount: linkForDifferentAccount } = useEmailLinkAuth({
    isEmailLinkMode,
    authTokenFromUrl,
    exchangeToken: exchangeBookingToken,
    getMe,
  });

  const canMulticityQuery =
    Boolean(bookingRef) &&
    !linkForDifferentAccount &&
    (!isEmailLinkMode || isAuthenticated);
  const hintMulticityFromNav = Boolean(
    navMulticity?.multicityGroupReference ||
      (navMulticity?.multicityLegBookingResults?.length ?? 0) > 0
  );
  const hintMulticityFromTripDetails = Boolean(detail?.parentVoyaBookingReference);
  const shouldFetchMulticityContext =
    canMulticityQuery && (hintMulticityFromNav || hintMulticityFromTripDetails);
  const { data: multicityApi } = useGetMulticityBookingContextQuery(
    { voyaBookingReference: bookingRef ?? '' },
    { skip: !shouldFetchMulticityContext }
  );

  const parentMulticityRef =
    multicityApi?.parentVoyaBookingReference ?? navMulticity?.multicityGroupReference ?? null;
  const multicityLegs =
    multicityApi?.legs?.length && multicityApi.legs.length > 0
      ? multicityApi.legs
      : navMulticity?.multicityLegBookingResults;
  const showMulticityCard =
    Boolean(parentMulticityRef) &&
    Array.isArray(multicityLegs) &&
    multicityLegs.length > 1;

  const segmentBoundLabels = useMemo(
    () =>
      detail?.segments && detail.segments.length > 0
        ? tripDetailsSegmentOutboundReturnLabels(detail.segments)
        : null,
    [detail?.segments],
  );

  // Require auth when not using email link
  useEffect(() => {
    if (!isEmailLinkMode && !isAuthenticated) {
      navigate('/', { replace: true });
    }
  }, [isEmailLinkMode, isAuthenticated, navigate]);

  // Load trip details only when allowed: not email-link, or email-link and we're the link's user (exchange succeeded). Never load when link is for another account (403).
  useEffect(() => {
    if (!bookingRef) return;
    if (linkForDifferentAccount) return;
    if (isEmailLinkMode && authTokenFromUrl && !isAuthenticated) return;
    if (!isEmailLinkMode && !isAuthenticated) return;
    getTripDetails({ voyaBookingReference: bookingRef })
      .unwrap()
      .then((res) => setDetail((res as TripDetailsFlightCamel) ?? null))
      .catch(() => setDetail(null));
  }, [bookingRef, isEmailLinkMode, authTokenFromUrl, isAuthenticated, linkForDifferentAccount, getTripDetails]);

  if (!bookingRef) {
    return (
      <Container size="md" py="xl">
        <Alert color="yellow">Missing booking reference.</Alert>
        <Box mt="md">{BACK_BUTTON}</Box>
      </Container>
    );
  }

  if (linkForDifferentAccount) {
    return (
      <Container size="md" py="xl">
        <Alert color="yellow" mb="md">
          This link is for a different account. Sign out and open the link again, or use your own
          bookings.
        </Alert>
        {BACK_BUTTON}
      </Container>
    );
  }

  if (isEmailLinkMode && authTokenFromUrl && !isAuthenticated) {
    return (
      <Container size="md" py="xl">
        <Loader />
        <Text size="sm" c="dimmed" mt="md">
          Verifying your link…
        </Text>
      </Container>
    );
  }

  const hasErrors = (detail?.errors?.length ?? 0) > 0;
  const totalFare =
    detail?.pricing?.fareTotals?.totalFare ?? detail?.pricing?.fareTotals?.originalTotalFare;
  const currency = totalFare?.currency ?? 'USD';
  const amount = parseFareAmount(totalFare?.amount);
  const ticketStatusStr =
    detail?.ticketStatus != null ? String(detail.ticketStatus).toLowerCase().trim() : '';
  const isTicketed = ticketStatusStr === 'ticketed';
  const bookingStatus = (detail?.bookingStatus ?? '').toLowerCase();
  const needsPayment =
    !isTicketed && (bookingStatus === 'pending' || bookingStatus === 'booked' || !detail?.bookingStatus);
  const paymentUrl = authTokenFromUrl
    ? `/flights/payment/${bookingRef}?auth_token=${encodeURIComponent(authTokenFromUrl)}`
    : `/flights/payment/${bookingRef}`;

  return (
    <Container size="lg" py="xl">
      <Box mb="md">{BACK_BUTTON}</Box>

      {showMulticityCard && parentMulticityRef && multicityLegs ? (
        <Card mb="md" p="lg" radius="md" withBorder>
          <Title order={6} fw={700}>
            Multi-city trip
          </Title>
          <Text size="sm" c="dimmed">
            Group reference
          </Text>
          <Text fw={600} mb="md">
            {parentMulticityRef}
          </Text>
          <Divider my="md" />
          <Text size="sm" c="dimmed" fw={500} mb={4}>
            Bookings by leg
          </Text>
          <Stack gap="sm">
            {multicityLegs.map((leg, idx) => {
              const voyaRef =
                'voyaBookingReference' in leg && typeof leg.voyaBookingReference === 'string'
                  ? leg.voyaBookingReference
                  : '';
              const legIndex =
                'legIndex' in leg && typeof (leg as { legIndex?: number }).legIndex === 'number'
                  ? (leg as { legIndex: number }).legIndex
                  : idx;
              const ticketSt =
                'ticketStatus' in leg && leg.ticketStatus != null
                  ? String(leg.ticketStatus)
                  : null;
              const isCurrent = voyaRef === bookingRef;
              const href =
                authTokenFromUrl && voyaRef
                  ? `/flights/bookings/${encodeURIComponent(voyaRef)}?auth_token=${encodeURIComponent(authTokenFromUrl)}`
                  : `/flights/bookings/${encodeURIComponent(voyaRef)}`;
              return (
                <Group
                  key={`${legIndex}-${voyaRef}`}
                  align="center"
                  gap="xs"
                  wrap="wrap"
                  p="sm"
                  style={{
                    borderRadius: 4,
                    backgroundColor: isCurrent
                      ? 'var(--mantine-color-gray-1)'
                      : 'var(--mantine-color-body)',
                    border: '1px solid var(--mantine-color-gray-3)',
                  }}
                >
                  <Text size="sm" c="dimmed" style={{ minWidth: 72 }}>
                    Leg {legIndex + 1}
                  </Text>
                  <Button
                    component={Link}
                    to={href}
                    size="xs"
                    variant={isCurrent ? 'filled' : 'outline'}
                    disabled={!voyaRef}
                  >
                    {voyaRef || '—'}
                  </Button>
                  {ticketSt && (
                    <Badge size="xs" color="navy.7" variant="outline">
                      {ticketSt}
                    </Badge>
                  )}
                </Group>
              );
            })}
          </Stack>
        </Card>
      ) : null}

      {isUninitialized || isLoading ? (
        <Group justify="center" py="xl">
          <Loader />
        </Group>
      ) : error ? (
        <Alert color="red" mt="md">
          Failed to load booking. This reference may be invalid or not yet available.
        </Alert>
      ) : hasErrors ? (
        <Alert color="yellow" mt="md">
          Booking details returned errors. The booking may not be available yet.
        </Alert>
      ) : detail ? (
        <>
          <BookingDetailsRefCard
            voyaBookingReference={detail.voyaBookingReference ?? bookingRef}
            externalBookingReference={detail.externalBookingReference}
            bookingStatus={detail.bookingStatus}
            ticketStatus={detail.ticketStatus}
            actions={
              needsPayment ? (
                <Button component={Link} to={paymentUrl}>
                  Pay now
                </Button>
              ) : null
            }
          />

          {detail.segments && detail.segments.length > 0 && (
            <BookingDetailsSegmentsCard
              segments={detail.segments}
              segmentBoundLabels={segmentBoundLabels}
            />
          )}

          {(!detail.segments || detail.segments.length === 0) &&
            detail.origin &&
            detail.destination && (
              <Card mb="md" p="lg" radius="md" withBorder>
                <Title order={6} fw={700}>
                  Route
                </Title>
                <Divider my="md" />
                <Text>
                  {detail.origin.iataCode} (
                  {detail.origin.cityName ?? detail.origin.airportName ?? ''}) →{' '}
                  {detail.destination.iataCode} (
                  {detail.destination.cityName ?? detail.destination.airportName ?? ''})
                </Text>
              </Card>
            )}

          {(amount > 0 || currency) && (
            <Card mb="md" p="lg" radius="md" withBorder>
              <Title order={6} fw={700}>
                Fare
              </Title>
              <Divider my="md" />
              <Group justify="space-between" align="center">
                <Text>Total fare</Text>
                <Title order={4} fw={700} c="navy.7">
                  {formatCurrency(amount, currency)}
                </Title>
              </Group>
            </Card>
          )}

          {detail.passengers && detail.passengers.length > 0 && (
            <Card mb="md" p="lg" radius="md" withBorder>
              <Title order={6} fw={700}>
                Passengers
              </Title>
              <Divider my="md" />
              <Stack gap={4}>
                {detail.passengers.map((p, i) => {
                  const name = p.personalInfo?.name;
                  const first = name?.firstName ?? '';
                  const last = name?.lastName ?? '';
                  const full = [first, last].filter(Boolean).join(' ') || `Passenger ${i + 1}`;
                  return <Text key={i}>{full}</Text>;
                })}
              </Stack>
            </Card>
          )}
        </>
      ) : null}
    </Container>
  );
}

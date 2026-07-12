import { useEffect, useMemo, useState } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import {
  Alert,
  Anchor,
  Box,
  Button,
  Card,
  Container,
  Divider,
  Group,
  Loader,
  Modal,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { ArrowLeft, RefreshCw } from 'lucide-react';
import { useAppSelector } from '@/store/hooks';
import { selectCurrentUser } from '@/store/slices/authSlice';
import { useGetTripDetailsMutation } from '@/api/flightsApi';
import {
  useGetAdminBookingEventByReferenceQuery,
  useAdminRetryBookingMutation,
} from '@/api/adminBookingsApi';
import { showErrorToastFromError, showSuccessToast } from '@/utils/toast';
import {
  formatCurrency,
  tripDetailsSegmentOutboundReturnLabels,
} from '@/features/flights/utils/flightUtils';

interface TripDetailsSegmentCamel {
  segmentId?: number;
  departureDatetime?: string | { value?: string };
  arrivalDatetime?: string | { value?: string };
  departureAirport?: { iataCode?: string; cityName?: string; airportName?: string };
  arrivalAirport?: { iataCode?: string; cityName?: string; airportName?: string };
  marketingFlightNumber?: {
    flightNumber?: string;
    formattedNumber?: string;
  };
  marketingAirline?: { airlineName?: string; iataCode?: string };
  operatingAirline?: { airlineName?: string };
}

interface TripDetailsFlightCamel {
  success?: boolean;
  voyaBookingReference?: string | null;
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

function parseSegmentDatetime(dt: string | { value?: string } | undefined): string | null {
  if (!dt) return null;
  if (typeof dt === 'string') return dt;
  return dt?.value ?? null;
}

/**
 * Admin-only page: view flight booking details by VOYA reference.
 */
export function AdminFlightBookingDetailPage() {
  const { voyaBookingReference } = useParams<{ voyaBookingReference: string }>();
  const navigate = useNavigate();
  const user = useAppSelector(selectCurrentUser);
  const [getTripDetails, { isLoading, error, isUninitialized }] =
    useGetTripDetailsMutation();
  const [detail, setDetail] = useState<TripDetailsFlightCamel | null>(null);
  const [retryDialogOpen, setRetryDialogOpen] = useState(false);

  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin';

  const { data: bookingEvent } = useGetAdminBookingEventByReferenceQuery(
    voyaBookingReference ?? '',
    { skip: !voyaBookingReference || !isAdmin }
  );

  const [retryBooking, { isLoading: isRetrying }] =
    useAdminRetryBookingMutation();

  useEffect(() => {
    if (user != null && !isAdmin) {
      navigate('/home', { replace: true });
    }
  }, [user, isAdmin, navigate]);

  useEffect(() => {
    if (!voyaBookingReference || !isAdmin) return;
    getTripDetails({ voyaBookingReference })
      .unwrap()
      .then((res) => setDetail((res as TripDetailsFlightCamel) ?? null))
      .catch(() => setDetail(null));
  }, [voyaBookingReference, isAdmin, getTripDetails]);

  const handleRetry = async () => {
    if (!bookingEvent?.id) return;
    try {
      await retryBooking({ bookingEventId: bookingEvent.id }).unwrap();
      showSuccessToast('Retry completed successfully.');
      const res = await getTripDetails({ voyaBookingReference: voyaBookingReference! }).unwrap();
      setDetail((res as TripDetailsFlightCamel) ?? null);
    } catch (err) {
      showErrorToastFromError(err, 'Retry failed.');
    }
  };

  const canRetry =
    bookingEvent?.eventType === 'FLIGHT' &&
    bookingEvent?.action === 'BOOKED' &&
    Boolean(bookingEvent?.id);

  const tripDetailsApiCompleted = !isLoading && !isUninitialized;
  const ticketStatusStr =
    detail?.ticketStatus != null ? String(detail.ticketStatus).toLowerCase().trim() : '';
  const isTicketed = ticketStatusStr === 'ticketed';
  const showRetryButton = canRetry && tripDetailsApiCompleted && !isTicketed;

  const segmentBoundLabels = useMemo(
    () =>
      detail?.segments && detail.segments.length > 0
        ? tripDetailsSegmentOutboundReturnLabels(detail.segments)
        : null,
    [detail?.segments]
  );

  if (user == null || !isAdmin) return null;

  if (!voyaBookingReference) {
    return (
      <Container size="md" py="lg">
        <Alert color="yellow">Missing VOYA booking reference.</Alert>
        <Button component={Link} to="/admin/bookings" leftSection={<ArrowLeft size={18} />} mt="md" tt="none">
          Back to bookings
        </Button>
      </Container>
    );
  }

  const hasErrors = (detail?.errors?.length ?? 0) > 0;
  const totalFare =
    detail?.pricing?.fareTotals?.totalFare ?? detail?.pricing?.fareTotals?.originalTotalFare;
  const currency = totalFare?.currency ?? 'USD';
  const amount = parseFareAmount(totalFare?.amount);

  return (
    <Container size="lg" py="lg">
      <Group justify="space-between" align="flex-start" gap="md" mb="md" wrap="wrap">
        <Button
          component={Link}
          to="/admin/bookings"
          leftSection={<ArrowLeft size={18} />}
          variant="subtle"
          tt="none"
        >
          Back to bookings
        </Button>
        <Group gap="md" align="center" wrap="wrap">
          <Anchor
            href="https://travelnext.biz/agents/bookingQueue"
            target="_blank"
            rel="noopener noreferrer"
            size="sm"
            fw={500}
          >
            Bookings overview
          </Anchor>
          <Anchor
            href="https://travelnext.biz/agents/ledgerStatement"
            target="_blank"
            rel="noopener noreferrer"
            size="sm"
            fw={500}
          >
            Account statement
          </Anchor>
          {showRetryButton && (
            <>
              <Button
                tt="none"
                fw={600}
                leftSection={isRetrying ? <Loader size={16} color="white" /> : <RefreshCw size={18} />}
                onClick={() => setRetryDialogOpen(true)}
                disabled={isRetrying}
              >
                {isRetrying ? 'Retrying…' : 'Retry'}
              </Button>
              <Modal
                opened={retryDialogOpen}
                onClose={() => !isRetrying && setRetryDialogOpen(false)}
                title="Confirm retry"
                centered
              >
                <Stack gap="md">
                  <Text size="sm">
                    Retry this flight booking? The booking will be retried with the supplier. This
                    action cannot be undone.
                  </Text>
                  <Group justify="flex-end" gap="xs">
                    <Button variant="subtle" tt="none" onClick={() => setRetryDialogOpen(false)} disabled={isRetrying}>
                      Cancel
                    </Button>
                    <Button
                      tt="none"
                      fw={600}
                      onClick={() => {
                        setRetryDialogOpen(false);
                        void handleRetry();
                      }}
                      disabled={isRetrying}
                    >
                      Retry
                    </Button>
                  </Group>
                </Stack>
              </Modal>
            </>
          )}
        </Group>
      </Group>

      {isUninitialized || isLoading ? (
        <Group justify="center" py="lg">
          <Loader />
        </Group>
      ) : error ? (
        <Alert color="red" mt="md">
          Failed to load trip details. This reference may be invalid or not yet available.
        </Alert>
      ) : hasErrors ? (
        <Alert color="yellow" mt="md">
          Trip details returned errors. The booking may not be available yet.
        </Alert>
      ) : detail ? (
        <Stack gap="lg">
          {/* Booking Reference Card */}
          <Card withBorder padding="lg" style={{ border: '2px solid var(--mantine-color-brand-6)' }}>
            <Title order={4} fw={700} mb="xs">
              Booking Reference
            </Title>
            <Divider mb="sm" />
            <Stack gap="xs">
              <Group align="baseline" gap="xs" wrap="wrap">
                <Text size="sm" c="dimmed" style={{ minWidth: 140 }}>
                  VOYA booking reference
                </Text>
                <Text size="md" fw={600}>
                  {detail.voyaBookingReference ?? voyaBookingReference}
                </Text>
              </Group>
              {detail.externalBookingReference && (
                <Group align="baseline" gap="xs" wrap="wrap">
                  <Text size="sm" c="dimmed" style={{ minWidth: 140 }}>
                    External reference
                  </Text>
                  <Text size="md" fw={600}>
                    {detail.externalBookingReference}
                  </Text>
                </Group>
              )}
              {detail.bookingStatus && (
                <Group align="baseline" gap="xs" wrap="wrap">
                  <Text size="sm" c="dimmed" style={{ minWidth: 140 }}>
                    Booking status
                  </Text>
                  <Text size="md" fw={600}>
                    {detail.bookingStatus}
                  </Text>
                </Group>
              )}
              {detail.ticketStatus && (
                <Group align="baseline" gap="xs" wrap="wrap">
                  <Text size="sm" c="dimmed" style={{ minWidth: 140 }}>
                    Ticket status
                  </Text>
                  <Text size="md" fw={600}>
                    {detail.ticketStatus}
                  </Text>
                </Group>
              )}
            </Stack>
          </Card>

          {/* Flight Details Card */}
          {detail.segments && detail.segments.length > 0 && (
            <Card withBorder padding="lg">
              <Title order={4} fw={700} mb="xs">
                Flight Details
              </Title>
              <Divider mb="sm" />
              {detail.segments.map((seg: TripDetailsSegmentCamel, idx: number) => {
                const bound = segmentBoundLabels?.[idx];
                const depIso = parseSegmentDatetime(seg.departureDatetime);
                const arrIso = parseSegmentDatetime(seg.arrivalDatetime);
                const depAirport = seg.departureAirport?.iataCode ?? '';
                const arrAirport = seg.arrivalAirport?.iataCode ?? '';
                const depCity =
                  seg.departureAirport?.cityName ?? seg.departureAirport?.airportName ?? depAirport;
                const arrCity =
                  seg.arrivalAirport?.cityName ?? seg.arrivalAirport?.airportName ?? arrAirport;
                const depTime = depIso
                  ? new Date(depIso).toLocaleTimeString('en-US', {
                      hour: '2-digit',
                      minute: '2-digit',
                    })
                  : '';
                const arrTime = arrIso
                  ? new Date(arrIso).toLocaleTimeString('en-US', {
                      hour: '2-digit',
                      minute: '2-digit',
                    })
                  : '';
                const depDate = depIso ? new Date(depIso).toLocaleDateString() : '';
                const airline =
                  seg.marketingAirline?.airlineName ??
                  seg.operatingAirline?.airlineName ??
                  'Unknown';
                const flightNumberDisplay =
                  seg.marketingFlightNumber?.formattedNumber ??
                  seg.marketingFlightNumber?.flightNumber ??
                  '';

                const borderColor =
                  bound === 'RETURN'
                    ? 'var(--mantine-color-grape-6)'
                    : bound === 'OUTBOUND'
                      ? 'var(--mantine-color-brand-6)'
                      : 'var(--mantine-color-gray-4)';
                return (
                  <Box
                    key={idx}
                    p="md"
                    mb="md"
                    style={{
                      backgroundColor: 'var(--mantine-color-gray-0)',
                      borderRadius: 8,
                      borderLeft: `3px solid ${borderColor}`,
                    }}
                  >
                    {(detail.segments?.length ?? 0) > 1 && bound && (
                      <Text
                        fw={600}
                        size="sm"
                        mb="xs"
                        style={{
                          color:
                            bound === 'RETURN'
                              ? 'var(--mantine-color-grape-6)'
                              : 'var(--mantine-color-brand-6)',
                        }}
                      >
                        {bound}
                      </Text>
                    )}
                    <Text size="md" fw={600}>
                      {depDate} · {depTime} {depCity} ({depAirport}) → {arrTime} {arrCity} ({arrAirport})
                    </Text>
                    <Text size="sm" c="dimmed" mt={2}>
                      {flightNumberDisplay ? `${airline} ${flightNumberDisplay}` : airline}
                    </Text>
                  </Box>
                );
              })}
            </Card>
          )}

          {/* Route summary when no segments */}
          {(!detail.segments || detail.segments.length === 0) &&
            detail.origin &&
            detail.destination && (
              <Card withBorder padding="lg">
                <Title order={4} fw={700} mb="xs">
                  Route
                </Title>
                <Divider mb="sm" />
                <Text size="md">
                  {detail.origin.iataCode} ({detail.origin.cityName ?? detail.origin.airportName ?? ''}) →{' '}
                  {detail.destination.iataCode} (
                  {detail.destination.cityName ?? detail.destination.airportName ?? ''})
                </Text>
              </Card>
            )}

          {/* Pricing Card */}
          {(amount > 0 || currency) && (
            <Card withBorder padding="lg">
              <Title order={4} fw={700} mb="xs">
                Fare
              </Title>
              <Divider mb="sm" />
              <Group justify="space-between" align="center">
                <Text size="md">Total fare</Text>
                <Title order={3} fw={700} c="brand.6">
                  {formatCurrency(amount, currency)}
                </Title>
              </Group>
              <Text size="sm" c="dimmed" mt="xs">
                {currency.toUpperCase()}
              </Text>
            </Card>
          )}

          {/* Passengers */}
          {detail.passengers && detail.passengers.length > 0 && (
            <Card withBorder padding="lg">
              <Title order={4} fw={700} mb="xs">
                Passengers
              </Title>
              <Divider mb="sm" />
              {detail.passengers.map((p, i) => {
                const name = p.personalInfo?.name;
                const first = name?.firstName ?? '';
                const last = name?.lastName ?? '';
                const full = [first, last].filter(Boolean).join(' ') || `Passenger ${i + 1}`;
                return (
                  <Text key={i} size="md" py={4}>
                    {full}
                  </Text>
                );
              })}
            </Card>
          )}
        </Stack>
      ) : null}
    </Container>
  );
}

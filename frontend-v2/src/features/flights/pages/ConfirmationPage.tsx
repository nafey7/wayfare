import { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Badge,
  Box,
  Button,
  Card,
  Container,
  Divider,
  Group,
  Loader,
  Text,
  Title,
} from '@mantine/core';
import { CheckCircle } from 'lucide-react';
import { useAppSelector } from '@/store/hooks';
import {
  selectBookingResult,
  selectMulticityGroupReference,
  selectMulticityLegBookingResults,
  selectRevalidationResponse,
  selectSearchFormParams,
} from '@/store/slices/flightBookingSlice';
import { buildFlightSearchRedirectTarget } from '../utils/redirectToSearch';
import { parseConfirmationPageState } from '../utils/bookingNavigationState';
import { useGetRevolutTransactionQuery } from '@/api/revolutPaymentsApi';
import {
  formatCurrencyFromCents,
  roundTripBoundLabelPerVendorLeg,
} from '../utils/flightUtils';
import type { ValidatedFareItineraryCamel } from '@/types/flightBackend';
import { BookingReferenceCard } from '../components/booking/BookingReferenceCard';
import { BookingFlightLegsCard } from '../components/booking/BookingFlightLegsCard';

/**
 * Confirmation Page
 * Shows booking reference, trip details, and payment status
 */
export function ConfirmationPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const state = parseConfirmationPageState(location.state) ?? null;

  const reduxBookingResult = useAppSelector(selectBookingResult);
  const searchFormParams = useAppSelector(selectSearchFormParams);
  const multicityLegsRedux = useAppSelector(selectMulticityLegBookingResults);
  const multicityGroupRedux = useAppSelector(selectMulticityGroupReference);
  const bookingResult = state?.bookingResult ?? reduxBookingResult;
  const paymentIntentId = state?.paymentIntentId;
  const multicityLegs =
    state?.multicityLegBookingResults ?? multicityLegsRedux ?? null;
  const multicityGroup =
    state?.multicityGroupReference ?? multicityGroupRedux ?? null;
  const revalidationResponse = useAppSelector(selectRevalidationResponse);

  // Get Revolut transaction status (paymentIntentId is Revolut order_id)
  const { data: transaction } = useGetRevolutTransactionQuery(paymentIntentId || '', {
    skip: !paymentIntentId,
  });

  useEffect(() => {
    if (!bookingResult) {
      navigate(buildFlightSearchRedirectTarget(searchFormParams), { replace: true });
    }
  }, [bookingResult, searchFormParams, navigate]);

  if (!bookingResult) {
    return (
      <Container size="lg" py="xl">
        <Loader />
      </Container>
    );
  }

  const currency = bookingResult.currency ?? transaction?.currency ?? 'USD';
  // Prefer Revolut transaction amount (source of truth for actual charge, always in cents).
  // Fall back to bookingResult.totalAmount when transaction unavailable (e.g. email-link flow).
  // If backend ever returns major units by mistake, transaction.amount ensures correct display.
  const totalAmountPaid = (() => {
    const txAmount = transaction?.amount;
    const bookingAmount = bookingResult.totalAmount;
    if (txAmount != null && txAmount > 0) return txAmount;
    if (bookingAmount != null && bookingAmount > 0) return bookingAmount;
    return 0;
  })();

  // Extract flight details from revalidation response (camelCase from API transform)
  const itinerary: ValidatedFareItineraryCamel | undefined =
    revalidationResponse?.validatedFareItineraries?.[0];
  const flightLegs = itinerary?.flightLegs ?? [];
  const isRoundTripLayout = flightLegs.length > 1;
  const rtLegBounds = roundTripBoundLabelPerVendorLeg(flightLegs);

  const status = bookingResult.status ?? '';
  const isConfirmed = status === 'confirmed' || status === 'ticketed';
  const isPending = status === 'pending';
  const statusColor = isConfirmed ? 'green' : isPending ? 'yellow' : 'gray';
  const statusMessage = isConfirmed
    ? 'Your booking is confirmed and tickets have been issued.'
    : isPending
      ? 'Your booking is being processed.'
      : 'Please check back later for updates.';

  return (
    <Container size="lg" py="xl">
      {/* Success Header */}
      <Box ta="center" mb="xl">
        <CheckCircle size={80} color="var(--mantine-color-green-6)" style={{ marginBottom: 16 }} />
        <Title order={3} fw={700} mb="xs">
          Booking Confirmed!
        </Title>
        <Text size="lg" c="dimmed">
          Your flight has been successfully booked
        </Text>
      </Box>

      <BookingReferenceCard
        voyaBookingReference={bookingResult.voyaBookingReference}
        externalBookingReference={bookingResult.externalBookingReference}
        multicityLegs={multicityLegs}
        multicityGroupReference={multicityGroup}
        paymentStatus={transaction?.status}
      />

      {itinerary && (
        <BookingFlightLegsCard
          flightLegs={flightLegs}
          isRoundTripLayout={isRoundTripLayout}
          rtLegBounds={rtLegBounds}
        />
      )}

      {/* Payment Summary */}
      <Card mb="md" p="lg" radius="md" withBorder>
        <Title order={6} fw={700}>
          Payment Summary
        </Title>
        <Divider my="md" />
        <Group justify="space-between" align="center">
          <Text>Total Amount Paid</Text>
          <Title order={4} fw={700} c="green.6">
            {formatCurrencyFromCents(totalAmountPaid, currency)}
          </Title>
        </Group>
        <Text size="sm" c="dimmed" mt={4}>
          {currency.toUpperCase()}
        </Text>
      </Card>

      {/* Booking Status */}
      <Card mb="md" p="lg" radius="md" withBorder>
        <Title order={6} fw={700}>
          Booking Status
        </Title>
        <Divider my="md" />
        <Group align="center" gap="md">
          <Badge color={statusColor} fw={600}>
            {(bookingResult.status ?? 'confirmed').toUpperCase()}
          </Badge>
          <Text size="sm" c="dimmed">
            {statusMessage}
          </Text>
        </Group>
      </Card>

      {/* Actions */}
      <Group justify="center" gap="md" mt="xl">
        <Button
          size="md"
          radius="md"
          fw={600}
          onClick={() => navigate('/home')}
          px="xl"
        >
          Back to Home
        </Button>
        <Button
          size="md"
          variant="outline"
          radius="md"
          fw={600}
          onClick={() => navigate('/flights/search')}
          px="xl"
        >
          Book Another Flight
        </Button>
      </Group>
    </Container>
  );
}

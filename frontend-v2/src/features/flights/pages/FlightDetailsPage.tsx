import { useEffect, useRef } from 'react';
import { useNavigate, useLocation, useParams } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '@/store';
import {
  selectSearchFormParams,
  selectRevalidationResponse,
  selectSelectedFlightData,
  selectMulticitySelectedLegs,
  setRevalidationResponse,
  setSelectedFlightData,
  type MulticityLegSelection,
} from '@/store/slices/flightBookingSlice';
import {
  aggregateMulticityFare,
  getSortedMulticityLegSelections,
  hasMulticitySelection,
} from '../utils/multicityPricing';
import { buildFlightSearchRedirectTarget } from '../utils/redirectToSearch';
import { parseFlightBookingState } from '../utils/bookingNavigationState';
import { FLIGHT_DETAILS_MULTICITY_SEGMENT } from '@/features/routing/constants';
import { trackEvent } from '@/utils/gtm';
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
import {
  processLeg,
  formatCurrency,
  parseFareFromRevalidateResponse,
  type ProcessedLeg,
} from '../utils/flightUtils';
import type {
  FarePricingCamel,
  FareTotalsCamel,
  PassengerFareBreakdownItemCamel,
} from '@/types/flightBackend';
import { FlightDetailsItineraryCard } from '../components/booking/FlightDetailsItineraryCard';
import { FlightDetailsPriceBreakdownCard } from '../components/booking/FlightDetailsPriceBreakdownCard';

/**
 * Flight Details Page
 * Displays flight details and price breakdown after revalidation
 */
export function FlightDetailsPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { fareSourceCode: fareSourceCodeParam } = useParams<{
    fareSourceCode: string;
  }>();
  const dispatch = useAppDispatch();
  const searchFormParams = useAppSelector(selectSearchFormParams);
  const reduxRevalidationResponse = useAppSelector(selectRevalidationResponse);
  const reduxSelectedFlightData = useAppSelector(selectSelectedFlightData);
  const multicitySelectedLegs = useAppSelector(selectMulticitySelectedLegs);

  const segmentCount = searchFormParams.segments?.length ?? 0;
  const isMulticityTrip =
    searchFormParams.tripType === 'multi-city' && segmentCount >= 2;
  const hasMcSelection =
    isMulticityTrip && hasMulticitySelection(multicitySelectedLegs);

  const state = parseFlightBookingState(location.state) ?? null;
  const revalidateResponse = state?.revalidateResponse ?? reduxRevalidationResponse;
  const selectedFlightData = state?.selectedFlightData ?? reduxSelectedFlightData;

  // Sync to Redux when receiving via location.state (enables tab-switch persistence)
  useEffect(() => {
    if (state?.revalidateResponse) {
      dispatch(setRevalidationResponse(state.revalidateResponse));
    }
    if (state?.selectedFlightData) {
      dispatch(setSelectedFlightData(state.selectedFlightData));
    }
  }, [state?.revalidateResponse, state?.selectedFlightData, dispatch]);

  // Reserved `/flights/details/multicity` URL must not be used for one-way / round-trip flows.
  useEffect(() => {
    if (fareSourceCodeParam !== FLIGHT_DETAILS_MULTICITY_SEGMENT) return;
    if (!isMulticityTrip) {
      navigate(buildFlightSearchRedirectTarget(searchFormParams), { replace: true });
    }
  }, [fareSourceCodeParam, isMulticityTrip, searchFormParams, navigate]);

  // If no data (state or Redux), redirect to search. Multicity: require at least one leg selected.
  useEffect(() => {
    if (isMulticityTrip && !hasMcSelection) {
      navigate(buildFlightSearchRedirectTarget(searchFormParams), { replace: true });
      return;
    }
    if (hasMcSelection) return;
    if (!revalidateResponse || !selectedFlightData) {
      navigate(buildFlightSearchRedirectTarget(searchFormParams), { replace: true });
    }
  }, [
    isMulticityTrip,
    hasMcSelection,
    revalidateResponse,
    selectedFlightData,
    searchFormParams,
    navigate,
  ]);

  // GTM funnel: flight_selected, flight_fare_validated (on mount when details are shown)
  const funnelTrackedRef = useRef(false);
  useEffect(() => {
    if (funnelTrackedRef.current) return;
    if (hasMcSelection) {
      funnelTrackedRef.current = true;
      const { totalAmount, currency } = aggregateMulticityFare(multicitySelectedLegs);
      trackEvent('flight_selected', {
        total_price: totalAmount,
        currency,
        booking_type: 'multicity',
      });
      trackEvent('flight_fare_validated', {
        total_price: totalAmount,
        currency,
        booking_type: 'multicity',
      });
      return;
    }
    if (!revalidateResponse || !selectedFlightData) return;
    funnelTrackedRef.current = true;
    const { amount: totalFare, currency } = parseFareFromRevalidateResponse(revalidateResponse);
    const itinerary = revalidateResponse.validatedFareItineraries?.[0];
    const pricing = itinerary?.updatedPricing ?? itinerary?.pricing;
    const fareType = pricing?.fareType;
    trackEvent('flight_selected', {
      total_price: totalFare,
      currency,
      booking_type: fareType === 'WebFare' ? 'LCC' : 'GDS',
    });
    trackEvent('flight_fare_validated', {
      total_price: totalFare,
      currency,
      booking_type: fareType === 'WebFare' ? 'LCC' : 'GDS',
    });
  }, [
    hasMcSelection,
    multicitySelectedLegs,
    revalidateResponse,
    selectedFlightData,
  ]);

  if (isMulticityTrip && !hasMcSelection) {
    return (
      <Container size="lg" py="xl">
        <Loader />
      </Container>
    );
  }

  if (!hasMcSelection && (!revalidateResponse || !selectedFlightData)) {
    return (
      <Container size="lg" py="xl">
        <Loader />
      </Container>
    );
  }

  if (hasMcSelection) {
    const sortedLegs = getSortedMulticityLegSelections(multicitySelectedLegs);
    const {
      totalAmount,
      currency: aggCurrency,
      hasMixedCurrencies: mcMixedCurrency,
    } = aggregateMulticityFare(multicitySelectedLegs);
    const firstLeg = sortedLegs[0] as MulticityLegSelection;

    return (
      <Container size="lg" py="xl">
        <Title order={2} fw={700}>
          Multi-city trip
        </Title>
        <Text size="sm" c="dimmed" mb="md">
          One fare per leg; one payment after passenger details. Each leg may be ticketed as GDS or
          LCC depending on the airline.
        </Text>

        {mcMixedCurrency && (
          <Alert color="red" mb="md">
            Selected legs use different currencies. Combined checkout needs one currency — go back and
            change a leg.
          </Alert>
        )}

        {sortedLegs.map((leg: MulticityLegSelection, idx: number) => {
          const { amount: legFare, currency: legCur } = parseFareFromRevalidateResponse(
            leg.revalidateResponse
          );
          const displayLeg = leg.selectedFlightData.legs?.[0];
          const itineraryMc = leg.revalidateResponse.validatedFareItineraries?.[0];
          const pricingMc = itineraryMc?.updatedPricing ?? itineraryMc?.pricing;
          const ft = pricingMc?.fareType;
          const isLegLcc = ft === 'WebFare';

          return (
            <Card key={leg.legIndex} mb="sm" p="lg" radius="md" withBorder>
              <Text fw={600} mb={4}>
                Leg {idx + 1}
              </Text>
              {displayLeg ? (
                <Group justify="space-between" align="center" wrap="wrap" gap="md">
                  <Box>
                    <Text fw={600}>
                      {displayLeg.departure.airport} → {displayLeg.arrival.airport}
                    </Text>
                    <Text size="sm" c="dimmed">
                      {displayLeg.departure.date} · {displayLeg.departure.time} –{' '}
                      {displayLeg.arrival.time}
                    </Text>
                  </Box>
                  <Box ta="right">
                    <Text size="sm" c="dimmed">
                      {isLegLcc ? 'LCC' : 'GDS'}
                    </Text>
                    <Title order={6} fw={700}>
                      {formatCurrency(legFare, legCur)}
                    </Title>
                  </Box>
                </Group>
              ) : (
                <Text size="sm" c="dimmed">
                  Flight details unavailable for this leg.
                </Text>
              )}
            </Card>
          );
        })}

        <Card
          mb="md"
          p="lg"
          radius="md"
          style={{ border: '2px solid var(--mantine-color-navy-7)' }}
        >
          <Title order={6} fw={700}>
            Combined total
          </Title>
          <Divider my="md" />
          <Group justify="space-between" align="center">
            <Text>All legs (incl. platform fee per leg)</Text>
            <Title
              order={3}
              fw={700}
              style={{
                background: 'linear-gradient(to right, var(--mantine-color-navy-7), var(--mantine-color-grape-6))',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
              }}
            >
              {formatCurrency(totalAmount, aggCurrency)}
            </Title>
          </Group>
        </Card>

        <Group justify="center" mt="xl">
          <Button
            size="lg"
            radius="md"
            fw={600}
            disabled={mcMixedCurrency}
            px="xl"
            styles={{ root: { fontSize: '1.125rem' } }}
            onClick={() => {
              dispatch(setRevalidationResponse(firstLeg.revalidateResponse));
              dispatch(setSelectedFlightData(firstLeg.selectedFlightData));
              navigate('/flights/passenger-info', {
                state: {
                  revalidateResponse: firstLeg.revalidateResponse,
                  selectedFlightData: firstLeg.selectedFlightData,
                  searchSessionId: firstLeg.sessionId,
                },
              });
            }}
          >
            Complete passenger details
          </Button>
        </Group>
      </Container>
    );
  }

  if (!revalidateResponse || !selectedFlightData) {
    return (
      <Container size="lg" py="xl">
        <Loader />
      </Container>
    );
  }

  // Extract itinerary and pricing data (camelCase from API transform)
  const itinerary = revalidateResponse.validatedFareItineraries?.[0];
  const pricing: FarePricingCamel | undefined =
    itinerary?.updatedPricing ?? itinerary?.pricing;
  const fareTotals: FareTotalsCamel | undefined =
    pricing?.validatedFareTotals ?? pricing?.fareTotals;
  const passengerBreakdown: PassengerFareBreakdownItemCamel[] =
    pricing?.passengerFareBreakdown ?? [];
  const flightLegs = itinerary?.flightLegs ?? [];

  const { amount: totalFare, currency } = parseFareFromRevalidateResponse(revalidateResponse);
  const baseFare = fareTotals?.baseFare?.amount != null ? Number(fareTotals.baseFare.amount) : 0;
  const totalTax = fareTotals?.totalTax?.amount != null ? Number(fareTotals.totalTax.amount) : 0;

  const platformFeePercentage = fareTotals?.platformFeePercentage ?? 5;
  const originalTotalFare =
    fareTotals?.originalTotalFare?.amount != null
      ? Number(fareTotals.originalTotalFare.amount)
      : totalFare * (1 - platformFeePercentage / 100);
  const ticketsAmount = originalTotalFare;
  const platformFee = totalFare - ticketsAmount;

  const fareType = pricing?.fareType;
  const isLCC = fareType === 'WebFare';
  const isRefundable = pricing?.isRefundable ?? false;

  const isRoundTrip = flightLegs.length > 1;
  const processedLegs = flightLegs
    .map((leg, legIndex) => processLeg(leg, legIndex, isRoundTrip))
    .filter((leg: ProcessedLeg | null): leg is ProcessedLeg => leg !== null);

  return (
    <Container size="lg" py="xl">
      <FlightDetailsItineraryCard processedLegs={processedLegs} />

      <FlightDetailsPriceBreakdownCard
        baseFare={baseFare}
        totalTax={totalTax}
        ticketsAmount={ticketsAmount}
        platformFee={platformFee}
        platformFeePercentage={platformFeePercentage}
        totalFare={totalFare}
        currency={currency}
      />

      {/* Fare Information Card */}
      <Card mb="md" p="lg" radius="md" withBorder>
        <Title order={5} fw={700}>
          Fare Information
        </Title>
        <Divider my="md" />

        <Group gap="sm" wrap="wrap">
          <Badge color="navy.7" variant="filled" fw={600}>
            {isLCC ? 'LCC (Low Cost Carrier)' : 'GDS (Global Distribution System)'}
          </Badge>
          <Badge
            color={isRefundable ? 'navy.7' : 'gray'}
            variant="filled"
            fw={600}
          >
            {isRefundable ? 'Refundable' : 'Non-Refundable'}
          </Badge>
          <Badge color="navy.7" variant="filled" fw={600}>
            {`Fare Type: ${fareType || 'Standard'}`}
          </Badge>
        </Group>

        <Box
          mt="md"
          p="sm"
          style={{
            backgroundColor: isLCC
              ? 'var(--mantine-color-grape-1)'
              : 'var(--mantine-color-navy-1)',
            borderRadius: 8,
            borderLeft: `3px solid ${isLCC ? 'var(--mantine-color-grape-6)' : 'var(--mantine-color-navy-7)'}`,
          }}
        >
          <Text size="sm" fw={600} mb={4}>
            {isLCC ? '⚡ LCC Process' : '🏢 GDS Process'}:
          </Text>
          <Text size="sm">
            {isLCC
              ? 'Payment → Immediate Booking Confirmation'
              : 'Create Booking → Payment → Issue Ticket (or Cancel if payment fails)'}
          </Text>
        </Box>
      </Card>

      {/* Passenger Breakdown (if available) */}
      {passengerBreakdown.length > 0 && (
        <Card mb="md" p="lg" radius="md" withBorder>
          <Title order={5} fw={700}>
            Passenger Breakdown
          </Title>
          <Divider my="md" />

          <Stack gap="sm">
            {passengerBreakdown.map((pax: PassengerFareBreakdownItemCamel, index: number) => {
              const paxType = pax.passengerTypeInfo;
              const paxFare = pax.individualPassengerFare;
              const quantity = paxType?.passengerCount ?? paxType?.quantity ?? 1;
              const typeLabel =
                paxType?.passengerType === 'ADULT'
                  ? 'Adult'
                  : paxType?.passengerType === 'CHILD'
                    ? 'Child'
                    : paxType?.passengerType === 'INFANT'
                      ? 'Infant'
                      : String(paxType?.passengerType ?? 'Passenger');

              const baseFareTotal = Number(paxFare?.baseFare?.amount ?? 0);
              const taxTotal = Number(paxFare?.totalTax?.amount ?? 0);
              const totalFareTotal = Number(paxFare?.totalFare?.amount ?? 0);
              const paxCurrency = paxFare?.totalFare?.currency ?? currency;

              return (
                <Box
                  key={index}
                  p="sm"
                  style={{
                    backgroundColor: 'var(--mantine-color-gray-0)',
                    borderRadius: 8,
                    borderLeft: '3px solid var(--mantine-color-navy-7)',
                  }}
                >
                  <Group justify="space-between" mb={4}>
                    <Text fw={600} size="sm">
                      {quantity}x {typeLabel}
                      {quantity > 1 ? 's' : ''}
                    </Text>
                    <Text fw={600} size="sm">
                      {formatCurrency(totalFareTotal, paxCurrency)}
                    </Text>
                  </Group>
                  <Group justify="space-between">
                    <Text size="xs" c="dimmed">
                      Base Fare (total):
                    </Text>
                    <Text size="xs" c="dimmed">
                      {formatCurrency(baseFareTotal, paxCurrency)}
                    </Text>
                  </Group>
                  <Group justify="space-between">
                    <Text size="xs" c="dimmed">
                      Taxes & Fees (total):
                    </Text>
                    <Text size="xs" c="dimmed">
                      {formatCurrency(taxTotal, paxCurrency)}
                    </Text>
                  </Group>
                </Box>
              );
            })}
          </Stack>
        </Card>
      )}

      {/* Fare Rules / Penalties (if available) */}
      {passengerBreakdown.some((fb: PassengerFareBreakdownItemCamel) => fb.penaltyDetails) && (
        <Card mb="md" p="lg" radius="md" withBorder>
          <Title order={5} fw={700}>
            📋 Fare Rules & Penalties
          </Title>
          <Divider my="md" />

          <Stack gap="sm">
            {passengerBreakdown.map((fb: PassengerFareBreakdownItemCamel, index: number) => {
              if (!fb.penaltyDetails) return null;

              const info = fb.passengerTypeInfo;
              const paxType = String(info?.passengerType ?? '');
              const count = Number(info?.quantity ?? info?.passengerCount ?? 1);
              let passengerType = '';
              let icon = '👤';

              if (paxType === 'ADT') {
                passengerType = count > 1 ? 'Adults' : 'Adult';
                icon = '👨';
              } else if (paxType === 'CHD') {
                passengerType = count > 1 ? 'Children' : 'Child';
                icon = '👧';
              } else if (paxType === 'INF') {
                passengerType = count > 1 ? 'Infants' : 'Infant';
                icon = '👶';
              } else {
                passengerType = paxType || 'Passenger';
              }

              const penalty = fb.penaltyDetails;
              const cancellationFee =
                penalty?.cancellationPenalty != null
                  ? formatCurrency(
                      Number(penalty.cancellationPenalty.amount ?? 0),
                      penalty.cancellationPenalty.currency ?? 'USD'
                    )
                  : 'N/A';
              const changeFee =
                penalty?.changePenalty != null
                  ? formatCurrency(
                      Number(penalty.changePenalty.amount ?? 0),
                      penalty.changePenalty.currency ?? 'USD'
                    )
                  : 'N/A';
              const isCancelAllowed = penalty?.isCancellationAllowed;
              const isChangeAllowed = penalty?.isChangeAllowed;

              return (
                <Box
                  key={index}
                  p="sm"
                  style={{
                    backgroundColor: 'var(--mantine-color-gray-0)',
                    borderRadius: 8,
                    borderLeft: '3px solid var(--mantine-color-gray-5)',
                  }}
                >
                  <Text fw={600} size="sm" mb={4}>
                    {icon} {count}x {passengerType}
                  </Text>
                  <Group justify="space-between" mb={4}>
                    <Text size="sm" c="dimmed">
                      Cancellation:
                    </Text>
                    <Text size="sm" fw={500} c={isCancelAllowed ? 'green.6' : 'red.6'}>
                      {isCancelAllowed ? '✓ Allowed' : '✗ Not Allowed'}
                      {isCancelAllowed && ` - Fee: ${cancellationFee}`}
                    </Text>
                  </Group>
                  <Group justify="space-between">
                    <Text size="sm" c="dimmed">
                      Changes:
                    </Text>
                    <Text size="sm" fw={500} c={isChangeAllowed ? 'green.6' : 'red.6'}>
                      {isChangeAllowed ? '✓ Allowed' : '✗ Not Allowed'}
                      {isChangeAllowed && ` - Fee: ${changeFee}`}
                    </Text>
                  </Group>
                </Box>
              );
            })}
          </Stack>
        </Card>
      )}

      {/* Complete Passenger Details Button */}
      <Group justify="center" mt="xl">
        <Button
          size="lg"
          radius="md"
          fw={600}
          px="xl"
          styles={{ root: { fontSize: '1.125rem' } }}
          onClick={() => {
            trackEvent('flight_fare_rules_accepted', {
              total_price: totalFare,
              currency,
              booking_type: isLCC ? 'LCC' : 'GDS',
            });
            navigate('/flights/passenger-info', {
              state: {
                revalidateResponse,
                selectedFlightData,
                searchSessionId: state?.searchSessionId,
              },
            });
          }}
        >
          Complete Passenger Details
        </Button>
      </Group>
    </Container>
  );
}

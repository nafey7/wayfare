import { useEffect, useState, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Card,
  Divider,
  Group,
  Loader,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import {
  selectPassengers,
  selectContact,
  selectFareRules,
  selectSessionId,
  selectFareSourceCode,
  selectIsLCC,
  selectRevalidationResponse,
  selectSelectedFlightData,
  selectSearchFormParams,
  selectMulticitySelectedLegs,
  selectMulticityGroupReference,
  selectFlightVoucherDiscountCents,
  selectFlightVoucherRedemptionId,
  selectFlightVoucherCheckoutRef,
  selectFlightVoucherAppliedCode,
  selectFlightVoucherReservationExpiresAt,
  setFareRules,
  setBookingResult,
  setRevalidationResponse,
  setSelectedFlightData,
  setMulticityGroupReference,
  setFlightVoucher,
} from '@/store/slices/flightBookingSlice';
import { useReleaseVoucherMutation } from '@/api/vouchersApi';
import { PromoCodeField } from '@/features/discount/components/PromoCodeField';
import { useGetFareRulesMutation } from '@/api/flightsApi';
import { useCreateRevolutOrderMutation } from '@/api/revolutPaymentsApi';
import {
  normalizeDateTime,
  extractTimeFromISO,
  formatCurrency,
  parseFareFromRevalidateResponse,
} from '../utils/flightUtils';
import { buildFlightSearchRedirectTarget } from '../utils/redirectToSearch';
import {
  buildFlightVoucherNavState,
  parseFlightBookingState,
} from '../utils/bookingNavigationState';
import {
  aggregateMulticityFare,
  generateMulticityGroupReference,
  getSortedMulticityLegSelections,
  hasMulticitySelection,
} from '../utils/multicityPricing';
import { trackEvent } from '@/utils/gtm';
import type {
  FlightLegCamel,
  FlightSegmentCamel,
  ValidatedFareItineraryCamel,
  FareTotalsCamel,
  FarePricingCamel,
} from '@/types/flightBackend';

interface SegmentDisplay {
  key: string;
  legLabel: string;
  depDate: string;
  depTime: string;
  arrTime: string;
  depCity: string;
  arrCity: string;
  depAirport: string;
  arrAirport: string;
  duration: string;
  airline: string;
  flightNumber: string;
}

/**
 * 1-based index within passenger type for UI labels (Adult 1, Adult 2, Child 1, …).
 * Matches PassengerInfoPage label behaviour.
 */
function getPassengerTypeIndex(
  passengers: Array<{ type: string }>,
  index: number
): number {
  const type = passengers[index]?.type;
  let count = 0;
  for (let j = 0; j <= index; j++) {
    if (passengers[j]?.type === type) count++;
  }
  return count;
}

/**
 * Format ISO date for display (e.g. "Jan 15, 2026")
 */
function formatDateForDisplay(isoString: string | null | undefined): string {
  if (!isoString) return '';
  const normalized = normalizeDateTime(isoString);
  if (!normalized) return '';
  try {
    return new Date(normalized).toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  } catch {
    return '';
  }
}

/**
 * Review Booking Details Page
 * Shows flight summary, passengers, contact, price, and cancellation policy (from fare-rules API).
 */
export function ReviewBookingPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useAppDispatch();
  const passengers = useAppSelector(selectPassengers);
  const contact = useAppSelector(selectContact);
  const reduxFareRules = useAppSelector(selectFareRules);
  const sessionId = useAppSelector(selectSessionId);
  const fareSourceCode = useAppSelector(selectFareSourceCode);
  const isLCC = useAppSelector(selectIsLCC);
  const reduxRevalidationResponse = useAppSelector(selectRevalidationResponse);
  const reduxSelectedFlightData = useAppSelector(selectSelectedFlightData);
  const searchFormParams = useAppSelector(selectSearchFormParams);
  const multicitySelectedLegs = useAppSelector(selectMulticitySelectedLegs);
  const multicityGroupReference = useAppSelector(selectMulticityGroupReference);
  const voucherDiscountCents = useAppSelector(selectFlightVoucherDiscountCents);
  const voucherRedemptionId = useAppSelector(selectFlightVoucherRedemptionId);
  const voucherCheckoutRef = useAppSelector(selectFlightVoucherCheckoutRef);
  const voucherAppliedCode = useAppSelector(selectFlightVoucherAppliedCode);
  const voucherReservationExpiresAt = useAppSelector(selectFlightVoucherReservationExpiresAt);

  const state = parseFlightBookingState(location.state) ?? null;
  const revalidateResponse = state?.revalidateResponse ?? reduxRevalidationResponse;
  const selectedFlightData = state?.selectedFlightData ?? reduxSelectedFlightData;

  const segmentCount = searchFormParams.segments?.length ?? 0;
  const isMulticity =
    searchFormParams.tripType === 'multi-city' && segmentCount >= 2;
  const hasMcSelection = isMulticity && hasMulticitySelection(multicitySelectedLegs);
  const multicityFirst = hasMcSelection
    ? getSortedMulticityLegSelections(multicitySelectedLegs)[0]
    : undefined;

  // Prefer search sessionId (from state, Redux, or localStorage); revalidate returns sequence_number, not the token
  const searchSessionId =
    state?.searchSessionId ??
    multicityFirst?.sessionId ??
    sessionId ??
    (typeof localStorage !== 'undefined' ? localStorage.getItem('sessionId') : null);

  const effectiveFareSourceCode =
    fareSourceCode ||
    multicityFirst?.fareSourceCode ||
    revalidateResponse?.fareSourceCode;

  // Store revalidation response and selected flight data in Redux (enables tab-switch persistence)
  useEffect(() => {
    if (revalidateResponse && !reduxRevalidationResponse) {
      dispatch(setRevalidationResponse(revalidateResponse));
    }
    if (state?.selectedFlightData) {
      dispatch(setSelectedFlightData(state.selectedFlightData));
    }
  }, [revalidateResponse, reduxRevalidationResponse, state?.selectedFlightData, dispatch]);

  const [getFareRules, { isLoading: loadingFareRules, error: fareRulesError }] =
    useGetFareRulesMutation();
  const [createRevolutOrder] = useCreateRevolutOrderMutation();
  const [releaseVoucherApi] = useReleaseVoucherMutation();

  const [fareRulesLoaded, setFareRulesLoaded] = useState(false);
  const [processingBooking, setProcessingBooking] = useState(false);
  // RTK Query handles loading state, but we keep local state for UI feedback
  const [bookingError, setBookingError] = useState<string | null>(null);

  useEffect(() => {
    if (isMulticity && !hasMcSelection) {
      navigate(buildFlightSearchRedirectTarget(searchFormParams), { replace: true });
      return;
    }
    if (!isMulticity && (!revalidateResponse || !selectedFlightData || !searchSessionId)) {
      navigate(buildFlightSearchRedirectTarget(searchFormParams), { replace: true });
      return;
    }
    if (isMulticity && hasMcSelection && !searchSessionId) {
      navigate(buildFlightSearchRedirectTarget(searchFormParams), { replace: true });
    }
  }, [
    isMulticity,
    hasMcSelection,
    revalidateResponse,
    selectedFlightData,
    searchSessionId,
    searchFormParams,
    navigate,
  ]);

  // GTM funnel: flight_booking_review_shown (once when review content is displayed)
  const reviewShownTrackedRef = useRef(false);
  useEffect(() => {
    if (reviewShownTrackedRef.current) return;
    if (isMulticity && hasMcSelection) {
      reviewShownTrackedRef.current = true;
      const { totalAmount, currency } = aggregateMulticityFare(multicitySelectedLegs);
      trackEvent('flight_booking_review_shown', {
        total_price: totalAmount,
        currency,
        passenger_count: passengers.length,
      });
      return;
    }
    if (!revalidateResponse || !selectedFlightData) return;
    reviewShownTrackedRef.current = true;
    const { amount: totalFare, currency } = parseFareFromRevalidateResponse(revalidateResponse);
    trackEvent('flight_booking_review_shown', {
      total_price: totalFare,
      currency,
      passenger_count: passengers.length,
    });
  }, [
    isMulticity,
    hasMcSelection,
    multicitySelectedLegs,
    revalidateResponse,
    selectedFlightData,
    passengers.length,
  ]);

  // Load fare rules on mount if not already loaded (e.g. user refreshed on this page)
  useEffect(() => {
    if (reduxFareRules) {
      setFareRulesLoaded(true);
      return;
    }
    if (!searchSessionId || !revalidateResponse?.fareSourceCode || fareRulesLoaded) return;

    const load = async () => {
      try {
        const result = await getFareRules({
          sessionId: searchSessionId!,
          fareSourceCode: effectiveFareSourceCode || revalidateResponse?.fareSourceCode || '',
        }).unwrap();
        dispatch(setFareRules(result));
        setFareRulesLoaded(true);
      } catch (err) {
        console.warn('Failed to load fare rules:', err);
        setFareRulesLoaded(true); // still allow review to show
      }
    };
    load();
  }, [
    searchSessionId,
    revalidateResponse?.fareSourceCode,
    effectiveFareSourceCode,
    getFareRules,
    dispatch,
    fareRulesLoaded,
    reduxFareRules,
  ]);

  const loadingBox = (
    <Group justify="center" align="center" style={{ width: '100%', minHeight: 200 }}>
      <Loader />
    </Group>
  );

  if (isMulticity && !hasMcSelection) {
    return loadingBox;
  }

  if (!isMulticity && (!revalidateResponse || !selectedFlightData)) {
    return loadingBox;
  }

  if (isMulticity && hasMcSelection && !multicityFirst) {
    return loadingBox;
  }

  const itinerary: ValidatedFareItineraryCamel | undefined =
    revalidateResponse?.validatedFareItineraries?.[0];
  const pricing: FarePricingCamel | undefined =
    itinerary?.updatedPricing ?? itinerary?.pricing;
  const fareTotals: FareTotalsCamel | undefined =
    pricing?.validatedFareTotals ?? pricing?.fareTotals;
  const flightLegs = itinerary?.flightLegs ?? [];
  const isRoundTrip = flightLegs.length > 1;

  const multicityAgg = hasMcSelection
    ? aggregateMulticityFare(multicitySelectedLegs)
    : null;
  const multicityCurrencyBlocked = Boolean(multicityAgg?.hasMixedCurrencies);
  const { amount: totalFare, currency } = hasMcSelection && multicityAgg
    ? { amount: multicityAgg.totalAmount, currency: multicityAgg.currency }
    : parseFareFromRevalidateResponse(revalidateResponse!);
  const platformFeePercentage = hasMcSelection && multicityAgg
    ? multicityAgg.platformFeePercentage
    : (fareTotals?.platformFeePercentage ?? 5);

  // Use API-provided originalTotalFare when available; otherwise derive from platformFeePercentage (not arbitrary 0.95)
  const originalTotalFare =
    hasMcSelection && multicityAgg
      ? platformFeePercentage > 0
        ? totalFare / (1 + platformFeePercentage / 100)
        : totalFare
      : fareTotals?.originalTotalFare?.amount != null
        ? Number(fareTotals.originalTotalFare.amount)
        : platformFeePercentage > 0
          ? totalFare / (1 + platformFeePercentage / 100)
          : totalFare;
  const platformFee = totalFare - originalTotalFare;

  const preDiscountCents = Math.max(0, Math.round(totalFare * 100));
  const voucherDc = voucherDiscountCents ?? 0;
  const payCents = Math.max(0, preDiscountCents - voucherDc);
  const payTotalFare = payCents / 100;
  const showUsdVoucher =
    !isMulticity &&
    !hasMcSelection &&
    currency.toUpperCase() === 'USD' &&
    !multicityCurrencyBlocked;

  // Use actual passengers from Redux (matches Passenger information section)
  const adultsCount = passengers.filter((p) => p.type === 'adult').length;
  const childrenCount = passengers.filter((p) => p.type === 'child').length;
  const infantsCount = passengers.filter((p) => p.type === 'infant').length;
  const totalPassengers = adultsCount + childrenCount + infantsCount;
  const adults = adultsCount;
  const children = childrenCount;
  const infants = infantsCount;

  const cancellationPolicyText = (() => {
    if (!reduxFareRules?.fareRules || !Array.isArray(reduxFareRules.fareRules)) return null;
    const outbound = reduxFareRules.fareRules
      .map((r) => r.ruleDescription)
      .filter((d): d is string => typeof d === 'string' && d.trim().length > 0)
      .join('\n\n');
    const inboundData = reduxFareRules.inboundFareData;
    const inboundRules = inboundData?.fareRules
      ?.map((r) => r.ruleDescription)
      .filter((d): d is string => typeof d === 'string' && d.trim().length > 0)
      .join('\n\n');
    if (inboundRules) {
      return outbound ? `${outbound}\n\n--- Return Flight ---\n\n${inboundRules}` : inboundRules;
    }
    return outbound || null;
  })();

  const showFareRulesLoading = !fareRulesLoaded && loadingFareRules;
  const showFareRulesError = fareRulesError && !reduxFareRules;

  const processLegSegments = (leg: FlightLegCamel | undefined, legLabel: string) => {
    const segments = leg?.flightSegments;
    if (!segments?.length) return null;
    return segments.map((seg: FlightSegmentCamel, segIndex: number) => {
      const depTime = extractTimeFromISO(seg.departureDatetime);
      const arrTime = extractTimeFromISO(seg.arrivalDatetime);
      const depDate = formatDateForDisplay(
        normalizeDateTime(seg.departureDatetime) ?? undefined
      );
      const durationMin = seg.flightDuration?.totalMinutes ?? 0;
      const hours = Math.floor(durationMin / 60);
      const mins = durationMin % 60;
      const depAirport = seg.departureAirport?.iataCode ?? '';
      const arrAirport = seg.arrivalAirport?.iataCode ?? '';
      const depCity = seg.departureAirport?.cityName ?? depAirport;
      const arrCity = seg.arrivalAirport?.cityName ?? arrAirport;
      const airlineCode =
        seg.marketingAirline?.iataCode ?? seg.operatingAirline?.iataCode ?? '';
      const airline =
        seg.marketingAirline?.airlineName ??
        seg.operatingAirline?.airlineName ??
        (airlineCode || 'Unknown');
      const flightNumber = seg.marketingFlightNumber?.formattedNumber ?? '';
      return {
        key: `${legLabel}-${segIndex}`,
        legLabel,
        depDate,
        depTime,
        arrTime,
        depCity,
        arrCity,
        depAirport,
        arrAirport,
        duration: `${hours}h ${mins}m`,
        airline,
        flightNumber,
      };
    });
  };

  let allSegments: SegmentDisplay[] = [];
  if (hasMcSelection) {
    const sortedMc = getSortedMulticityLegSelections(multicitySelectedLegs);
    sortedMc.forEach((mcLeg, legIdx) => {
      const it = mcLeg.revalidateResponse.validatedFareItineraries?.[0];
      const mcFlightLegs = it?.flightLegs ?? [];
      mcFlightLegs.forEach((fl, flIdx) => {
        const label = `Leg ${legIdx + 1}${mcFlightLegs.length > 1 ? ` (${flIdx + 1})` : ''}`;
        const rows = processLegSegments(fl, label);
        if (rows) allSegments.push(...rows);
      });
    });
  } else {
    const outboundSegments = flightLegs[0]
      ? processLegSegments(flightLegs[0], isRoundTrip ? 'OUTBOUND' : '')
      : [];
    const returnSegments =
      isRoundTrip && flightLegs[1] ? processLegSegments(flightLegs[1], 'RETURN') : [];
    allSegments = [
      ...(Array.isArray(outboundSegments) ? outboundSegments : []).map((s: SegmentDisplay) => ({
        ...s,
        legLabel: s.legLabel || 'OUTBOUND',
      })),
      ...(Array.isArray(returnSegments) ? returnSegments : []),
    ];
  }

  const itineraryForLCC = revalidateResponse?.validatedFareItineraries?.[0];
  const pricingForLCC = itineraryForLCC?.updatedPricing ?? itineraryForLCC?.pricing;
  const fareTypeForLCC = pricingForLCC?.fareType;
  const isLCCFromResponse = fareTypeForLCC === 'WebFare';

  /**
   * Handle Continue to Payment button click
   * For GDS: Create booking first, then navigate to payment
   * For LCC: Navigate directly to payment
   */
  const handleContinueToPayment = async () => {
    try {
      setProcessingBooking(true);
      setBookingError(null);

      // Validate required data
      if (!revalidateResponse || !searchSessionId || !effectiveFareSourceCode) {
        setBookingError('Missing flight information. Please start over.');
        setProcessingBooking(false);
        return;
      }

      if (passengers.length === 0) {
        setBookingError('Please complete passenger information.');
        setProcessingBooking(false);
        return;
      }

      // Validate passenger data is not empty
      const hasValidPassengers = passengers.every(
        (p) =>
          p.title?.trim() &&
          p.firstName?.trim() &&
          p.lastName?.trim() &&
          p.dateOfBirth?.trim() &&
          p.nationality?.trim()
      );
      if (!hasValidPassengers) {
        setBookingError(
          'Please complete all passenger information fields. If you just filled them out, please try again.'
        );
        setProcessingBooking(false);
        return;
      }

      if (!contact.email) {
        setBookingError('Please provide contact email.');
        setProcessingBooking(false);
        return;
      }

      if (payCents <= 0) {
        setBookingError('Total after discount must be greater than zero.');
        setProcessingBooking(false);
        return;
      }

      const flightVoucherNav = buildFlightVoucherNavState({
        voucherRedemptionId,
        voucherCheckoutRef,
        voucherAppliedCode,
        voucherDiscountCents,
        voucherReservationExpiresAt,
      });

      if (isMulticity && hasMcSelection) {
        const mcFare = aggregateMulticityFare(multicitySelectedLegs);
        if (mcFare.hasMixedCurrencies) {
          setBookingError(
            'Selected legs use different currencies. Adjust your selection so all legs share one currency.'
          );
          setProcessingBooking(false);
          return;
        }
        let groupRef = multicityGroupReference;
        if (!groupRef) {
          groupRef = generateMulticityGroupReference();
          dispatch(setMulticityGroupReference(groupRef));
        }
        const { totalAmount, currency: aggCur } = mcFare;
        const amountCents = Math.round(totalAmount * 100);
        const orderData = await createRevolutOrder({
          bookingAmount: amountCents,
          currency: aggCur.toLowerCase(),
          voyaBookingReference: groupRef,
          voucherRedemptionId: undefined,
          carrierType: (isLCCFromResponse || isLCC) ? 'LCC' : 'GDS',
        }).unwrap();
        const firstMc = getSortedMulticityLegSelections(multicitySelectedLegs)[0];
        if (!firstMc) {
          setBookingError('Missing multicity leg data.');
          setProcessingBooking(false);
          return;
        }
        navigate('/flights/payment', {
          state: {
            multicityMode: true,
            multicityGroupReference: groupRef,
            revalidateResponse: firstMc.revalidateResponse,
            selectedFlightData: firstMc.selectedFlightData,
            searchSessionId: firstMc.sessionId,
            revolutOrder: {
              orderId: orderData.orderId,
              publicOrderId: orderData.publicOrderId,
              amount: orderData.amount,
              currency: orderData.currency,
              platformFee: orderData.platformFee,
              supplierAmount: orderData.supplierAmount,
            },
            ...(flightVoucherNav ? { flightVoucher: flightVoucherNav } : {}),
          },
        });
        setProcessingBooking(false);
        return;
      }

      // For LCC: Create Revolut order, then navigate to payment
      if (isLCCFromResponse || isLCC) {
        const fareCurrency = currency.toLowerCase();
        const bookingRef =
          voucherRedemptionId && voucherCheckoutRef
            ? voucherCheckoutRef
            : `VOYA-TEMP-${crypto.randomUUID()}`;
        const orderData = await createRevolutOrder({
          bookingAmount: payCents,
          currency: fareCurrency,
          voyaBookingReference: bookingRef,
          voucherRedemptionId: voucherRedemptionId ?? undefined,
          carrierType: 'LCC',
        }).unwrap();
        navigate('/flights/payment', {
          state: {
            revalidateResponse,
            selectedFlightData,
            searchSessionId,
            revolutOrder: {
              orderId: orderData.orderId,
              publicOrderId: orderData.publicOrderId,
              amount: orderData.amount,
              currency: orderData.currency,
              platformFee: orderData.platformFee,
              supplierAmount: orderData.supplierAmount,
            },
            ...(flightVoucherNav ? { flightVoucher: flightVoucherNav } : {}),
          },
        });
        setProcessingBooking(false);
        return;
      }

      // For GDS: Create Revolut order first (backend generates voya_ref + PENDING event), then navigate
      // Booking API is deferred to Payment page "Pay Now"
      const fareCurrency = currency.toLowerCase();
      const orderData = await createRevolutOrder({
        bookingAmount: payCents,
        currency: fareCurrency,
        voyaBookingReference: voucherCheckoutRef ?? undefined,
        voucherRedemptionId: voucherRedemptionId ?? undefined,
        carrierType: 'GDS',
      }).unwrap();
      const voyaRef = orderData.voyaBookingReference;

      dispatch(
        setBookingResult({
          voyaBookingReference: voyaRef,
          status: 'pending',
          totalAmount: payCents,
          currency: fareCurrency,
        })
      );

      navigate('/flights/payment', {
        state: {
          revalidateResponse,
          selectedFlightData,
          searchSessionId,
          bookingResult: {
            voyaBookingReference: voyaRef,
            status: 'pending',
            totalAmount: payCents,
            currency: fareCurrency,
          },
          revolutOrder: {
            orderId: orderData.orderId,
            publicOrderId: orderData.publicOrderId,
            amount: orderData.amount,
            currency: orderData.currency,
            platformFee: orderData.platformFee,
            supplierAmount: orderData.supplierAmount,
          },
          ...(flightVoucherNav ? { flightVoucher: flightVoucherNav } : {}),
        },
      });
      setProcessingBooking(false);
    } catch (error: unknown) {
      console.error('Booking creation error:', error);
      if (voucherRedemptionId) {
        try {
          await releaseVoucherApi({ redemptionId: voucherRedemptionId }).unwrap();
        } catch {
          /* best-effort release */
        }
        dispatch(setFlightVoucher(null));
      }
      const err = error as { data?: { detail?: string; message?: string }; message?: string };
      const errorMessage =
        err?.data?.detail ??
        err?.data?.message ??
        err?.message ??
        'Failed to create booking. Please try again.';
      setBookingError(errorMessage);
      setProcessingBooking(false);
    }
  };

  const handleBack = async () => {
    if (voucherRedemptionId) {
      try {
        await releaseVoucherApi({ redemptionId: voucherRedemptionId }).unwrap();
      } catch {
        /* best-effort */
      }
      dispatch(setFlightVoucher(null));
    }
    navigate(-1);
  };

  return (
    <Box style={{ width: '100%', flex: 1, minHeight: 0 }} px="md" py="sm">
      <Title order={2} fw={700}>
        Review your booking
      </Title>
      <Text c="dimmed" mb="md">
        Please review your flight details, passengers, and contact information before proceeding.
      </Text>

      {showFareRulesLoading && (
        <Group align="center" gap="sm" mb="sm">
          <Loader size="sm" />
          <Text size="sm" c="dimmed">
            Loading fare rules and cancellation policy…
          </Text>
        </Group>
      )}
      {showFareRulesError && (
        <Alert color="yellow" mb="sm">
          Could not load cancellation policy. You can still proceed.
        </Alert>
      )}
      {bookingError && (
        <Alert color="red" mb="sm">
          {bookingError}
        </Alert>
      )}

      {/* Flight details */}
      <Card mb="md" p="lg" radius="md" withBorder>
        <Title order={6} fw={700} c="navy.7">
          Flight details
        </Title>
        <Divider my="md" />
        <Stack gap="sm">
          {allSegments.map((seg: SegmentDisplay) => (
            <Box
              key={seg.key}
              p="sm"
              style={{
                backgroundColor: 'var(--mantine-color-gray-0)',
                borderRadius: 8,
                borderLeft: `3px solid var(--mantine-color-${seg.legLabel === 'RETURN' ? 'grape' : 'navy'}-7)`,
              }}
            >
              {seg.legLabel && (
                <Text
                  fw={600}
                  size="sm"
                  c={seg.legLabel === 'RETURN' ? 'grape.6' : 'navy.7'}
                  mb={4}
                >
                  {seg.legLabel}
                </Text>
              )}
              <Text fw={600}>
                {seg.depDate} · {seg.depTime}{' '}
                {seg.depCity === seg.depAirport
                  ? seg.depAirport
                  : `${seg.depCity} (${seg.depAirport})`}{' '}
                → {seg.arrTime}{' '}
                {seg.arrCity === seg.arrAirport
                  ? seg.arrAirport
                  : `${seg.arrCity} (${seg.arrAirport})`}
              </Text>
              <Text size="sm" c="dimmed" mt={2}>
                <span style={{ fontWeight: 600, color: 'var(--mantine-color-navy-7)' }}>
                  {seg.airline}
                </span>
                {seg.flightNumber && (
                  <>
                    <span style={{ margin: '0 8px' }}>·</span>
                    {seg.flightNumber}
                  </>
                )}
                <span style={{ marginLeft: 8, fontWeight: 600 }}>{seg.duration}</span>
              </Text>
            </Box>
          ))}
        </Stack>
      </Card>

      {/* Passenger information */}
      <Card mb="md" p="lg" radius="md" withBorder>
        <Title order={6} fw={700} c="navy.7">
          Passenger information
        </Title>
        <Divider my="md" />
        <Stack gap="xs">
          {passengers.map((p, i) => (
            <Box
              key={i}
              p="sm"
              style={{
                backgroundColor: 'var(--mantine-color-gray-0)',
                borderRadius: 8,
              }}
            >
              <Text fw={600} size="sm">
                {p.type === 'adult' ? 'Adult' : p.type === 'child' ? 'Child' : 'Infant'}{' '}
                {getPassengerTypeIndex(passengers, i)}: {p.title} {p.firstName} {p.lastName}
              </Text>
              <Text size="sm" c="dimmed">
                DOB: {p.dateOfBirth} · Nationality: {p.nationality}
                {p.passportNumber && (
                  <>
                    <br />
                    Passport: {p.passportNumber} ({p.passportCountry}, Exp: {p.passportExpiry})
                  </>
                )}
              </Text>
            </Box>
          ))}
        </Stack>
      </Card>

      {/* Contact information */}
      <Card mb="md" p="lg" radius="md" withBorder>
        <Title order={6} fw={700} c="navy.7">
          Contact information
        </Title>
        <Divider my="md" />
        <Box p="sm" style={{ backgroundColor: 'var(--mantine-color-gray-0)', borderRadius: 8 }}>
          <Text size="sm">
            <strong>Email:</strong> {contact.email}
          </Text>
          <Text size="sm" mt={2}>
            <strong>Phone:</strong> +{contact.country_code} {contact.phone}
          </Text>
        </Box>
      </Card>

      {/* Price summary */}
      <Card
        mb="md"
        p="lg"
        radius="md"
        style={{
          border: '2px solid var(--mantine-color-green-3)',
          backgroundColor: 'var(--mantine-color-green-0)',
        }}
      >
        <Title order={6} fw={700} c="green.8">
          Price summary
        </Title>
        <Divider my="md" />
        <Group justify="space-between" mb={4}>
          <Text size="sm" c="dimmed">
            Tickets amount
          </Text>
          <Text size="sm" fw={600}>
            {formatCurrency(originalTotalFare, currency)}
          </Text>
        </Group>
        <Group justify="space-between" mb="sm">
          <Text size="sm" c="dimmed">
            Platform fee ({platformFeePercentage}%)
          </Text>
          <Text size="sm" fw={600}>
            {formatCurrency(platformFee, currency)}
          </Text>
        </Group>
        {voucherDc > 0 && (
          <Group justify="space-between" mb={4}>
            <Text size="sm" c="dimmed">
              Promo discount
              {voucherAppliedCode ? ` (${voucherAppliedCode})` : ''}
            </Text>
            <Text size="sm" fw={600} c="navy.7">
              −{formatCurrency(voucherDc / 100, currency)}
            </Text>
          </Group>
        )}
        <Group
          justify="space-between"
          align="center"
          pt="md"
          mt="md"
          style={{ borderTop: '2px solid var(--mantine-color-green-8)' }}
        >
          <Box>
            <Text size="sm" fw={600} c="green.8">
              {totalPassengers} passenger{totalPassengers !== 1 ? 's' : ''} total
              {adults ? ` (${adults} adult${adults !== 1 ? 's' : ''}` : ''}
              {children ? `, ${children} child${children !== 1 ? 'ren' : ''}` : ''}
              {infants ? `, ${infants} infant${infants !== 1 ? 's' : ''}` : ''}
              {adults || children || infants ? ')' : ''}
            </Text>
            <Text size="xs" c="dimmed">
              Amount to be charged
            </Text>
          </Box>
          <Title order={4} fw={700} c="green.8">
            {formatCurrency(payTotalFare, currency)}
          </Title>
        </Group>
      </Card>

      {isMulticity && multicityCurrencyBlocked && (
        <Alert color="red" mb="md">
          Selected legs use different currencies. One combined payment requires a single currency — go
          back and change a leg before continuing.
        </Alert>
      )}

      {/* Cancellation policy (from fare rules) */}
      {cancellationPolicyText && (
        <Card
          mb="md"
          p="lg"
          radius="md"
          style={{
            border: '2px solid var(--mantine-color-yellow-6)',
            backgroundColor: 'var(--mantine-color-yellow-0)',
          }}
        >
          <Title order={6} fw={700} c="yellow.8">
            Cancellation policy
          </Title>
          <Divider my="md" />
          <Box
            style={{
              fontSize: '0.875rem',
              lineHeight: 1.6,
              maxHeight: 280,
              overflowY: 'auto',
              whiteSpace: 'pre-wrap',
            }}
          >
            {cancellationPolicyText}
          </Box>
        </Card>
      )}

      {showUsdVoucher && (
        <Box mt="sm" mb="sm">
          <PromoCodeField
            emphasized
            bookingType="flight"
            amountCents={preDiscountCents}
            currencyCode={currency}
            applied={
              voucherRedemptionId &&
              voucherCheckoutRef &&
              voucherAppliedCode &&
              voucherDiscountCents != null
                ? {
                    redemptionId: voucherRedemptionId,
                    discountCents: voucherDiscountCents,
                    code: voucherAppliedCode,
                    checkoutVoyaReference: voucherCheckoutRef,
                    reservationExpiresAt: voucherReservationExpiresAt ?? undefined,
                  }
                : null
            }
            onApplied={(v) =>
              dispatch(
                setFlightVoucher({
                  redemptionId: v.redemptionId,
                  discountCents: v.discountCents,
                  checkoutVoyaReference: v.checkoutVoyaReference,
                  code: v.code,
                  reservationExpiresAt: v.reservationExpiresAt ?? null,
                })
              )
            }
            onCleared={() => dispatch(setFlightVoucher(null))}
          />
        </Box>
      )}

      {/* Actions */}
      <Group justify="space-between" gap="md" mt="xl" wrap="wrap">
        <Button variant="outline" color="gray" radius="md" onClick={() => void handleBack()}>
          Back
        </Button>
        <Button
          size="md"
          disabled={processingBooking || (isMulticity && multicityCurrencyBlocked)}
          onClick={handleContinueToPayment}
          radius="md"
          fw={600}
          px="xl"
          leftSection={processingBooking ? <Loader size="xs" color="white" /> : undefined}
        >
          {processingBooking ? 'Processing…' : 'Continue to payment'}
        </Button>
      </Group>
    </Box>
  );
}

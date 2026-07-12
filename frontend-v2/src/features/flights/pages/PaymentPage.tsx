import { useEffect, useState, useRef } from 'react';
import { useNavigate, useLocation, useParams, useSearchParams } from 'react-router-dom';
import {
  Alert,
  Button,
  Card,
  Container,
  Divider,
  Group,
  Loader,
  Text,
  Title,
} from '@mantine/core';
import { CreditCard, Lock } from 'lucide-react';
import { RevolutPaymentForm } from '@/components/revolut';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import {
  selectPassengers,
  selectContact,
  selectPostalCode,
  selectSavedPassengerIds,
  selectSessionId,
  selectFareSourceCode,
  selectIsLCC,
  selectBookingResult,
  selectRevalidationResponse,
  selectSearchFormParams,
  selectMulticitySelectedLegs,
  selectMulticityGroupReference,
  selectFlightVoucherRedemptionId,
  selectFlightVoucherCheckoutRef,
  selectFlightVoucherDiscountCents,
  selectFlightVoucherAppliedCode,
  setPaymentIntentId,
  setBookingResult,
  setMulticityGroupReference,
  setMulticityLegBookingResults,
  setFlightVoucher,
} from '@/store/slices/flightBookingSlice';
import { useReleaseVoucherMutation } from '@/api/vouchersApi';
import { selectIsAuthenticated, selectCurrentUser } from '@/store/slices/authSlice';
import { selectActiveSavedItineraryIdForBooking } from '@/store/slices/uiSlice';
import { useEmailLinkAuth } from '@/hooks/useEmailLinkAuth';
import { useCheckBookingExpiryMutation } from '@/api/paymentsApi';
import {
  useCreateRevolutOrderMutation,
  useLazyGetExistingRevolutOrderQuery,
  useLazyGetRevolutTransactionQuery,
  useGetRevolutTransactionsByBookingQuery,
} from '@/api/revolutPaymentsApi';
import {
  useBookFlightMutation,
  useIssueTicketMutation,
  useExchangeBookingTokenMutation,
  useGetTripDetailsMutation,
  useReportMulticityPartialBookingMutation,
} from '@/api/flightsApi';
import { useLazyGetMeQuery } from '@/api/usersApi';
import { extractErrorMessage, showErrorToast, showInfoToast, showSuccessToast } from '@/utils/toast';
import { trackEvent } from '@/utils/gtm';
import { buildBookingRequest } from '../utils/bookingRequest';
import { buildFlightSearchRedirectTarget } from '../utils/redirectToSearch';
import {
  parseFlightVoucherNavState,
  parsePaymentPageState,
  parsePaymentPageStateMinimal,
  type PaymentPageState,
} from '../utils/bookingNavigationState';
import {
  formatCurrencyFromCents,
  parseFareFromRevalidateResponse,
  DEFAULT_CURRENCY,
} from '../utils/flightUtils';
import { parseFareAmountFromTripDetails } from '../utils/tripDetailsFare';
import { generateClientVoyaReference } from '@/utils/voyaClientReference';
import { DEFAULT_FLIGHT_PLATFORM_FEE_PERCENTAGE } from '@/features/flights/constants/platformFee';
import {
  aggregateMulticityFare,
  generateMulticityGroupReference,
  getSortedMulticityLegSelections,
  hasMulticitySelection,
  isLegLccFromSelection,
} from '../utils/multicityPricing';
/** Revolut mode: prod only when VITE_ENV is production; otherwise sandbox (default). */
const REVOLUT_MODE: 'prod' | 'sandbox' =
  import.meta.env.VITE_ENV === 'production' ? 'prod' : 'sandbox';

/** RTK Query `unwrap()` rejects with `{ status, data? }` for HTTP errors. */
function isFetchErrorWithStatus(err: unknown, status: number): err is { status: number; data?: unknown } {
  return (
    typeof err === 'object' &&
    err !== null &&
    'status' in err &&
    (err as { status: unknown }).status === status
  );
}

function toastFromApiError(err: unknown, fallback: string) {
  showErrorToast(extractErrorMessage(err, fallback));
}

function buildBookingDetailsPath(bookingRef: string, authToken?: string | null): string {
  if (!authToken) return `/flights/bookings/${bookingRef}`;
  return `/flights/bookings/${bookingRef}?auth_token=${encodeURIComponent(authToken)}`;
}

/**
 * Payment Page – Revolut only.
 * Handles GDS and LCC payment flows (in-app) and payment from email link (/flights/payment/:bookingRef?auth_token=...).
 *
 * **LCC + flight promo (USD voucher):** This path is the sensitive one: checkout uses `voucherCheckoutRef`
 * on create-order, discounted cents vs revalidated fare, then `bookFlight` after pay. Revolut `submit()`
 * must include contact email (and phone when present) or the widget often fails with generic errors.
 */
export function PaymentPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { bookingRef: bookingRefFromUrl } = useParams<{ bookingRef?: string }>();
  const [searchParams] = useSearchParams();
  const authTokenFromUrl = searchParams.get('auth_token');
  const dispatch = useAppDispatch();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);

  const isEmailLinkMode = Boolean(bookingRefFromUrl);

  const state =
    parsePaymentPageState(location.state) ?? parsePaymentPageStateMinimal(location.state) ?? null;

  const revalidateResponseFromState = state?.revalidateResponse;
  const revalidateResponseFromRedux = useAppSelector(selectRevalidationResponse);
  const revalidateResponse = (revalidateResponseFromState || revalidateResponseFromRedux) as
    | PaymentPageState['revalidateResponse']
    | null;
  const reduxBookingResult = useAppSelector(selectBookingResult);
  const currentFlowBookingRef =
    bookingRefFromUrl ?? state?.bookingResult?.voyaBookingReference ?? reduxBookingResult?.voyaBookingReference;
  // Prefer Redux when it has completed booking (Pay Now done) for same voya ref
  const bookingResult =
    reduxBookingResult?.externalBookingReference &&
    reduxBookingResult?.voyaBookingReference === currentFlowBookingRef
      ? reduxBookingResult
      : (state?.bookingResult ?? reduxBookingResult);
  const effectiveBookingResult =
    isEmailLinkMode && bookingRefFromUrl
      ? { voyaBookingReference: bookingRefFromUrl, status: 'pending', totalAmount: 0, currency: DEFAULT_CURRENCY }
      : bookingResult;

  const itineraryForLCC = revalidateResponse?.validatedFareItineraries?.[0] as
    | { updatedPricing?: { fareType?: string }; pricing?: { fareType?: string } }
    | undefined;
  const fareTypeForLCC =
    itineraryForLCC?.updatedPricing?.fareType ?? itineraryForLCC?.pricing?.fareType;
  const isLCCDerived = fareTypeForLCC === 'WebFare';
  const reduxIsLCC = useAppSelector(selectIsLCC);
  const isLCC = isLCCDerived ?? reduxIsLCC;
  const reduxSessionId = useAppSelector(selectSessionId);
  const reduxFareSourceCode = useAppSelector(selectFareSourceCode);
  const sessionId =
    state?.searchSessionId ??
    reduxSessionId ??
    (typeof localStorage !== 'undefined' ? localStorage.getItem('sessionId') : null) ??
    revalidateResponse?.sessionId ??
    null;
  const fareSourceCode = reduxFareSourceCode ?? revalidateResponse?.fareSourceCode ?? null;
  const passengers = useAppSelector(selectPassengers);
  const savedPassengerIds = useAppSelector(selectSavedPassengerIds);
  const currentUser = useAppSelector(selectCurrentUser);
  const contact = useAppSelector(selectContact);
  const postalCode = useAppSelector(selectPostalCode);
  const searchFormParams = useAppSelector(selectSearchFormParams);
  const activeSavedItineraryId = useAppSelector(selectActiveSavedItineraryIdForBooking);
  const multicitySelectedLegs = useAppSelector(selectMulticitySelectedLegs);
  const multicityGroupRefRedux = useAppSelector(selectMulticityGroupReference);
  const voucherRedemptionId = useAppSelector(selectFlightVoucherRedemptionId);
  const voucherCheckoutRef = useAppSelector(selectFlightVoucherCheckoutRef);
  const voucherDiscountCents = useAppSelector(selectFlightVoucherDiscountCents);
  const voucherAppliedCode = useAppSelector(selectFlightVoucherAppliedCode);

  const segmentCount = searchFormParams.segments?.length ?? 0;
  const isMulticityTrip =
    searchFormParams.tripType === 'multi-city' && segmentCount >= 2;
  const hasMcSelection =
    isMulticityTrip && hasMulticitySelection(multicitySelectedLegs);
  const multicityGroupRef = state?.multicityGroupReference ?? multicityGroupRefRedux ?? null;
  const multicityMode =
    Boolean(state?.multicityMode) ||
    (Boolean(multicityGroupRef) && isMulticityTrip && hasMcSelection);

  const [publicOrderId, setPublicOrderId] = useState<string | null>(null);
  const [orderId, setOrderId] = useState<string | null>(null);
  const [amount, setAmount] = useState<number>(0);
  const [currency, setCurrency] = useState<string>(DEFAULT_CURRENCY);
  const [platformFee, setPlatformFee] = useState<number>(0);
  const [supplierAmount, setSupplierAmount] = useState<number>(0);
  const [loading, setLoading] = useState(false);
  /** GDS book-before-pay returned HTTP 409: non-retryable; Pay stays disabled. User is notified via error toast. */
  const [gdsBookingConflictMessage, setGdsBookingConflictMessage] = useState<string | null>(null);
  const mixedCurrencyToastFiredRef = useRef(false);

  const [emailLinkTripDetails, setEmailLinkTripDetails] = useState<Record<string, unknown> | null>(null);

  const [createRevolutOrder, { isLoading: isCreateOrderPending }] = useCreateRevolutOrderMutation();
  const [getExistingRevolutOrder, { isFetching: isExistingOrderFetching }] = useLazyGetExistingRevolutOrderQuery();
  const [getRevolutTransaction] = useLazyGetRevolutTransactionQuery();
  const [checkBookingExpiry] = useCheckBookingExpiryMutation();
  const [bookFlight] = useBookFlightMutation();
  const [issueTicket] = useIssueTicketMutation();
  const [exchangeBookingToken] = useExchangeBookingTokenMutation();
  const [getTripDetails] = useGetTripDetailsMutation();
  const [reportMulticityPartialBooking] = useReportMulticityPartialBookingMutation();
  const [getMe] = useLazyGetMeQuery();
  const [releaseVoucherApi] = useReleaseVoucherMutation();

  const releaseFlightVoucherBestEffort = async (reason?: string) => {
    if (!voucherRedemptionId) {
      return;
    }
    try {
      await releaseVoucherApi({
        redemptionId: voucherRedemptionId,
        reason: reason ? `payment_page:${reason}` : undefined,
      }).unwrap();
    } catch {
      /* best-effort; clear UI state below */
    }
    dispatch(setFlightVoucher(null));
  };

  // Same idea as hotel carrying revolut + voya ref in location.state: restore USD voucher if Redux lost it.
  useEffect(() => {
    if (isEmailLinkMode) return;
    if (voucherRedemptionId) return;
    const fromNav = parseFlightVoucherNavState(location.state);
    if (!fromNav) return;
    dispatch(
      setFlightVoucher({
        redemptionId: fromNav.redemptionId,
        discountCents: fromNav.discountCents,
        checkoutVoyaReference: fromNav.checkoutVoyaReference,
        code: fromNav.code,
        reservationExpiresAt: fromNav.reservationExpiresAt ?? null,
      })
    );
  }, [isEmailLinkMode, voucherRedemptionId, location.state, dispatch]);

  const { authDone: emailLinkAuthDone, wrongAccount: emailLinkWrongAccount } = useEmailLinkAuth({
    isEmailLinkMode,
    authTokenFromUrl,
    exchangeToken: exchangeBookingToken,
    getMe,
  });

  const revolutLookupRef =
    multicityMode && multicityGroupRef ? multicityGroupRef : currentFlowBookingRef || '';

  const { data: existingRevolutTransactions } = useGetRevolutTransactionsByBookingQuery(
    revolutLookupRef,
    { skip: !revolutLookupRef || (isEmailLinkMode && !isAuthenticated) }
  );

  useEffect(() => {
    if (state?.multicityGroupReference) {
      dispatch(setMulticityGroupReference(state.multicityGroupReference));
    }
  }, [state?.multicityGroupReference, dispatch]);

  // GTM funnel: flight_payment_initiated (when Revolut form is displayed)
  const paymentInitiatedTrackedRef = useRef(false);
  useEffect(() => {
    if (!publicOrderId || paymentInitiatedTrackedRef.current) return;
    paymentInitiatedTrackedRef.current = true;
    const props: Record<string, unknown> = {
      booking_type: multicityMode ? 'multicity' : isLCC ? 'LCC' : 'GDS',
    };
    if (multicityMode && hasMcSelection) {
      const agg = aggregateMulticityFare(multicitySelectedLegs);
      props.total_price = agg.totalAmount;
      props.currency = agg.currency.toUpperCase();
      if (agg.hasMixedCurrencies) props.multicity_mixed_currency = true;
    } else if (revalidateResponse) {
      const { amount: totalFare, currency: fareCurrency } = parseFareFromRevalidateResponse(revalidateResponse);
      props.total_price = totalFare;
      props.currency = fareCurrency.toUpperCase();
    } else if (emailLinkTripDetails) {
      const { amount: totalFare, currency: fareCurrency } =
        parseFareAmountFromTripDetails(emailLinkTripDetails);
      props.total_price = totalFare;
      props.currency = fareCurrency;
    }
    trackEvent('flight_payment_initiated', props);
  }, [
    publicOrderId,
    revalidateResponse,
    emailLinkTripDetails,
    isLCC,
    multicityMode,
    hasMcSelection,
    multicitySelectedLegs,
  ]);

  // Initialize from pre-created Revolut order (passed from ReviewBookingPage one-click flow)
  useEffect(() => {
    if (isEmailLinkMode) return;
    const order = state?.revolutOrder;
    if (!order || publicOrderId) return;
    setOrderId(order.orderId);
    setPublicOrderId(order.publicOrderId);
    setAmount(order.amount);
    setCurrency(order.currency);
    setPlatformFee(order.platformFee);
    setSupplierAmount(order.supplierAmount);
    dispatch(setPaymentIntentId(order.orderId));
  }, [isEmailLinkMode, state?.revolutOrder, dispatch, publicOrderId, isLCC]);

  useEffect(() => {
    if (!isEmailLinkMode || !bookingRefFromUrl || !isAuthenticated) return;
    getTripDetails({ voyaBookingReference: bookingRefFromUrl })
      .unwrap()
      .then((res) => setEmailLinkTripDetails((res as Record<string, unknown>) ?? null))
      .catch(() => setEmailLinkTripDetails(null));
  }, [isEmailLinkMode, bookingRefFromUrl, isAuthenticated, getTripDetails]);

  // Redirect only. Create-order is triggered by user action (Continue to payment), not by effect.
  useEffect(() => {
    if (isEmailLinkMode) {
      if (!emailLinkAuthDone) return;
      if (authTokenFromUrl && !isAuthenticated) return;
      if (!isAuthenticated) {
        navigate('/', { replace: true });
        return;
      }
      if (!emailLinkTripDetails) return;
      if (!bookingRefFromUrl) return;

      if (existingRevolutTransactions && existingRevolutTransactions.length > 0) {
        const succeeded = existingRevolutTransactions.find((t) => t.status === 'succeeded');
        if (succeeded) {
          navigate(buildBookingDetailsPath(bookingRefFromUrl, authTokenFromUrl), {
            replace: true,
          });
        }
      }
      return;
    }

    const hasValidGdsPaymentFromReview = !!parsePaymentPageStateMinimal(location.state);
    if (multicityMode && hasMcSelection) {
      if (!revalidateResponse || !sessionId) {
        navigate(buildFlightSearchRedirectTarget(searchFormParams), { replace: true });
        return;
      }
    } else if (
      !hasValidGdsPaymentFromReview &&
      (!revalidateResponse || !sessionId || !fareSourceCode)
    ) {
      navigate(buildFlightSearchRedirectTarget(searchFormParams), { replace: true });
      return;
    }

    const refAfterPay = currentFlowBookingRef;
    if (!multicityMode && refAfterPay && existingRevolutTransactions && existingRevolutTransactions.length > 0) {
      const succeeded = existingRevolutTransactions.find((t) => t.status === 'succeeded');
      if (succeeded) {
        navigate(buildBookingDetailsPath(refAfterPay), { replace: true });
      }
    }
  }, [
    isEmailLinkMode,
    emailLinkAuthDone,
    authTokenFromUrl,
    isAuthenticated,
    emailLinkTripDetails,
    bookingRefFromUrl,
    existingRevolutTransactions,
    revalidateResponse,
    sessionId,
    fareSourceCode,
    searchFormParams,
    currentFlowBookingRef,
    multicityMode,
    hasMcSelection,
    state?.bookingResult,
    bookingResult,
    navigate,
    location.state,
  ]);

  const handleInitializePayment = async () => {
    if (multicityMode && hasMcSelection) {
      try {
        const agg = aggregateMulticityFare(multicitySelectedLegs);
        if (agg.hasMixedCurrencies) {
          showErrorToast(
            'Selected legs use different currencies. Remove or change a leg so all fares share one currency, then try again.'
          );
          return;
        }
        if (agg.totalAmount === 0) throw new Error('Invalid flight price');
        const groupRef = multicityGroupRef ?? generateMulticityGroupReference();
        dispatch(setMulticityGroupReference(groupRef));
        const amountCents = Math.round(agg.totalAmount * 100);
        const fareCurrency = agg.currency.toLowerCase();
        type OrderData = {
          orderId: string;
          publicOrderId: string;
          amount: number;
          currency: string;
          platformFee: number;
          supplierAmount: number;
        };
        let orderData: OrderData;
        try {
          const existing = await getExistingRevolutOrder(groupRef).unwrap();
          orderData = {
            orderId: existing.orderId,
            publicOrderId: existing.publicOrderId,
            amount: existing.amount,
            currency: existing.currency,
            platformFee: existing.platformFee,
            supplierAmount: existing.supplierAmount,
          };
        } catch {
          const created = await createRevolutOrder({
            bookingAmount: amountCents,
            currency: fareCurrency,
            voyaBookingReference: groupRef,
            voucherRedemptionId: undefined,
            carrierType: isLCC ? 'LCC' : 'GDS',
          }).unwrap();
          orderData = {
            orderId: created.orderId,
            publicOrderId: created.publicOrderId,
            amount: created.amount,
            currency: created.currency,
            platformFee: created.platformFee,
            supplierAmount: created.supplierAmount,
          };
        }
        setOrderId(orderData.orderId);
        setPublicOrderId(orderData.publicOrderId);
        setAmount(orderData.amount);
        setCurrency(orderData.currency);
        setPlatformFee(orderData.platformFee);
        setSupplierAmount(orderData.supplierAmount);
        dispatch(setPaymentIntentId(orderData.orderId));
      } catch (err) {
        toastFromApiError(err, 'Failed to initialize payment');
      }
      return;
    }

    if (!revalidateResponse || !sessionId || !fareSourceCode) return;

    try {
      const { amount: totalFare, currency: fareCurrency } = parseFareFromRevalidateResponse(revalidateResponse);

      if (totalFare === 0) throw new Error('Invalid flight price');

      const baseCents = Math.round(totalFare * 100);
      const vDisc = voucherDiscountCents ?? 0;
      const amountCents =
        voucherRedemptionId && vDisc > 0 ? Math.max(0, baseCents - vDisc) : baseCents;
      const bookingRef = isLCC
        ? voucherRedemptionId && voucherCheckoutRef
          ? voucherCheckoutRef
          : generateClientVoyaReference()
        : (currentFlowBookingRef ?? generateClientVoyaReference());

      type OrderData = { orderId: string; publicOrderId: string; amount: number; currency: string; platformFee: number; supplierAmount: number };
      let orderData: OrderData;
      if (!isLCC && currentFlowBookingRef) {
        try {
          const existing = await getExistingRevolutOrder(currentFlowBookingRef).unwrap();
          orderData = {
            orderId: existing.orderId,
            publicOrderId: existing.publicOrderId,
            amount: existing.amount,
            currency: existing.currency,
            platformFee: existing.platformFee,
            supplierAmount: existing.supplierAmount,
          };
        } catch {
          const created = await createRevolutOrder({
            bookingAmount: amountCents,
            currency: fareCurrency.toLowerCase(),
            voyaBookingReference: bookingRef,
            voucherRedemptionId: voucherRedemptionId ?? undefined,
            carrierType: 'GDS',
          }).unwrap();
          orderData = {
            orderId: created.orderId,
            publicOrderId: created.publicOrderId,
            amount: created.amount,
            currency: created.currency,
            platformFee: created.platformFee,
            supplierAmount: created.supplierAmount,
          };
        }
      } else {
        const created = await createRevolutOrder({
          bookingAmount: amountCents,
          currency: fareCurrency.toLowerCase(),
          voyaBookingReference: bookingRef,
          voucherRedemptionId: voucherRedemptionId ?? undefined,
          carrierType: isLCC ? 'LCC' : 'GDS',
        }).unwrap();
        orderData = {
          orderId: created.orderId,
          publicOrderId: created.publicOrderId,
          amount: created.amount,
          currency: created.currency,
          platformFee: created.platformFee,
          supplierAmount: created.supplierAmount,
        };
      }

      setOrderId(orderData.orderId);
      setPublicOrderId(orderData.publicOrderId);
      setAmount(orderData.amount);
      setCurrency(orderData.currency);
      setPlatformFee(orderData.platformFee);
      setSupplierAmount(orderData.supplierAmount);
      dispatch(setPaymentIntentId(orderData.orderId));
    } catch (err) {
      toastFromApiError(err, 'Failed to initialize payment');
    }
  };

  const handleInitializePaymentFromEmailLink = async () => {
    if (!bookingRefFromUrl || !emailLinkTripDetails) return;
    const { amount: totalFare, currency: fareCurrency } = parseFareAmountFromTripDetails(emailLinkTripDetails);
    if (totalFare <= 0) {
      showErrorToast('Could not determine booking amount.');
      return;
    }

    try {
      setAmount(totalFare);
      setCurrency(fareCurrency);

      try {
        const existing = await getExistingRevolutOrder(bookingRefFromUrl).unwrap();
        setOrderId(existing.orderId);
        setPublicOrderId(existing.publicOrderId);
        setAmount(existing.amount);
        setCurrency(existing.currency);
        setPlatformFee(existing.platformFee);
        setSupplierAmount(existing.supplierAmount);
        dispatch(setPaymentIntentId(existing.orderId));
      } catch {
        const result = await createRevolutOrder({
          bookingAmount: Math.round(totalFare * 100),
          currency: fareCurrency.toLowerCase(),
          voyaBookingReference: bookingRefFromUrl,
          carrierType: isLCC ? 'LCC' : 'GDS',
        }).unwrap();
        setOrderId(result.orderId);
        setPublicOrderId(result.publicOrderId);
        setAmount(result.amount);
        setCurrency(result.currency);
        setPlatformFee(result.platformFee);
        setSupplierAmount(result.supplierAmount);
        dispatch(setPaymentIntentId(result.orderId));
      }
    } catch (err) {
      toastFromApiError(err, 'Failed to initialize payment');
    }
  };

  /**
   * GDS: run FlightLogic booking after card validation, before Revolut capture (same "Pay now" as card submit).
   * Skips if already booked; throws on failure so Revolut is not charged.
   */
  const handleGdsBookBeforePayment = async () => {
    const voyaRef = effectiveBookingResult?.voyaBookingReference ?? bookingResult?.voyaBookingReference;
    if (effectiveBookingResult?.externalBookingReference) {
      return;
    }
    if (!voyaRef || !sessionId || !fareSourceCode || !revalidateResponse) {
      throw new Error('Missing booking session. Please go back and try again.');
    }

    const expiryCheck = await checkBookingExpiry({ voyaBookingReference: voyaRef }).unwrap();
    if (!expiryCheck.isValid) {
      throw new Error(expiryCheck.message || 'Booking has expired. Please start a new search.');
    }

    try {
      const leadNationality = passengers[0]?.nationality;
      const bookingRequest = buildBookingRequest({
        sessionId,
        fareSourceCode,
        passengers,
        contact,
        paymentId: null,
        revalidateResponse,
        savedPassengerIds,
        postalCode: postalCode || undefined,
        billingCountry: leadNationality ?? 'NL',
        isLCC: false,
        savedItineraryId: activeSavedItineraryId,
        voyaBookingReference: voyaRef,
        voucherRedemptionId: voucherRedemptionId ?? undefined,
      });
      const result = await bookFlight(bookingRequest as Parameters<typeof bookFlight>[0]).unwrap();
      // Backend may return a different VOYA ref when it creates a new booking row instead of
      // updating the PENDING (TEMP-REF) event — always prefer the API value for issue_ticket lookups.
      const resolvedVoyaRef = result.voyaBookingReference ?? voyaRef;
      dispatch(
        setBookingResult({
          voyaBookingReference: resolvedVoyaRef,
          externalBookingReference: result.externalBookingReference,
          status: result.status ?? 'confirmed',
          totalAmount: result.totalAmount ?? amount,
          currency: result.currency ?? currency,
        })
      );
    } catch (err) {
      let msg = 'Booking failed. Please try again.';
      let conflict409 = false;

      if (isFetchErrorWithStatus(err, 409)) {
        conflict409 = true;
        const detail = (err.data as { detail?: string } | undefined)?.detail;
        msg =
          typeof detail === 'string'
            ? detail
            : 'This booking cannot be completed. Please start a new search.';
      } else if (err && typeof err === 'object' && 'data' in err) {
        msg = String((err.data as { detail?: string })?.detail ?? 'Booking failed');
      } else if (err instanceof Error) {
        msg = err.message;
      }

      const e = new Error(msg) as Error & { gdsBookingConflict409?: true };
      if (conflict409) e.gdsBookingConflict409 = true;
      throw e;
    }
  };

  const handlePaymentSuccess = async (revolutOrderId: string) => {
    try {
      setLoading(true);

      if (multicityMode && hasMcSelection) {
        const groupRef =
          multicityGroupRef ?? multicityGroupRefRedux ?? generateMulticityGroupReference();
        if (!multicityGroupRefRedux && !state?.multicityGroupReference) {
          dispatch(setMulticityGroupReference(groupRef));
        }
        const sorted = getSortedMulticityLegSelections(multicitySelectedLegs);
        const leadNationality = passengers[0]?.nationality;
        const succeeded: string[] = [];
        const voyaRefByLegIndex = new Map<number, string>();
        let lastError: string | null = null;

        for (const leg of sorted) {
          const legIsLcc = isLegLccFromSelection(leg);
          try {
            const bookingRequestBackend = buildBookingRequest({
              sessionId: leg.sessionId,
              fareSourceCode: leg.fareSourceCode,
              passengers,
              contact,
              paymentId: revolutOrderId,
              revalidateResponse: leg.revalidateResponse,
              savedPassengerIds,
              postalCode: postalCode ?? undefined,
              billingCountry: leadNationality ?? 'NL',
              isLCC: legIsLcc,
              savedItineraryId: activeSavedItineraryId,
              parentVoyaBookingReference: groupRef,
              multistayLegIndex: leg.legIndex,
            });
            const result = await bookFlight(
              bookingRequestBackend as Parameters<typeof bookFlight>[0]
            ).unwrap();
            const voyaRef = result.voyaBookingReference ?? '';
            if (!voyaRef) {
              lastError = 'Missing booking reference';
              break;
            }
            succeeded.push(voyaRef);
            voyaRefByLegIndex.set(leg.legIndex, voyaRef);

            if (!legIsLcc) {
              const ticketResult = await issueTicket({
                voyaBookingReference: voyaRef,
                paymentId: revolutOrderId,
              }).unwrap();
              if (!ticketResult.success) {
                const errMsg =
                  ticketResult.errors &&
                  Array.isArray(ticketResult.errors) &&
                  ticketResult.errors.length > 0
                    ? String(
                        (ticketResult.errors as { message?: string }[])[0]?.message ??
                          'Ticket issuance failed'
                      )
                    : 'Ticket issuance failed';
                lastError = errMsg;
                break;
              }
            }
          } catch (e) {
            lastError = e instanceof Error ? e.message : String(e);
            break;
          }
        }

        if (succeeded.length === 0) {
          showErrorToast(lastError ?? 'Booking failed');
          return;
        }

        if (lastError) {
          showErrorToast(
            `Some legs did not complete: ${lastError}. ${succeeded.length} leg(s) were booked. Contact support if you need help.`
          );
          void reportMulticityPartialBooking({
            multicityGroupReference: groupRef,
            revolutOrderId,
            legsBookedCount: succeeded.length,
            legsTotal: sorted.length,
            lastError,
            bookedVoyaReferences: succeeded,
          }).catch(() => {
            /* server log is best-effort */
          });
        } else {
          showSuccessToast('Payment confirmed.');
        }

        const primaryRef = succeeded[0]!;
        const legBookingResults = sorted.map((leg) => ({
          legIndex: leg.legIndex,
          voyaBookingReference: voyaRefByLegIndex.get(leg.legIndex) ?? '',
        }));
        dispatch(setMulticityLegBookingResults(legBookingResults));
        dispatch(
          setBookingResult({
            voyaBookingReference: primaryRef,
            externalBookingReference: undefined,
            status: lastError ? 'partial' : 'confirmed',
            totalAmount: amount,
            currency: currency.toUpperCase(),
          })
        );
        const multicityStatus = lastError ? 'partial' : 'confirmed';
        trackEvent('flight_payment_completed', {
          voya_booking_reference: primaryRef,
          total_price: amount / 100,
          currency: currency.toUpperCase(),
          booking_type: 'multicity',
          multicity_status: multicityStatus,
        });
        trackEvent('flight_booking_confirmed', {
          source: 'booker',
          voya_booking_reference: primaryRef,
          booking_type: 'multicity',
          total_price: amount / 100,
          currency: currency.toUpperCase(),
          passenger_count: passengers.length,
          journey_type: 'Circle',
          search_session_id: sessionId ?? undefined,
          multicity_status: multicityStatus,
        });
        if (lastError) {
          trackEvent('multicity_booking_partial_after_payment', {
            multicity_group_reference: groupRef,
            revolut_order_id: revolutOrderId,
            legs_booked_count: succeeded.length,
            legs_total: sorted.length,
            last_error: lastError,
            primary_voya_booking_reference: primaryRef,
            voya_booking_references_booked: succeeded,
            total_price: amount / 100,
            currency: currency.toUpperCase(),
          });
        }

        dispatch(setFlightVoucher(null));
        navigate(buildBookingDetailsPath(primaryRef, authTokenFromUrl), {
          replace: true,
          state: {
            multicityGroupReference: groupRef,
            multicityLegBookingResults: legBookingResults,
          },
        });
        return;
      }

      const gdsBookingRef = effectiveBookingResult?.voyaBookingReference ?? bookingResult?.voyaBookingReference;

      if (!isLCC && gdsBookingRef) {
        const expiryCheck = await checkBookingExpiry({ voyaBookingReference: gdsBookingRef }).unwrap();
        if (!expiryCheck.isValid) {
          showErrorToast(
            expiryCheck.message || 'Booking has expired. Please start a new search.'
          );
          return;
        }

        const maxAttempts = 10;
        const pollInterval = 2000;
        let attempts = 0;
        let transaction: { status: string } | null = null;

        while (attempts < maxAttempts) {
          attempts++;
          try {
            const data = await getRevolutTransaction(revolutOrderId).unwrap();
            transaction = data;
            if (data.status === 'succeeded') break;
          } catch (pollErr) {
            if (attempts === maxAttempts) throw pollErr;
          }
          await new Promise((r) => setTimeout(r, pollInterval));
        }

        if (!transaction || transaction.status !== 'succeeded') {
          showErrorToast('Payment verification timeout. Please contact support.');
          return;
        }

        showSuccessToast('Payment confirmed.');

        const ticketResult = await issueTicket({
          voyaBookingReference: gdsBookingRef,
          paymentId: revolutOrderId,
        }).unwrap();

        if (!ticketResult.success) {
          const errMsg =
            ticketResult.errors && Array.isArray(ticketResult.errors) && ticketResult.errors.length > 0
              ? String((ticketResult.errors as { message?: string }[])[0]?.message ?? 'Ticket issuance failed')
              : 'Ticket issuance failed';
          trackEvent('flight_payment_failed', {
            reason: errMsg,
            booking_type: 'GDS',
          });
          showErrorToast(errMsg);
          return;
        }

        trackEvent('flight_payment_completed', {
          voya_booking_reference: gdsBookingRef,
          total_price: (effectiveBookingResult?.totalAmount ?? bookingResult?.totalAmount ?? amount) / 100,
          currency: (effectiveBookingResult?.currency ?? bookingResult?.currency ?? currency).toUpperCase(),
          booking_type: 'GDS',
        });

        const baseResult = effectiveBookingResult ?? bookingResult;
        const gdsFlightLegs = revalidateResponse?.validatedFareItineraries?.[0]?.flightLegs ?? [];
        const gdsJourneyType = gdsFlightLegs.length > 1 ? 'Return' : 'OneWay';
        trackEvent('flight_booking_confirmed', {
          source: 'booker',
          voya_booking_reference: gdsBookingRef,
          booking_type: 'GDS',
          total_price: (baseResult?.totalAmount ?? amount) / 100,
          currency: (baseResult?.currency ?? currency).toUpperCase(),
          passenger_count: passengers.length,
          journey_type: gdsJourneyType,
          search_session_id: sessionId ?? undefined,
        });

        dispatch(setFlightVoucher(null));
        navigate(buildBookingDetailsPath(gdsBookingRef, authTokenFromUrl), {
          replace: true,
        });
        return;
      }

      if (isLCC) {
        const leadNationality = passengers[0]?.nationality;
        const bookingRequestBackend = buildBookingRequest({
          sessionId: sessionId!,
          fareSourceCode: fareSourceCode!,
          passengers,
          contact,
          paymentId: revolutOrderId,
          revalidateResponse: revalidateResponse ?? null,
          savedPassengerIds,
          postalCode: postalCode ?? undefined,
          billingCountry: leadNationality ?? 'NL',
          isLCC: true,
          savedItineraryId: activeSavedItineraryId,
          voyaBookingReference: voucherCheckoutRef ?? undefined,
          voucherRedemptionId: voucherRedemptionId ?? undefined,
        });
        const result = await bookFlight(bookingRequestBackend as Parameters<typeof bookFlight>[0]).unwrap();
        const voyaRef = result.voyaBookingReference ?? '';
        trackEvent('flight_payment_completed', {
          voya_booking_reference: voyaRef,
          total_price: (result.totalAmount ?? amount) / 100,
          currency: (result.currency ?? currency).toUpperCase(),
          booking_type: 'LCC',
        });
        const lccFlightLegs = revalidateResponse?.validatedFareItineraries?.[0]?.flightLegs ?? [];
        const lccJourneyType = lccFlightLegs.length > 1 ? 'Return' : 'OneWay';
        trackEvent('flight_booking_confirmed', {
          source: 'booker',
          voya_booking_reference: voyaRef,
          booking_type: 'LCC',
          total_price: (result.totalAmount ?? amount) / 100,
          currency: (result.currency ?? currency).toUpperCase(),
          passenger_count: passengers.length,
          journey_type: lccJourneyType,
          search_session_id: sessionId ?? undefined,
        });

        const externalRef = result.externalBookingReference;
        const status = result.status ?? 'confirmed';
        const totalAmount = result.totalAmount ?? amount;
        const currencyResult = result.currency ?? currency;

        dispatch(
          setBookingResult({
            voyaBookingReference: voyaRef,
            externalBookingReference: externalRef,
            status,
            totalAmount,
            currency: currencyResult,
          })
        );

        showSuccessToast('Payment confirmed.');

        dispatch(setFlightVoucher(null));
        navigate(buildBookingDetailsPath(voyaRef, authTokenFromUrl), {
          replace: true,
        });
      }
    } catch (err) {
      const errMsg = extractErrorMessage(err, 'Failed to process payment');
      trackEvent('flight_payment_failed', {
        reason: errMsg,
        booking_type: isLCC ? 'LCC' : 'GDS',
      });
      void releaseFlightVoucherBestEffort('post_pay_flow_error');
      showErrorToast(errMsg);
    } finally {
      setLoading(false);
    }
  };

  const handlePaymentError = (message: string, meta?: { gdsBookingConflict409?: boolean }) => {
    trackEvent('flight_payment_failed', {
      reason: message,
      booking_type: isLCC ? 'LCC' : 'GDS',
    });
    if (meta?.gdsBookingConflict409) {
      void releaseFlightVoucherBestEffort('gds_booking_conflict_409');
      setGdsBookingConflictMessage(message);
      showErrorToast(message);
      setLoading(false);
      return;
    }
    void releaseFlightVoucherBestEffort('revolut_or_validation_error');
    showErrorToast(message);
    setLoading(false);
  };

  const handlePaymentBack = () => {
    void releaseFlightVoucherBestEffort('user_navigate_back');
    navigate(-1);
  };

  const multicityFare =
    multicityMode && hasMcSelection ? aggregateMulticityFare(multicitySelectedLegs) : null;

  useEffect(() => {
    if (multicityFare?.hasMixedCurrencies && !mixedCurrencyToastFiredRef.current) {
      mixedCurrencyToastFiredRef.current = true;
      showErrorToast(
        'Selected legs use different currencies. One combined payment requires a single currency — go back and adjust your selection.'
      );
    }
  }, [multicityFare?.hasMixedCurrencies]);

  if (isEmailLinkMode && emailLinkAuthDone && emailLinkWrongAccount) {
    return (
      <Container size="md" py="xl">
        <Alert color="red" mb="sm">
          This link is for a different account. Sign out and open the link again, or use your own bookings.
        </Alert>
        <Button onClick={() => navigate('/')}>Back to home</Button>
      </Container>
    );
  }

  if (isEmailLinkMode && emailLinkAuthDone && authTokenFromUrl && !isAuthenticated) {
    return (
      <Container size="md" py="xl">
        <Alert color="red" mb="sm">
          This link has expired or is invalid. Please sign in and open the payment link from your email again.
        </Alert>
        <Button onClick={() => navigate('/')}>Back to home</Button>
      </Container>
    );
  }

  const isInitializing = isExistingOrderFetching || isCreateOrderPending;

  // Compute display amount for price summary (before or after create-order)
  const fareFromRevalidate = revalidateResponse
    ? parseFareFromRevalidateResponse(revalidateResponse)
    : null;
  const displayPlatformFeePct =
    multicityFare?.platformFeePercentage ??
    fareFromRevalidate?.platformFeePercentage ??
    DEFAULT_FLIGHT_PLATFORM_FEE_PERCENTAGE;
  const displayAmount =
    amount > 0
      ? amount
      : isEmailLinkMode && emailLinkTripDetails
        ? parseFareAmountFromTripDetails(emailLinkTripDetails).amount
        : multicityFare
          ? multicityFare.totalAmount
          : fareFromRevalidate?.amount ?? 0;
  const displayCurrency =
    amount > 0
      ? currency
      : isEmailLinkMode && emailLinkTripDetails
        ? parseFareAmountFromTripDetails(emailLinkTripDetails).currency
        : multicityFare
          ? multicityFare.currency
          : fareFromRevalidate?.currency ?? DEFAULT_CURRENCY;
  const displaySupplierAmount =
    supplierAmount > 0
      ? supplierAmount
      : Math.round((displayAmount * 100) / (1 + displayPlatformFeePct / 100));
  const displayPlatformFee =
    platformFee > 0 ? platformFee : Math.round(displayAmount * 100) - displaySupplierAmount;

  /**
   * `displayAmount` is fare in major units when `amount` is 0, but Revolut `amount` state is in cents
   * once an order is loaded.
   */
  const summarySubtotalCents =
    amount > 0 ? amount : Math.round((displayAmount ?? 0) * 100);
  const showPromoOnPayment =
    !isEmailLinkMode && (voucherDiscountCents ?? 0) > 0 && Boolean(voucherRedemptionId);
  const summaryAfterPromoCents = showPromoOnPayment
    ? Math.max(0, summarySubtotalCents - (voucherDiscountCents ?? 0))
    : summarySubtotalCents;

  // Email link: wait for trip details before showing the payment UI
  if (isEmailLinkMode && !emailLinkTripDetails) {
    return (
      <Container size="lg" py="xl">
        <Group justify="center" align="center" style={{ minHeight: 400 }}>
          <Loader />
        </Group>
      </Container>
    );
  }

  // Show full-page spinner only when create-order or get-existing is in progress
  if (isInitializing && !publicOrderId) {
    return (
      <Container size="lg" py="xl">
        <Group justify="center" align="center" style={{ minHeight: 400 }}>
          <Loader />
        </Group>
      </Container>
    );
  }

  // No order yet: show summary + Continue to payment button (or loading if email link trip details not ready)
  if (!publicOrderId || !orderId) {
    const handleContinue = isEmailLinkMode ? handleInitializePaymentFromEmailLink : handleInitializePayment;
    const hasDisplayAmount = isEmailLinkMode
      ? Boolean(emailLinkTripDetails)
      : multicityMode && hasMcSelection
        ? true
        : Boolean(revalidateResponse);

    return (
      <Container size="md" py="xl">
        <Group align="center" gap="sm" mb={4}>
          <CreditCard size={32} color="var(--mantine-color-navy-7)" />
          <Title order={2} fw={700}>
            Payment
          </Title>
        </Group>
        <Text c="dimmed" mb="md">
          {multicityMode
            ? 'One payment covers all legs; bookings are created per leg after payment succeeds.'
            : isLCC
              ? 'Complete your payment to confirm your booking.'
              : 'Complete your payment to finalize your booking.'}
        </Text>

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
            {multicityMode ? 'Multi-city payment summary' : 'Payment summary'}
          </Title>
          <Divider my="md" />
          <Group justify="space-between" mb={4}>
            <Text size="sm" c="dimmed">
              Flight / booking amount
            </Text>
            <Text size="sm" fw={600}>
              {formatCurrencyFromCents(displaySupplierAmount, displayCurrency)}
            </Text>
          </Group>
          <Group justify="space-between" mb="sm">
            <Text size="sm" c="dimmed">
              Platform service fee ({displayPlatformFeePct}%)
            </Text>
            <Text size="sm" fw={600}>
              {formatCurrencyFromCents(displayPlatformFee, displayCurrency)}
            </Text>
          </Group>
          {showPromoOnPayment && (
            <Group justify="space-between" mb={4}>
              <Text size="sm" c="dimmed">
                Promo discount
                {voucherAppliedCode ? ` (${voucherAppliedCode})` : ''}
              </Text>
              <Text size="sm" fw={600} c="navy.7">
                −{formatCurrencyFromCents(voucherDiscountCents ?? 0, displayCurrency)}
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
            <Text size="sm" fw={600} c="green.8">
              Total to pay
            </Text>
            <Title order={4} fw={700} c="green.8">
              {formatCurrencyFromCents(summaryAfterPromoCents, displayCurrency)}
            </Title>
          </Group>
        </Card>

        <Card mb="md" p="lg" radius="md" shadow="sm">
          <Title order={6} fw={700} c="navy.7">
            Card details
          </Title>
          <Divider my="md" />
          <Text size="sm" c="dimmed" mb="sm">
            Click below to load the secure payment form.
          </Text>
          <Button
            size="md"
            fullWidth
            onClick={handleContinue}
            disabled={
              isInitializing ||
              !hasDisplayAmount ||
              displayAmount <= 0 ||
              Boolean(multicityFare?.hasMixedCurrencies)
            }
            leftSection={isInitializing ? <Loader size="xs" color="white" /> : undefined}
          >
            {!hasDisplayAmount ? 'Loading…' : isInitializing ? 'Loading payment form…' : 'Continue to payment'}
          </Button>
        </Card>

        <Group justify="space-between" mt="md" wrap="wrap" gap="sm">
          <Button variant="outline" color="gray" radius="md" onClick={() => void handlePaymentBack()}>
            Back
          </Button>
        </Group>
      </Container>
    );
  }

  // Single-leg GDS: book-before-pay uses pending VOYA ref from create-order. Multicity has no
  // pending row until after Revolut succeeds — legs are booked in handlePaymentSuccess.
  const gdsBookBeforePay =
    !isLCC &&
    !isEmailLinkMode &&
    !effectiveBookingResult?.externalBookingReference &&
    !(multicityMode && hasMcSelection);

  const leadPassenger = passengers[0];
  // Revolut requires cardholder name to be at least two words
  const leadName = leadPassenger
    ? `${leadPassenger.firstName ?? ''} ${leadPassenger.lastName ?? ''}`.trim()
    : '';
  const userName = currentUser
    ? [currentUser.firstName, currentUser.lastName].filter(Boolean).join(' ').trim()
    : '';
  const hasTwoWords = (s: string) => s.split(/\s+/).filter(Boolean).length >= 2;
  const customerName =
    (leadName && hasTwoWords(leadName) ? leadName : null) ??
    (userName && hasTwoWords(userName) ? userName : null) ??
    'Card Holder';

  // Revolut card-field `submit()` metadata — required for reliable payment; issues were reported on LCC + promo.
  const paymentEmail =
    (contact.email && contact.email.trim()) || (currentUser?.email && currentUser.email.trim()) || '';
  const paymentPhone = (() => {
    const code = contact.country_code?.replace(/^\+/, '').trim();
    const num = contact.phone?.replace(/\D/g, '') ?? '';
    if (code && num) return `+${code}${num}`;
    return '';
  })();

  return (
    <Container size="md" py="xl">
      <Group align="center" gap="sm" mb={4}>
        <CreditCard size={32} color="var(--mantine-color-navy-7)" />
        <Title order={2} fw={700}>
          Payment
        </Title>
      </Group>
      <Text c="dimmed" mb="md">
        {multicityMode
          ? 'One payment covers all legs; bookings are created per leg after payment succeeds.'
          : isLCC
            ? 'Complete your payment to confirm your booking.'
            : 'Complete your payment to finalize your booking.'}
      </Text>

      {/* Price breakdown – same structure as flight-booker / Review page */}
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
          {multicityMode ? 'Multi-city payment summary' : 'Payment summary'}
        </Title>
        <Divider my="md" />
        <Group justify="space-between" mb={4}>
          <Text size="sm" c="dimmed">
            Flight / booking amount
          </Text>
          <Text size="sm" fw={600}>
            {formatCurrencyFromCents(supplierAmount, currency)}
          </Text>
        </Group>
        <Group justify="space-between" mb="sm">
          <Text size="sm" c="dimmed">
            Platform service fee ({displayPlatformFeePct}%)
          </Text>
          <Text size="sm" fw={600}>
            {formatCurrencyFromCents(platformFee, currency)}
          </Text>
        </Group>
        {showPromoOnPayment && (
          <Group justify="space-between" mb={4}>
            <Text size="sm" c="dimmed">
              Promo discount
              {voucherAppliedCode ? ` (${voucherAppliedCode})` : ''}
            </Text>
            <Text size="sm" fw={600} c="navy.7">
              −{formatCurrencyFromCents(voucherDiscountCents ?? 0, currency)}
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
          <Text size="sm" fw={600} c="green.8">
            Total to pay
          </Text>
          <Title order={4} fw={700} c="green.8">
            {formatCurrencyFromCents(amount, currency)}
          </Title>
        </Group>
      </Card>

      <Card mb="md" p="lg" radius="md" shadow="sm">
        <Title order={6} fw={700} c="navy.7">
          Card details
        </Title>
        <Divider my="md" />
        <RevolutPaymentForm
          orderToken={publicOrderId}
          orderId={orderId}
          mode={REVOLUT_MODE}
          customerName={customerName}
          customerEmail={paymentEmail}
          customerPhone={paymentPhone}
          amount={amount}
          currency={currency}
          onBeforeSubmit={gdsBookBeforePay ? handleGdsBookBeforePayment : undefined}
          onSubmitStart={() => showInfoToast('We are confirming your payment.')}
          onSuccess={handlePaymentSuccess}
          onError={handlePaymentError}
          disabled={loading || Boolean(gdsBookingConflictMessage)}
          submitLabel={
            multicityMode
              ? 'Pay for multi-city trip'
              : isLCC
                ? 'Pay and Confirm Booking'
                : 'Pay Now'
          }
        />
        <Group
          align="center"
          gap="xs"
          mt="sm"
          py="sm"
          px="sm"
          style={{ backgroundColor: 'var(--mantine-color-gray-0)', borderRadius: 8 }}
        >
          <Lock size={18} color="var(--mantine-color-dimmed)" />
          <Text size="xs" c="dimmed">
            Your payment is processed securely by Revolut. We do not store your card details.
          </Text>
        </Group>
      </Card>

      <Group justify="space-between" mt="md" wrap="wrap" gap="sm">
        <Button variant="outline" color="gray" radius="md" onClick={() => void handlePaymentBack()}>
          Back
        </Button>
      </Group>
    </Container>
  );
}

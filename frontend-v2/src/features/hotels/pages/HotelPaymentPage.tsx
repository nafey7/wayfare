/**
 * Hotel payment page — Revolut payment.
 * Route: /hotels/payment, /hotels/payment/:bookingRef
 * Step 6: Create Revolut order, render Revolut form, on success call book then navigate to confirmation.
 */
import { useEffect, useState, useRef } from 'react';
import type { HotelMultistayLegBookingResult } from '@/types/hotels';
import { useNavigate, useParams, useSearchParams, useLocation } from 'react-router-dom';
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
  selectSelectedHotel,
  selectSelectedRoom,
  selectHotelInternalSessionId,
  selectHotelSessionId,
  selectHotelProductId,
  selectHotelTokenId,
  selectHotelRateBasisId,
  selectHotelSearchFormParams,
  selectHotelGuests,
  selectHotelContactEmail,
  selectHotelContactPhone,
  selectHotelSpecialRequests,
  selectRateRulesResponse,
  setBookingResult,
  setPaymentIntentId,
  selectHotelVoucherRedemptionId,
  selectHotelVoucherDiscountCents,
  selectHotelVoucherCheckoutRef,
  selectHotelVoucherAppliedCode,
  setHotelVoucher,
  selectHotelTripType,
  selectMultistayLegs,
  selectMultistaySegments,
  setMultistayLegBookingResults,
} from '@/store/slices/hotelBookingSlice';
import { useReleaseVoucherMutation } from '@/api/vouchersApi';
import { selectIsAuthenticated, selectCurrentUser } from '@/store/slices/authSlice';
import { selectActiveSavedItineraryIdForBooking } from '@/store/slices/uiSlice';
import { useEmailLinkAuth } from '@/hooks/useEmailLinkAuth';
import {
  useCreateRevolutOrderMutation,
  useLazyGetRevolutTransactionQuery,
} from '@/api/revolutPaymentsApi';
import {
  useBookHotelMutation,
  useExchangeHotelBookingTokenMutation,
} from '@/api/hotelsApi';
import { useLazyGetMeQuery } from '@/api/usersApi';
import {
  extractErrorMessage,
  showErrorToast,
  showInfoToast,
  showSuccessToast,
} from '@/utils/toast';
import { devLog } from '@/utils/devLog';
import { trackEvent } from '@/utils/gtm';
import { DEFAULT_CURRENCY } from '../utils/hotelUtils';
import { buildHotelBookingDisplayPayload } from '../utils/hotelBookingDisplayPayload';
import { HotelPriceBreakdown } from '../components/HotelPriceBreakdown';
import { HotelCancellationPolicy } from '../components/HotelCancellationPolicy';

/** Revolut mode: prod only when VITE_ENV is production; otherwise sandbox (default). */
const REVOLUT_MODE: 'prod' | 'sandbox' =
  import.meta.env.VITE_ENV === 'production' ? 'prod' : 'sandbox';

const DEFAULT_PLATFORM_FEE_PERCENTAGE = 10.5;

function toastFromApiError(err: unknown, fallback: string) {
  showErrorToast(extractErrorMessage(err, fallback));
}

interface RevolutOrderFromState {
  orderId: string;
  publicOrderId: string;
  amount: number;
  currency: string;
  supplierAmount: number;
  voyaBookingReference?: string;
}

export function HotelPaymentPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { bookingRef: bookingRefFromUrl } = useParams<{ bookingRef?: string }>();
  const [searchParams] = useSearchParams();
  const authTokenFromUrl = searchParams.get('auth_token');
  const dispatch = useAppDispatch();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);

  const isEmailLinkMode = Boolean(bookingRefFromUrl);

  const selectedHotel = useAppSelector(selectSelectedHotel);
  const internalSessionId = useAppSelector(selectHotelInternalSessionId);
  const sessionId = useAppSelector(selectHotelSessionId);
  const productId = useAppSelector(selectHotelProductId);
  const tokenId = useAppSelector(selectHotelTokenId);
  const rateBasisId = useAppSelector(selectHotelRateBasisId);
  const searchFormParams = useAppSelector(selectHotelSearchFormParams);
  const guests = useAppSelector(selectHotelGuests);
  const contactEmail = useAppSelector(selectHotelContactEmail);
  const contactPhone = useAppSelector(selectHotelContactPhone);
  const specialRequests = useAppSelector(selectHotelSpecialRequests);
  const rateRulesResponse = useAppSelector(selectRateRulesResponse);
  const selectedRoom = useAppSelector(selectSelectedRoom);
  const currentUser = useAppSelector(selectCurrentUser);
  const activeSavedItineraryId = useAppSelector(selectActiveSavedItineraryIdForBooking);
  const voucherRedemptionId = useAppSelector(selectHotelVoucherRedemptionId);
  const voucherDiscountCents = useAppSelector(selectHotelVoucherDiscountCents);
  const voucherCheckoutRef = useAppSelector(selectHotelVoucherCheckoutRef);
  const voucherAppliedCode = useAppSelector(selectHotelVoucherAppliedCode);
  const tripType = useAppSelector(selectHotelTripType);
  const multistayLegs = useAppSelector(selectMultistayLegs);
  const multistaySegments = useAppSelector(selectMultistaySegments);
  const isMultistay = tripType === 'multi-stay';

  const [publicOrderId, setPublicOrderId] = useState<string | null>(null);
  const [orderId, setOrderId] = useState<string | null>(null);
  const [amountCents, setAmountCents] = useState<number>(0);
  const [currency, setCurrency] = useState<string>('USD');
  const [, setSupplierAmountCents] = useState<number>(0);
  const [voyaRefForRevolut, setVoyaRefForRevolut] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const [createRevolutOrder, { isLoading: isCreateOrderPending }] = useCreateRevolutOrderMutation();
  const [getRevolutTransaction] = useLazyGetRevolutTransactionQuery();
  const [bookHotel] = useBookHotelMutation();
  const [exchangeHotelBookingToken] = useExchangeHotelBookingTokenMutation();
  const [getMe] = useLazyGetMeQuery();
  const [releaseVoucherApi] = useReleaseVoucherMutation();

  const releaseHotelVoucherBestEffort = async () => {
    if (!voucherRedemptionId) return;
    try {
      await releaseVoucherApi({ redemptionId: voucherRedemptionId }).unwrap();
    } catch {
      /* ignore */
    }
    dispatch(setHotelVoucher(null));
  };

  const { authDone: emailLinkAuthDone, wrongAccount: emailLinkWrongAccount } = useEmailLinkAuth({
    isEmailLinkMode,
    authTokenFromUrl,
    exchangeToken: exchangeHotelBookingToken,
    getMe,
  });

  useEffect(() => {
    devLog('HotelPaymentPage Revolut mode:', REVOLUT_MODE);
  }, []);

  // GTM funnel: hotel_payment_initiated (when Revolut form is displayed).
  // Price and currency are paired: when amountCents > 0 we use Revolut order state; otherwise hotel/room/rate data.
  const paymentInitiatedTrackedRef = useRef(false);
  useEffect(() => {
    if (!publicOrderId || paymentInitiatedTrackedRef.current) return;
    if (!selectedHotel && !selectedRoom) return;
    paymentInitiatedTrackedRef.current = true;
    const totalMajor =
      selectedRoom?.totalPrice ??
      rateRulesResponse?.netPrice ??
      selectedHotel?.total ??
      selectedHotel?.originalTotal ??
      amountCents / 100;
    const currencyCode =
      selectedHotel?.startingPrice?.currency ??
      selectedRoom?.currency ??
      rateRulesResponse?.currency ??
      (selectedHotel as { currency?: string })?.currency ??
      DEFAULT_CURRENCY;
    const nights =
      searchFormParams?.checkin && searchFormParams?.checkout
        ? Math.ceil(
            (new Date(searchFormParams.checkout).getTime() -
              new Date(searchFormParams.checkin).getTime()) /
              (1000 * 60 * 60 * 24)
          )
        : 1;
    trackEvent('hotel_payment_initiated', {
      hotel_name: selectedHotel?.name ?? (selectedHotel as { hotelName?: string })?.hotelName ?? '',
      total_price: amountCents > 0 ? amountCents / 100 : totalMajor,
      currency: amountCents > 0 ? currency : currencyCode,
      nights,
      rooms: searchFormParams?.rooms?.length ?? 1,
    });
  }, [
    publicOrderId,
    selectedHotel,
    selectedRoom,
    rateRulesResponse,
    amountCents,
    currency,
    searchFormParams,
  ]);

  const state = location.state as { revolutOrder?: RevolutOrderFromState } | null;

  // Initialize from pre-created Revolut order (passed from HotelReviewBookingPage one-click flow)
  useEffect(() => {
    if (isEmailLinkMode) return;
    const order = state?.revolutOrder;
    if (!order || publicOrderId) return;
    setOrderId(order.orderId);
    setPublicOrderId(order.publicOrderId);
    setAmountCents(order.amount);
    setCurrency(order.currency);
    setSupplierAmountCents(order.supplierAmount);
    if (order.voyaBookingReference) setVoyaRefForRevolut(order.voyaBookingReference);
    dispatch(setPaymentIntentId(order.orderId));
  }, [isEmailLinkMode, state?.revolutOrder, dispatch, publicOrderId]);

  // Redirect if missing required state. Create-order is triggered by user action (Continue to payment), not by effect.
  useEffect(() => {
    if (isEmailLinkMode) {
      if (!emailLinkAuthDone) return;
      if (authTokenFromUrl && !isAuthenticated) return;
      if (!isAuthenticated) {
        navigate('/', { replace: true });
        return;
      }
      return;
    }

    if (isMultistay) {
      if (!multistayLegs.length || !guests.length || !contactEmail.trim() || !contactPhone.trim()) {
        navigate('/hotels/review-booking', { replace: true });
      }
      return;
    }
    if (
      !selectedHotel ||
      !internalSessionId ||
      !productId ||
      !tokenId ||
      !rateBasisId ||
      !guests.length ||
      !contactEmail.trim() ||
      !contactPhone.trim()
    ) {
      navigate('/hotels/review-booking', { replace: true });
      return;
    }
  }, [
    isEmailLinkMode,
    emailLinkAuthDone,
    authTokenFromUrl,
    isAuthenticated,
    isMultistay,
    multistayLegs.length,
    selectedHotel,
    internalSessionId,
    productId,
    tokenId,
    rateBasisId,
    guests.length,
    contactEmail,
    contactPhone,
    navigate,
  ]);

  const handleInitializePayment = async () => {
    if (!selectedHotel) return;

    const totalMajor =
      selectedRoom?.totalPrice ??
      rateRulesResponse?.netPrice ??
      selectedHotel.total ??
      selectedHotel.originalTotal ??
      0;
    const currencyCode =
      selectedHotel.startingPrice?.currency ??
      (selectedHotel as { currency?: string }).currency ??
      'USD';

    if (totalMajor <= 0) {
      showErrorToast('Invalid hotel price.');
      return;
    }

    try {
      const baseCents = Math.round(totalMajor * 100);
      const vDisc = voucherDiscountCents ?? 0;
      const amountCentsValue =
        voucherRedemptionId && vDisc > 0 ? Math.max(0, baseCents - vDisc) : baseCents;

      const created = await createRevolutOrder({
        bookingAmount: amountCentsValue,
        currency: currencyCode.toLowerCase(),
        voyaBookingReference: voucherCheckoutRef ?? undefined,
        orderType: 'hotel',
        voucherRedemptionId: voucherRedemptionId ?? undefined,
      }).unwrap();

      setVoyaRefForRevolut(created.voyaBookingReference);
      setOrderId(created.orderId);
      setPublicOrderId(created.publicOrderId);
      setAmountCents(created.amount);
      setCurrency(created.currency);
      setSupplierAmountCents(created.supplierAmount);
      dispatch(setPaymentIntentId(created.orderId));
    } catch (err) {
      toastFromApiError(err, 'Failed to initialize payment');
    }
  };

  const handlePaymentSuccess = async (revolutOrderId: string) => {
    const singleStayDataMissing =
      !isMultistay && (!internalSessionId || !productId || !tokenId || !rateBasisId);
    if (singleStayDataMissing || !contactEmail || !contactPhone) {
      showErrorToast('Booking data missing. Please go back and try again.');
      return;
    }

    try {
      setLoading(true);

      // Poll until Revolut transaction is succeeded (same as flights) so backend validation sees COMPLETED
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
          devLog('Payment poll attempt failed:', pollErr);
          if (attempts === maxAttempts) {
            throw pollErr;
          }
        }
        await new Promise((r) => setTimeout(r, pollInterval));
      }
      if (!transaction || transaction.status !== 'succeeded') {
        showErrorToast('Payment verification timeout. Please check your payment or contact support.');
        setLoading(false);
        return;
      }

      // Use voyaRefForRevolut for clientRef; backend overwrites with authoritative ref from Revolut transaction
      const clientRef = voyaRefForRevolut ?? `VOYA-${Date.now()}`;

      // ── Multi-stay: book each leg sequentially with a shared parent reference ──
      if (isMultistay) {
        const parentRef = clientRef;
        const legResults: HotelMultistayLegBookingResult[] = [];
        try {
          for (let i = 0; i < multistayLegs.length; i++) {
            const leg = multistayLegs[i]!;
            if (!leg.internalSessionId || !leg.productId || !leg.tokenId || !leg.rateBasisId) continue;
            const legDisplay = leg.selectedHotel ? buildHotelBookingDisplayPayload(leg.selectedHotel) : {};
            const legResult = await bookHotel({
              sessionId: leg.internalSessionId,
              tokenId: leg.tokenId,
              productId: leg.productId,
              rateBasisId: leg.rateBasisId,
              clientRef: parentRef,
              customerEmail: contactEmail,
              customerPhone: contactPhone,
              bookingNote: specialRequests ?? '',
              guests, // v1: all legs share the same occupancy
              roomCount: multistaySegments[i]?.rooms?.length ?? 1,
              paymentIntentId: revolutOrderId,
              ...legDisplay,
              savedItineraryId: activeSavedItineraryId ?? undefined,
              parentVoyaBookingReference: parentRef,
              multistayLegIndex: i,
            }).unwrap();
            legResults.push({
              legIndex: i,
              voyaBookingReference: legResult.voyaBookingReference ?? parentRef,
              externalBookingReference: legResult.supplierConfirmationNum ?? null,
              hotelName: leg.selectedHotel?.name ?? null,
              hotelCity: leg.selectedHotel?.city ?? null,
            });
          }
        } catch (err) {
          // Persist whichever legs succeeded so the confirmation page can show partial results.
          if (legResults.length > 0) {
            dispatch(setMultistayLegBookingResults(legResults));
            navigate('/hotels/confirmation', { replace: true });
            showErrorToast(
              `Legs ${legResults.map((r) => r.legIndex + 1).join(', ')} confirmed; leg ${legResults.length + 1} failed. Contact support with reference ${parentRef}.`
            );
          } else {
            toastFromApiError(err, 'Multi-stay booking failed. Please try again.');
          }
          return;
        }
        dispatch(setMultistayLegBookingResults(legResults));
        dispatch(setHotelVoucher(null));
        trackEvent('hotel_payment_completed', {
          voya_booking_reference: parentRef,
          stay_count: multistayLegs.length,
          total_price: amountCents / 100,
          currency: currency.toUpperCase(),
        });
        showSuccessToast('Payment confirmed. Your multi-stay booking is confirmed.');
        navigate('/hotels/confirmation', { replace: true });
        return;
      }

      if (!internalSessionId || !productId || !tokenId || !rateBasisId) {
        showErrorToast('Booking data missing. Please go back and try again.');
        return;
      }
      devLog('hotel booking (sending bookHotel request)', {
        rateBasisId,
        sessionId,
        productId,
      });
      const hotelDisplay = buildHotelBookingDisplayPayload(selectedHotel);
      const result = await bookHotel({
        sessionId: internalSessionId,
        tokenId,
        productId,
        rateBasisId,
        clientRef,
        customerEmail: contactEmail,
        customerPhone: contactPhone,
        bookingNote: specialRequests ?? '',
        guests,
        roomCount: searchFormParams?.rooms?.length ?? 1,
        paymentIntentId: revolutOrderId,
        ...hotelDisplay,
        savedItineraryId: activeSavedItineraryId ?? undefined,
        voucherRedemptionId: voucherRedemptionId ?? undefined,
      }).unwrap();

      // Prefer API response (authoritative); backend always returns voya_booking_reference on success
      const voyaRef =
        result.voyaBookingReference ?? voyaRefForRevolut ?? clientRef;
      const nights =
        searchFormParams?.checkin && searchFormParams?.checkout
          ? Math.ceil(
              (new Date(searchFormParams.checkout).getTime() - new Date(searchFormParams.checkin).getTime()) /
                (1000 * 60 * 60 * 24)
            )
          : 1;
      trackEvent('hotel_payment_completed', {
        voya_booking_reference: voyaRef,
        hotel_name: result.hotel?.name ?? selectedHotel?.name ?? '',
        total_price: (result.totalAmount ?? amountCents) / 100,
        currency: (result.currency ?? currency).toUpperCase(),
        nights,
        rooms: searchFormParams?.rooms?.length ?? 1,
      });
      trackEvent('hotel_booking_confirmed', {
        source: 'booker',
        voya_booking_reference: voyaRef,
        supplier_confirmation: result.supplierConfirmationNum ?? '',
        hotel_name: result.hotel?.name ?? selectedHotel?.name ?? '',
        total_price: (result.totalAmount ?? amountCents) / 100,
        currency: (result.currency ?? currency).toUpperCase(),
        nights,
        rooms: searchFormParams?.rooms?.length ?? 1,
        search_session_id: sessionId ?? internalSessionId ?? undefined,
      });

      // Merge API result with Redux state so confirmation page has full display data
      // (backend may only return voyaBookingReference, status, supplierConfirmationNum)
      const totalAmountCents =
        result.totalAmount != null && result.totalAmount > 0
          ? result.totalAmount
          : amountCents;
      dispatch(
        setBookingResult({
          voyaBookingReference: result.voyaBookingReference ?? voyaRef,
          status: result.status,
          supplierConfirmationNum: result.supplierConfirmationNum,
          hotel: result.hotel ?? selectedHotel ?? undefined,
          roomName: result.roomName ?? selectedRoom?.roomType ?? selectedRoom?.roomName ?? '',
          checkin: result.checkin ?? searchFormParams?.checkin ?? undefined,
          checkout: result.checkout ?? searchFormParams?.checkout ?? undefined,
          totalAmount: totalAmountCents,
          currency: result.currency ?? currency,
          guests: result.guests ?? guests ?? [],
        })
      );
      dispatch(setPaymentIntentId(revolutOrderId));

      showSuccessToast('Payment confirmed. Your booking is confirmed.');

      dispatch(setHotelVoucher(null));
      navigate('/hotels/confirmation', { replace: true });
    } catch (err) {
      const errMsg = extractErrorMessage(err, 'Booking failed. Your payment may be refunded.');
      trackEvent('hotel_payment_failed', { reason: errMsg });
      void releaseHotelVoucherBestEffort();
      showErrorToast(errMsg);
    } finally {
      setLoading(false);
    }
  };

  const handlePaymentError = (message: string) => {
    trackEvent('hotel_payment_failed', { reason: message });
    void releaseHotelVoucherBestEffort();
    showErrorToast(message);
    setLoading(false);
  };

  const handleHotelPaymentBack = () => {
    void releaseHotelVoucherBestEffort();
    navigate('/hotels/review-booking');
  };

  // Email link: wrong account
  if (isEmailLinkMode && emailLinkAuthDone && emailLinkWrongAccount) {
    return (
      <Container size="md" py="xl">
        <Alert color="red" mb="sm">
          This link is for a different account. Sign out and open the link again, or use your own
          bookings.
        </Alert>
        <Button onClick={() => navigate('/')}>Back to home</Button>
      </Container>
    );
  }

  // Email link: auth failed or no session restore
  if (isEmailLinkMode && emailLinkAuthDone && authTokenFromUrl && !isAuthenticated) {
    return (
      <Container size="md" py="xl">
        <Alert color="red" mb="sm">
          This link has expired or is invalid. Please sign in and open the payment link from your
          email again.
        </Alert>
        <Button onClick={() => navigate('/')}>Back to home</Button>
      </Container>
    );
  }

  // Email link: authenticated but hotel payment from email not supported (no restore by ref)
  if (isEmailLinkMode && emailLinkAuthDone && isAuthenticated && !loading && !publicOrderId) {
    return (
      <Container size="md" py="xl">
        <Alert color="blue" mb="sm">
          To complete your hotel payment, please use the same device or browser where you started
          the booking, or go to Hotels and start a new search.
        </Alert>
        <Button onClick={() => navigate('/hotels/search')}>
          Search hotels
        </Button>
      </Container>
    );
  }

  // Compute display values for price breakdown (before or after create-order)
  const displayTotalMajor =
    amountCents > 0
      ? amountCents / 100
      : (selectedRoom?.totalPrice ??
         rateRulesResponse?.netPrice ??
         selectedHotel?.total ??
         selectedHotel?.originalTotal ??
         0);
  const displayCurrency =
    amountCents > 0
      ? currency
      : (selectedHotel?.startingPrice?.currency ??
         (selectedHotel as { currency?: string })?.currency ??
         'USD');
  const displayPlatformFeePercentage =
    selectedHotel?.platformFeePercentage ?? rateRulesResponse?.platformFeePercentage ?? DEFAULT_PLATFORM_FEE_PERCENTAGE;
  // Hotel amount: use backend-derived values (matches HotelReviewBookingPage); fallback to total * (1 - fee%) for reverse markup
  const displayHotelAmount =
    rateRulesResponse?.originalNetPrice ??
    selectedRoom?.originalTotalPrice ??
    selectedHotel?.originalTotal ??
    (displayTotalMajor > 0 ? displayTotalMajor * (1 - displayPlatformFeePercentage / 100) : 0);

  /** Pre-promo total for the breakdown; after create-order, Revolut amount is post-discount. */
  const priceBreakdownTotalMajor =
    amountCents > 0 && (voucherDiscountCents ?? 0) > 0 && voucherRedemptionId
      ? amountCents / 100 + (voucherDiscountCents ?? 0) / 100
      : displayTotalMajor;

  // Show full-page spinner only when create-order is in progress and we have no order yet
  if (isCreateOrderPending && !publicOrderId) {
    return (
      <Container size="lg" py="xl">
        <Group justify="center" align="center" style={{ minHeight: 400 }}>
          <Loader />
        </Group>
      </Container>
    );
  }

  // No order yet: show summary + Continue to payment button (user must click to create order)
  if (!publicOrderId || !orderId) {
    const cancellationPolicy =
      rateRulesResponse?.cancellationPolicy ?? selectedRoom?.cancellationPolicy ?? null;

    return (
      <Container size="md" py="xl">
        <Group align="center" gap="sm" mb={4}>
          <CreditCard size={32} color="var(--mantine-color-navy-7)" />
          <Title order={2} fw={700}>
            Payment
          </Title>
        </Group>
        <Text c="dimmed" mb="md">
          Complete your payment to confirm your hotel booking.
        </Text>

        <HotelPriceBreakdown
          hotelAmount={displayHotelAmount}
          platformFeePercentage={displayPlatformFeePercentage}
          totalAmount={priceBreakdownTotalMajor}
          currency={displayCurrency}
          voucherDiscountCents={
            (voucherDiscountCents ?? 0) > 0 && voucherRedemptionId ? voucherDiscountCents : null
          }
          voucherCode={voucherAppliedCode}
        />

        <HotelCancellationPolicy cancellationPolicy={cancellationPolicy} />

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
            onClick={handleInitializePayment}
            disabled={isCreateOrderPending || displayTotalMajor <= 0}
            leftSection={isCreateOrderPending ? <Loader size="xs" color="white" /> : undefined}
          >
            {isCreateOrderPending ? 'Loading payment form…' : 'Continue to payment'}
          </Button>
        </Card>

        <Group justify="space-between" mt="md" wrap="wrap" gap="sm">
          <Button variant="outline" color="gray" radius="md" onClick={() => void handleHotelPaymentBack()}>
            Back
          </Button>
        </Group>
      </Container>
    );
  }

  const leadGuest = guests[0];
  const leadName = leadGuest
    ? `${leadGuest.firstName ?? ''} ${leadGuest.lastName ?? ''}`.trim()
    : '';
  const userName = currentUser
    ? [currentUser.firstName, currentUser.lastName].filter(Boolean).join(' ').trim()
    : '';
  const hasTwoWords = (s: string) => s.split(/\s+/).filter(Boolean).length >= 2;
  const customerName =
    (leadName && hasTwoWords(leadName) ? leadName : null) ??
    (userName && hasTwoWords(userName) ? userName : null) ??
    'Card Holder';

  const cancellationPolicy =
    rateRulesResponse?.cancellationPolicy ?? selectedRoom?.cancellationPolicy ?? null;
  const platformFeePercentage =
    selectedHotel?.platformFeePercentage ?? rateRulesResponse?.platformFeePercentage ?? DEFAULT_PLATFORM_FEE_PERCENTAGE;

  return (
    <Container size="md" py="xl">
      <Group align="center" gap="sm" mb={4}>
        <CreditCard size={32} color="var(--mantine-color-navy-7)" />
        <Title order={2} fw={700}>
          Payment
        </Title>
      </Group>
      <Text c="dimmed" mb="md">
        Complete your payment to confirm your hotel booking.
      </Text>

      <HotelPriceBreakdown
        hotelAmount={displayHotelAmount}
        platformFeePercentage={platformFeePercentage}
        totalAmount={priceBreakdownTotalMajor}
        currency={currency}
        voucherDiscountCents={
          (voucherDiscountCents ?? 0) > 0 && voucherRedemptionId ? voucherDiscountCents : null
        }
        voucherCode={voucherAppliedCode}
      />

      <HotelCancellationPolicy cancellationPolicy={cancellationPolicy} />

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
          customerEmail={
            (contactEmail && contactEmail.trim()) ||
            (currentUser?.email && currentUser.email.trim()) ||
            ''
          }
          customerPhone={(contactPhone && contactPhone.trim()) || ''}
          amount={amountCents}
          currency={currency}
          onSubmitStart={() => showInfoToast('We are confirming your payment.')}
          onSuccess={handlePaymentSuccess}
          onError={handlePaymentError}
          disabled={loading}
          submitLabel="Pay and Confirm Booking"
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
        <Button variant="outline" color="gray" radius="md" onClick={() => void handleHotelPaymentBack()}>
          Back
        </Button>
      </Group>
    </Container>
  );
}

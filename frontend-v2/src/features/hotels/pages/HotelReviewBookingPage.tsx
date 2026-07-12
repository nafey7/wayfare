/**
 * Hotel review + guest details (single step) — Paula UI layout.
 * Route: /hotels/review-booking
 * After room selection: collect guests, contact, show summary; continue creates Revolut order → payment.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Button, Group, Loader, SimpleGrid, Stack, Text, Textarea, TextInput } from '@mantine/core';
import { Mail } from 'lucide-react';
import { CountrySelect } from '@/components/CountrySelect';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import {
  setGuests,
  setContactEmail,
  setContactPhone,
  setSpecialRequests,
  selectHotelSearchFormParams,
  selectHotelTokenId,
  selectHotelGuests,
  selectHotelContactEmail,
  selectHotelContactPhone,
  selectHotelSpecialRequests,
  selectSelectedHotel,
  selectSelectedRoom,
  selectRateRulesResponse,
  selectHotelVoucherRedemptionId,
  selectHotelVoucherDiscountCents,
  selectHotelVoucherCheckoutRef,
  selectHotelVoucherAppliedCode,
  selectHotelVoucherReservationExpiresAt,
  setHotelVoucher,
  selectHotelTripType,
  selectMultistayLegs,
  selectMultistaySegments,
} from '@/store/slices/hotelBookingSlice';
import { selectCurrentUser } from '@/store/slices/authSlice';
import { useReleaseVoucherMutation } from '@/api/vouchersApi';
import { PromoCodeField } from '@/features/discount/components/PromoCodeField';
import type { HotelItinerary, HotelGuestDetails, RoomOccupancy } from '@/types/hotels';
import { GuestForm, type GuestSlot } from '../components/GuestForm';
import {
  buildE164Phone,
  validateEmail,
  validatePhoneWithCountryCode,
} from '../utils/validation';
import {
  DEFAULT_CURRENCY,
  formatHotelPrice,
  formatCompactHotelStayLine,
  getNightsBetweenDates,
} from '../utils/hotelUtils';
import { resolveHotelImageUrl } from '../utils/imageUtils';
import { ageFromIsoDateOfBirth } from '../utils/ageFromDateOfBirth';
import {
  applySavedPassengerSelectionWithDedup,
  inferInitialSavedPassengerMap,
} from '../utils/savedPassengerSlotUtils';
import { trackEvent } from '@/utils/gtm';
import { showErrorToast } from '@/utils/toast';
import { countries } from '@/data';
import { useGetPassengersQuery, useUpdatePassengerMutation } from '@/api/usersApi';
import {
  isMaskedPassportValue,
  isMaskedFrequentFlyerValue,
} from '@/features/flights/utils/passengerStorageUtils';
import type { PassengerCreateRequest, PassengerUpdateRequest, StoredPassenger } from '@/types/passengers';
import { PassengerFormDialog } from '@/features/profile/components/travelDetails/PassengerFormDialog';
import { useCreateRevolutOrderMutation } from '@/api/revolutPaymentsApi';
import { HotelBookingReviewLayout } from '../components/HotelBookingReviewLayout';
import { HotelDetailRoomCard } from '../components/hotelDetail';
import hotelFallback from '@/assets/images/hotels/hotel-fallback.svg';

const DEFAULT_PLATFORM_FEE_PERCENTAGE = 10.5;

/** Longer than default so users can read while fixing guest/contact fields (toast is fixed; layout scrolls). */
const HOTEL_REVIEW_PAYMENT_ERROR_TOAST = { autoClose: 12_000 };

function buildGuestSlotsFromRooms(rooms: RoomOccupancy[] | null): { roomNumber: number; slots: GuestSlot[] }[] {
  if (!rooms) return [];
  const result: { roomNumber: number; slots: GuestSlot[] }[] = [];
  rooms.forEach((room, roomIndex) => {
    const roomNumber = roomIndex + 1;
    const adults = Math.max(1, room.adult ?? 1);
    const childCount = room.child ?? 0;
    const childAges = room.childAge ?? Array.from({ length: childCount }, () => 0);
    const slots: GuestSlot[] = [];
    for (let i = 0; i < adults; i++) {
      slots.push({ isChild: false, label: `Adult ${i + 1}` });
    }
    for (let i = 0; i < childCount; i++) {
      slots.push({
        isChild: true,
        age: childAges[i] ?? 0,
        label: `Child ${i + 1}`,
      });
    }
    result.push({ roomNumber, slots });
  });
  return result;
}

function buildEmptyGuests(roomBlocks: { roomNumber: number; slots: GuestSlot[] }[]): HotelGuestDetails[] {
  const list: HotelGuestDetails[] = [];
  roomBlocks.forEach(({ roomNumber, slots }) => {
    slots.forEach((slot) => {
      list.push(emptyGuestForSlot(roomNumber, slot));
    });
  });
  return list;
}

function emptyGuestForSlot(roomNumber: number, slot: GuestSlot): HotelGuestDetails {
  return {
    title: slot.isChild ? 'Master' : 'Mr',
    firstName: '',
    lastName: '',
    roomNumber,
    isChild: slot.isChild,
    age: slot.isChild ? (slot.age ?? 0) : undefined,
  };
}

function getSlotAtGlobalIndex(
  roomBlocks: { roomNumber: number; slots: GuestSlot[] }[],
  globalIndex: number
): { roomNumber: number; slot: GuestSlot } | null {
  let idx = 0;
  for (const { roomNumber, slots } of roomBlocks) {
    for (const slot of slots) {
      if (idx === globalIndex) return { roomNumber, slot };
      idx += 1;
    }
  }
  return null;
}

function guestFieldsEqual(a: HotelGuestDetails, b: HotelGuestDetails): boolean {
  return (
    a.title === b.title &&
    a.firstName === b.firstName &&
    a.lastName === b.lastName &&
    a.roomNumber === b.roomNumber &&
    a.isChild === b.isChild &&
    a.age === b.age
  );
}

/** When room occupancy changes, keep existing rows by index when slot shape matches; only new/changed slots reset. */
function guestsAlignedWithRooms(
  prev: HotelGuestDetails[],
  roomBlocks: { roomNumber: number; slots: GuestSlot[] }[]
): HotelGuestDetails[] {
  const totalSlots = roomBlocks.reduce((sum, b) => sum + b.slots.length, 0);
  const next: HotelGuestDetails[] = [];
  for (let i = 0; i < totalSlots; i++) {
    const meta = getSlotAtGlobalIndex(roomBlocks, i);
    if (!meta) continue;
    const old = prev[i];
    if (old && old.roomNumber === meta.roomNumber && old.isChild === meta.slot.isChild) {
      if (meta.slot.isChild && old.isChild) {
        const slotAge = meta.slot.age ?? 0;
        if ((old.age ?? 0) !== slotAge) {
          next.push({ ...old, age: slotAge });
        } else {
          next.push(old);
        }
      } else {
        next.push(old);
      }
    } else {
      next.push(emptyGuestForSlot(meta.roomNumber, meta.slot));
    }
  }
  return next;
}

function parseE164ToCountryAndLocal(e164: string): { countryCode: string; localNumber: string } {
  const digits = (e164 ?? '').replace(/\D/g, '');
  if (!digits.length) return { countryCode: '', localNumber: '' };
  const sorted = [...countries].sort((a, b) => {
    const pa = (a.phone ?? '').replace(/\D/g, '');
    const pb = (b.phone ?? '').replace(/\D/g, '');
    return pb.length - pa.length;
  });
  for (const c of sorted) {
    const code = (c.phone ?? '').replace(/\D/g, '');
    if (code && digits.startsWith(code) && digits.length > code.length) {
      return { countryCode: c.phone ?? '', localNumber: digits.slice(code.length) };
    }
  }
  return { countryCode: '', localNumber: digits };
}

function getHotelDisplayName(hotel: HotelItinerary | null): string {
  if (!hotel) return '';
  return hotel.name ?? (hotel as { hotelName?: string }).hotelName ?? 'Hotel';
}

export function HotelReviewBookingPage() {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const tripType = useAppSelector(selectHotelTripType);
  const multistayLegs = useAppSelector(selectMultistayLegs);
  const multistaySegments = useAppSelector(selectMultistaySegments);
  const searchFormParams = useAppSelector(selectHotelSearchFormParams);
  const tokenId = useAppSelector(selectHotelTokenId);
  const reduxGuests = useAppSelector(selectHotelGuests);
  const reduxContactEmail = useAppSelector(selectHotelContactEmail);
  const reduxContactPhone = useAppSelector(selectHotelContactPhone);
  const reduxSpecialRequests = useAppSelector(selectHotelSpecialRequests);
  const selectedHotel = useAppSelector(selectSelectedHotel);
  const selectedRoom = useAppSelector(selectSelectedRoom);
  const rateRulesResponse = useAppSelector(selectRateRulesResponse);
  const voucherRedemptionId = useAppSelector(selectHotelVoucherRedemptionId);
  const voucherDiscountCents = useAppSelector(selectHotelVoucherDiscountCents);
  const voucherCheckoutRef = useAppSelector(selectHotelVoucherCheckoutRef);
  const voucherAppliedCode = useAppSelector(selectHotelVoucherAppliedCode);
  const voucherReservationExpiresAt = useAppSelector(selectHotelVoucherReservationExpiresAt);
  const user = useAppSelector(selectCurrentUser);

  // ── Multi-stay computed values (declared early so useEffects below can reference them) ──
  const isMultistay = tripType === 'multi-stay';
  const allMultistayLegsReady = useMemo(
    () =>
      isMultistay &&
      multistayLegs.length > 0 &&
      multistayLegs.every((leg) => leg.selectedHotel && leg.selectedRoom && leg.rateRulesResponse),
    [isMultistay, multistayLegs]
  );
  const multistayTotalMajor = useMemo(
    () =>
      multistayLegs.reduce((sum, leg) => {
        const raw = leg.rateRulesResponse?.netPrice ?? leg.selectedRoom?.totalPrice ?? 0;
        return sum + (Number(raw) || 0);
      }, 0),
    [multistayLegs]
  );
  const multistayFirstCurrency = useMemo(
    () =>
      multistayLegs[0]?.rateRulesResponse?.currency ??
      multistayLegs[0]?.selectedRoom?.currency ??
      DEFAULT_CURRENCY,
    [multistayLegs]
  );

  const bookingPricing = useMemo(() => {
    const currency =
      selectedHotel?.startingPrice?.currency ??
      selectedRoom?.currency ??
      rateRulesResponse?.currency ??
      (selectedHotel as { currency?: string })?.currency ??
      DEFAULT_CURRENCY;
    const paymentLineTotal =
      selectedRoom?.totalPrice ?? rateRulesResponse?.netPrice ?? selectedHotel?.total ?? 0;
    const displayLineTotal =
      selectedRoom?.totalPrice ?? rateRulesResponse?.netPrice ?? selectedHotel?.total ?? 0;
    return { currency, paymentLineTotal, displayLineTotal };
  }, [selectedHotel, selectedRoom, rateRulesResponse]);

  const hotelLightboxImages = useMemo(() => {
    const h = selectedHotel;
    if (!h) return [hotelFallback];
    const seen = new Set<string>();
    const out: string[] = [];
    const push = (raw: string | undefined) => {
      if (!raw?.trim()) return;
      const resolved = resolveHotelImageUrl(raw);
      if (resolved && !seen.has(resolved)) {
        seen.add(resolved);
        out.push(resolved);
      }
    };
    push(h.thumbnailUrl ?? h.imageUrl ?? h.images?.[0]);
    for (const u of h.images ?? []) {
      push(u);
    }
    return out.length ? out : [hotelFallback];
  }, [selectedHotel]);

  const guestFormsRef = useRef<HTMLDivElement | null>(null);
  /** Per guest index: saved passenger id or manual (Figma radio cards). */
  const [savedPassengerByGuestIndex, setSavedPassengerByGuestIndex] = useState<
    Record<number, string | 'manual'>
  >({});
  const savedPassengerByGuestIndexRef = useRef(savedPassengerByGuestIndex);
  savedPassengerByGuestIndexRef.current = savedPassengerByGuestIndex;
  const [createRevolutOrder, { isLoading: isCreatingRevolutOrder }] = useCreateRevolutOrderMutation();
  const [updatePassengerMut] = useUpdatePassengerMutation();
  const [releaseVoucherApi] = useReleaseVoucherMutation();

  const [passengerModal, setPassengerModal] = useState<{
    open: boolean;
    editPassengerId: string | null;
  }>({
    open: false,
    editPassengerId: null,
  });

  const closePassengerModal = () =>
    setPassengerModal({
      open: false,
      editPassengerId: null,
    });

  const checkin = searchFormParams?.checkin ?? null;
  const checkout = searchFormParams?.checkout ?? null;
  const nights = getNightsBetweenDates(checkin, checkout);

  const roomBlocks = useMemo(
    () => buildGuestSlotsFromRooms(searchFormParams.rooms),
    [searchFormParams.rooms]
  );
  const totalSlots = useMemo(
    () => roomBlocks.reduce((sum, b) => sum + b.slots.length, 0),
    [roomBlocks]
  );

  const roomBlocksWithStart = useMemo(() => {
    let start = 0;
    return roomBlocks.map((block) => {
      const s = start;
      start += block.slots.length;
      return { ...block, startIndex: s };
    });
  }, [roomBlocks]);

  const [guests, setGuestsState] = useState<HotelGuestDetails[]>(() =>
    reduxGuests.length === totalSlots ? reduxGuests : buildEmptyGuests(roomBlocks)
  );
  const [contactEmail, setContactEmailState] = useState(reduxContactEmail || user?.email || '');
  const [contactPhoneCountryCode, setContactPhoneCountryCode] = useState('');
  const [contactPhoneLocal, setContactPhoneLocal] = useState('');
  const [specialRequests, setSpecialRequestsState] = useState(reduxSpecialRequests || '');
  const [touched, setTouched] = useState(false);
  const { data: savedPassengers = [] } = useGetPassengersQuery();

  const passengerModalEditData = useMemo((): StoredPassenger | null => {
    if (!passengerModal.open || !passengerModal.editPassengerId) {
      return null;
    }
    return savedPassengers.find((p) => p.id === passengerModal.editPassengerId) ?? null;
  }, [passengerModal.open, passengerModal.editPassengerId, savedPassengers]);

  useEffect(() => {
    if (reduxContactPhone && reduxContactPhone.startsWith('+')) {
      const { countryCode, localNumber } = parseE164ToCountryAndLocal(reduxContactPhone);
      if (countryCode) setContactPhoneCountryCode(countryCode);
      if (localNumber) setContactPhoneLocal(localNumber);
    } else if (user?.phone) {
      // Tech debt: leading "1" + length heuristic mis-classifies some non-US numbers; prefer libphonenumber-js if we normalize profile phones here.
      const normalized = user.phone.replace(/\D/g, '');
      if (normalized.startsWith('1') && normalized.length >= 10) {
        setContactPhoneCountryCode('1');
        setContactPhoneLocal(normalized.slice(1));
      } else {
        const parsed = parseE164ToCountryAndLocal(user.phone);
        if (parsed.countryCode) setContactPhoneCountryCode(parsed.countryCode);
        if (parsed.localNumber) setContactPhoneLocal(parsed.localNumber);
      }
    }
  }, [reduxContactPhone, user?.phone]);

  // Infer saved-passenger mode for slots with no explicit choice once profiles load.
  // Map + Set: O(n) per slot; duplicate names resolve to first saved profile (same as prior find).
  useEffect(() => {
    setSavedPassengerByGuestIndex((prev) =>
      inferInitialSavedPassengerMap(prev, savedPassengers, guests, totalSlots)
    );
  }, [savedPassengers, guests, totalSlots]);

  useEffect(() => {
    if (!user) return;
    setGuestsState((prev) => {
      if (prev.length === 0) return prev;
      const firstBlock = roomBlocks[0];
      if (!firstBlock) return prev;
      const firstAdultLocal = firstBlock.slots.findIndex((s) => !s.isChild);
      if (firstAdultLocal === -1) return prev;
      const leadIndex = firstAdultLocal;
      const current = prev[leadIndex];
      if (!current || (current.firstName?.trim() && current.lastName?.trim())) return prev;
      const next = [...prev];
      next[leadIndex] = {
        ...next[leadIndex]!,
        firstName: (current.firstName?.trim() || user.firstName) ?? '',
        lastName: (current.lastName?.trim() || user.lastName) ?? '',
      };
      return next;
    });
  }, [user, roomBlocks]);

  useEffect(() => {
    setGuestsState((prev) => {
      const aligned = guestsAlignedWithRooms(prev, roomBlocks);
      if (
        aligned.length === prev.length &&
        aligned.every((g, i) => guestFieldsEqual(g, prev[i]!))
      ) {
        return prev;
      }
      return aligned;
    });
  }, [roomBlocks]);

  const reviewShownTrackedRef = useRef(false);
  useEffect(() => {
    if (reviewShownTrackedRef.current) return;
    if (isMultistay) {
      if (!allMultistayLegsReady) return;
      reviewShownTrackedRef.current = true;
      trackEvent('hotel_booking_review_shown', {
        stay_count: multistayLegs.length,
        total_price: multistayTotalMajor,
        currency: multistayFirstCurrency,
      });
      return;
    }
    if (!selectedHotel || !selectedRoom || !rateRulesResponse) return;
    reviewShownTrackedRef.current = true;
    trackEvent('hotel_booking_review_shown', {
      hotel_name: getHotelDisplayName(selectedHotel),
      total_price: bookingPricing.paymentLineTotal,
      currency: bookingPricing.currency,
      nights,
      rooms: searchFormParams?.rooms?.length ?? 1,
      guest_count: guests.length,
    });
  }, [
    isMultistay,
    allMultistayLegsReady,
    multistayLegs.length,
    multistayTotalMajor,
    multistayFirstCurrency,
    bookingPricing,
    selectedHotel,
    selectedRoom,
    rateRulesResponse,
    nights,
    searchFormParams?.rooms?.length,
    guests.length,
  ]);

  useEffect(() => {
    if (isMultistay) {
      if (!allMultistayLegsReady) navigate('/hotels/search', { replace: true });
      return;
    }
    if (selectedHotel && tokenId && selectedRoom && rateRulesResponse) return;
    if (tokenId) navigate(`/hotels/rooms/${tokenId}`, { replace: true });
    else navigate('/hotels/search', { replace: true });
  }, [isMultistay, allMultistayLegsReady, selectedHotel, tokenId, selectedRoom, rateRulesResponse, navigate]);

  const updateGuest = (
    globalIndex: number,
    field: keyof Pick<HotelGuestDetails, 'title' | 'firstName' | 'lastName' | 'age'>,
    value: string | number
  ) => {
    setSavedPassengerByGuestIndex((prev) => ({ ...prev, [globalIndex]: 'manual' }));
    setGuestsState((prev) => {
      const next = [...prev];
      if (!next[globalIndex]) return prev;
      next[globalIndex] = { ...next[globalIndex]!, [field]: value };
      return next;
    });
  };

  /** One saved passenger per booking: selecting an id elsewhere clears it from other slots (any room / type). */
  const handleSavedPassengerModeChange = useCallback(
    (globalIndex: number, value: string | 'manual') => {
      const prevMap = savedPassengerByGuestIndexRef.current;
      setSavedPassengerByGuestIndex((prev) =>
        applySavedPassengerSelectionWithDedup(prev, globalIndex, value, totalSlots)
      );

      if (typeof value === 'string' && value !== 'manual') {
        setGuestsState((prevGuests) => {
          let changed = false;
          const nextGuests = [...prevGuests];
          for (let i = 0; i < totalSlots; i++) {
            if (i === globalIndex) continue;
            if (prevMap[i] !== value) continue;
            const meta = getSlotAtGlobalIndex(roomBlocks, i);
            if (!meta || !nextGuests[i]) continue;
            nextGuests[i] = emptyGuestForSlot(meta.roomNumber, meta.slot);
            changed = true;
          }
          return changed ? nextGuests : prevGuests;
        });
      }
    },
    [totalSlots, roomBlocks]
  );

  const handleSelectSavedPassenger = (
    startIndex: number,
    localIndex: number,
    p: { title: string; firstName: string; lastName: string; dateOfBirth: string }
  ) => {
    const globalIndex = startIndex + localIndex;
    setGuestsState((prev) => {
      const current = prev[globalIndex];
      if (!current) return prev;
      const age = p.dateOfBirth ? ageFromIsoDateOfBirth(p.dateOfBirth) : undefined;
      const next = [...prev];
      next[globalIndex] = {
        ...next[globalIndex]!,
        title: p.title as HotelGuestDetails['title'],
        firstName: p.firstName,
        lastName: p.lastName,
        roomNumber: current.roomNumber,
        isChild: current.isChild,
        age: current.isChild ? age : undefined,
      };
      return next;
    });
  };

  const handlePassengerDialogUpdate = async (data: PassengerCreateRequest) => {
    const id = passengerModal.editPassengerId;
    if (!id) return;
    const body: PassengerUpdateRequest = {
      title: data.title,
      firstName: data.firstName,
      lastName: data.lastName,
      dateOfBirth: data.dateOfBirth,
      nationality: data.nationality,
      email: data.email,
      phone: data.phone,
      type: data.type,
      isPrimary: data.isPrimary,
    };
    if (!isMaskedPassportValue(data.passportNumber, 'number')) body.passportNumber = data.passportNumber;
    if (!isMaskedPassportValue(data.passportExpiry, 'expiry')) body.passportExpiry = data.passportExpiry;
    if (!isMaskedFrequentFlyerValue(data.frequentFlyerNumber))
      body.frequentFlyerNumber = data.frequentFlyerNumber;
    if (data.passportCountry) body.passportCountry = data.passportCountry;

    const updated = await updatePassengerMut({ passengerId: id, body }).unwrap();

    setGuestsState((prev) =>
      prev.map((g, i) => {
        if (savedPassengerByGuestIndex[i] !== id) return g;
        const age = updated.dateOfBirth ? ageFromIsoDateOfBirth(updated.dateOfBirth) : undefined;
        const titleForSlot = g.isChild ? (updated.hotelTitle ?? updated.title) : updated.title;
        return {
          ...g,
          title: titleForSlot as HotelGuestDetails['title'],
          firstName: updated.firstName,
          lastName: updated.lastName,
          age: g.isChild ? age : undefined,
        };
      })
    );
  };

  const handleFooterBack = useCallback(async () => {
    if (voucherRedemptionId) {
      try {
        await releaseVoucherApi({ redemptionId: voucherRedemptionId }).unwrap();
      } catch {
        /* best-effort */
      }
      dispatch(setHotelVoucher(null));
    }
    navigate(-1);
  }, [voucherRedemptionId, releaseVoucherApi, dispatch, navigate]);

  const handleContinueToPayment = async () => {
    setTouched(true);

    const e164 = buildE164Phone(contactPhoneCountryCode, contactPhoneLocal);
    const emailValid = validateEmail(contactEmail);
    const phoneValid = validatePhoneWithCountryCode(contactPhoneCountryCode, contactPhoneLocal);
    const allGuestsValid = guests.every(
      (g) =>
        g.title &&
        (g.firstName ?? '').trim() &&
        (g.lastName ?? '').trim() &&
        (!g.isChild || (g.age != null && g.age >= 0 && g.age <= 17))
    );

    if (!emailValid || !phoneValid || !allGuestsValid) {
      showErrorToast('Please complete guest and contact details.', HOTEL_REVIEW_PAYMENT_ERROR_TOAST);
      guestFormsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      return;
    }

    dispatch(setGuests(guests));
    dispatch(setContactEmail(contactEmail.trim()));
    dispatch(setContactPhone(e164));
    dispatch(setSpecialRequests(specialRequests.trim()));

    trackEvent('hotel_guest_details_completed', {
      guest_count: guests.length,
      rooms: roomBlocks.length,
    });

    const totalMajor = isMultistay ? multistayTotalMajor : bookingPricing.paymentLineTotal;
    const currencyCode = isMultistay ? multistayFirstCurrency : bookingPricing.currency;

    if (totalMajor <= 0) {
      showErrorToast('Invalid hotel price.', HOTEL_REVIEW_PAYMENT_ERROR_TOAST);
      return;
    }

    const preCents = Math.round(totalMajor * 100);
    const vDisc = voucherDiscountCents ?? 0;
    const payCents = Math.max(0, preCents - vDisc);
    if (payCents <= 0) {
      showErrorToast('Total after discount must be greater than zero.', HOTEL_REVIEW_PAYMENT_ERROR_TOAST);
      return;
    }

    try {
      const created = await createRevolutOrder({
        bookingAmount: payCents,
        currency: currencyCode.toLowerCase(),
        voyaBookingReference: voucherCheckoutRef ?? undefined,
        orderType: 'hotel',
        voucherRedemptionId: voucherRedemptionId ?? undefined,
      }).unwrap();

      navigate('/hotels/payment', {
        state: {
          revolutOrder: {
            orderId: created.orderId,
            publicOrderId: created.publicOrderId,
            amount: created.amount,
            currency: created.currency,
            supplierAmount: created.supplierAmount,
            voyaBookingReference: created.voyaBookingReference,
          },
        },
      });
    } catch (err) {
      if (voucherRedemptionId) {
        try {
          await releaseVoucherApi({ redemptionId: voucherRedemptionId }).unwrap();
        } catch {
          /* best-effort */
        }
        dispatch(setHotelVoucher(null));
      }
      showErrorToast(
        err instanceof Error ? err.message : 'Failed to initialize payment. Please try again.',
        HOTEL_REVIEW_PAYMENT_ERROR_TOAST
      );
    }
  };

  const shouldRedirect =
    !isMultistay && (!selectedHotel || !tokenId || !selectedRoom || !rateRulesResponse);
  const multistayNotReady = isMultistay && !allMultistayLegsReady;
  if (shouldRedirect || multistayNotReady) {
    return (
      <Group justify="center" align="center" style={{ width: '100%', minHeight: 200 }}>
        <Loader />
      </Group>
    );
  }

  // ── Multi-stay JSX ────────────────────────────────────────────
  if (isMultistay) {
    const completeGuestsMs = guests.filter(
      (g) =>
        g.title &&
        (g.firstName ?? '').trim() &&
        (g.lastName ?? '').trim() &&
        (!g.isChild || (g.age != null && g.age >= 0 && g.age <= 17))
    );
    return (
      <Box style={{ width: '100%', flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        <Stack gap="md" p="md" mx="auto" style={{ maxWidth: 800, width: '100%' }}>
          <Text component="h2" fw={700} style={{ fontSize: 24, lineHeight: '32px' }}>
            Review your multi-stay booking
          </Text>

          {/* Per-leg summaries */}
          {multistayLegs.map((leg, i) => {
            const seg = multistaySegments[i];
            const legNights = (() => {
              const a = seg?.checkin ? new Date(seg.checkin) : null;
              const b = seg?.checkout ? new Date(seg.checkout) : null;
              return a && b ? Math.max(1, Math.ceil((b.getTime() - a.getTime()) / 86400000)) : 1;
            })();
            const legPrice = leg.rateRulesResponse?.netPrice ?? leg.selectedRoom?.totalPrice ?? 0;
            const legCurrency = leg.rateRulesResponse?.currency ?? leg.selectedRoom?.currency ?? 'USD';
            return (
              <Box
                key={i}
                p="sm"
                style={{
                  borderRadius: 8,
                  border: '1px solid var(--mantine-color-default-border)',
                  backgroundColor: 'var(--mantine-color-body)',
                }}
              >
                <Text fw={700} mb={4}>
                  Stay {i + 1}: {seg?.destination || leg.selectedHotel?.city || ''}
                </Text>
                <Text size="sm" c="dimmed" mb={2}>
                  {leg.selectedHotel?.name}
                </Text>
                {seg?.checkin && seg?.checkout && (
                  <Text size="sm" c="dimmed" mb={2}>
                    {formatCompactHotelStayLine(seg.checkin, seg.checkout, legNights)}
                  </Text>
                )}
                {leg.selectedRoom && (
                  <Text size="sm" c="dimmed">
                    {leg.selectedRoom.roomType ?? 'Room selected'}
                  </Text>
                )}
                <Text size="sm" fw={600} mt={4}>
                  {formatHotelPrice(legPrice, legCurrency)}
                </Text>
              </Box>
            );
          })}

          {/* Combined total */}
          <Box
            p="sm"
            style={{
              borderRadius: 8,
              backgroundColor: 'var(--mantine-color-navy-1)',
              border: '1px solid var(--mantine-color-navy-3)',
            }}
          >
            <Text fw={700}>
              Combined Total: {formatHotelPrice(multistayTotalMajor, multistayFirstCurrency)}
            </Text>
            <Text size="xs" c="dimmed">
              Taxes and fees included
            </Text>
          </Box>

          {/* Guest form using first stay's rooms */}
          <Box ref={guestFormsRef}>
            {roomBlocksWithStart.map(({ roomNumber, slots, startIndex }, blockIndex) => {
              const roomGuests = guests.slice(startIndex, startIndex + slots.length);
              return (
                <GuestForm
                  key={roomNumber}
                  roomNumber={roomNumber}
                  globalSlotStartIndex={startIndex}
                  savedPassengerByGuestIndex={savedPassengerByGuestIndex}
                  onSavedPassengerModeChange={handleSavedPassengerModeChange}
                  slots={slots}
                  guests={roomGuests}
                  onChange={(localIndex, field, value) =>
                    updateGuest(startIndex + localIndex, field, value)
                  }
                  touched={touched}
                  isLeadGuest={blockIndex === 0}
                  savedPassengers={savedPassengers}
                  onSelectSaved={(localIndex, p) =>
                    handleSelectSavedPassenger(startIndex, localIndex, p)
                  }
                  onEditPassenger={(passengerId) =>
                    setPassengerModal({ open: true, editPassengerId: passengerId })
                  }
                />
              );
            })}
          </Box>

          {/* Contact section */}
          <Box
            p="sm"
            style={{
              borderRadius: 8,
              backgroundColor: 'var(--mantine-color-green-1)',
              border: '1px solid var(--mantine-color-green-6)',
            }}
          >
            <Group align="center" gap="xs" mb="sm">
              <Mail size={18} color="var(--mantine-color-green-8)" />
              <Text fw={600} size="sm">Contact information</Text>
            </Group>
            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
              <TextInput
                label="Email"
                type="email"
                value={contactEmail}
                onChange={(e) => setContactEmailState(e.currentTarget.value)}
                size="sm"
                required
                error={touched && !validateEmail(contactEmail) ? (contactEmail ? 'Enter a valid email' : 'Email is required') : undefined}
              />
              <Group gap={0} align="flex-start" wrap="nowrap">
                <CountrySelect
                  variant="phone"
                  label="Code"
                  value={contactPhoneCountryCode}
                  onChange={setContactPhoneCountryCode}
                  size="small"
                  required
                  error={touched && !contactPhoneCountryCode.trim()}
                />
                <TextInput
                  label="Phone"
                  value={contactPhoneLocal}
                  onChange={(e) => setContactPhoneLocal(e.currentTarget.value)}
                  size="sm"
                  required
                  placeholder="e.g. 5551234567"
                  error={touched && !validatePhoneWithCountryCode(contactPhoneCountryCode, contactPhoneLocal) ? 'Enter a valid phone number' : undefined}
                  style={{ flex: 1 }}
                />
              </Group>
            </SimpleGrid>
            <Textarea
              label="Special requests (optional)"
              value={specialRequests}
              onChange={(e) => setSpecialRequestsState(e.currentTarget.value)}
              size="sm"
              rows={2}
              mt="md"
            />
          </Box>

          {/* Action buttons */}
          <Group justify="flex-end" gap="md">
            <Button variant="outline" color="gray" radius="md" onClick={() => navigate(-1)}>
              Back
            </Button>
            <Button
              radius="md"
              fw={600}
              disabled={isCreatingRevolutOrder}
              onClick={() => void handleContinueToPayment()}
              leftSection={isCreatingRevolutOrder ? <Loader size="xs" color="white" /> : undefined}
            >
              {isCreatingRevolutOrder ? 'Processing…' : `Continue to payment · ${formatHotelPrice(multistayTotalMajor, multistayFirstCurrency)}`}
            </Button>
          </Group>

          <Text size="xs" c="dimmed" ta="center">
            {completeGuestsMs.length} guest{completeGuestsMs.length !== 1 ? 's' : ''} · {multistayLegs.length} stay{multistayLegs.length !== 1 ? 's' : ''}
          </Text>
        </Stack>

        <PassengerFormDialog
          open={passengerModal.open}
          onClose={closePassengerModal}
          onSubmit={handlePassengerDialogUpdate}
          initialData={passengerModalEditData ?? undefined}
          isUpdate
        />
      </Box>
    );
  }

  // ── Single-stay JSX ───────────────────────────────────────────
  // TypeScript narrowing: after the multi-stay early return and shouldRedirect guard,
  // selectedHotel/selectedRoom/rateRulesResponse are guaranteed non-null for single-stay.
  if (!selectedHotel || !selectedRoom || !rateRulesResponse) return null;

  const currency = bookingPricing.currency;
  const platformFeePercentage =
    selectedHotel?.platformFeePercentage ??
    rateRulesResponse?.platformFeePercentage ??
    DEFAULT_PLATFORM_FEE_PERCENTAGE;
  const totalAmount = bookingPricing.displayLineTotal;
  const hotelAmount =
    rateRulesResponse?.originalNetPrice ??
    selectedRoom?.originalTotalPrice ??
    selectedHotel?.originalTotal ??
    (totalAmount > 0 ? totalAmount * (1 - platformFeePercentage / 100) : 0);
  const platformFee = Math.max(0, totalAmount - hotelAmount);
  const voucherDiscMajor = (voucherDiscountCents ?? 0) / 100;
  const totalChargedForDisplay = Math.max(0, totalAmount - voucherDiscMajor);

  const hotelThumb =
    resolveHotelImageUrl(
      selectedHotel.thumbnailUrl ?? selectedHotel.imageUrl ?? selectedHotel.images?.[0]
    ) ?? hotelFallback;

  const preDiscountCents = Math.max(0, Math.round(totalAmount * 100));
  const showUsdVoucher = currency.toUpperCase() === 'USD';

  const dateLine = formatCompactHotelStayLine(checkin, checkout, nights);
  const addressLine = [selectedHotel.address, selectedHotel.city].filter(Boolean).join(', ');

  const completeGuests = guests.filter(
    (g) =>
      g.title &&
      (g.firstName ?? '').trim() &&
      (g.lastName ?? '').trim() &&
      (!g.isChild || (g.age != null && g.age >= 0 && g.age <= 17))
  );
  const selectedBullets = completeGuests.map(
    (g) => `${g.title} ${g.firstName} ${g.lastName}`.trim()
  );

  return (
    <Box
      style={{
        width: '100%',
        flex: 1,
        minHeight: 0,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <HotelBookingReviewLayout
        subtitle="Please review your hotel details, passengers, and contact information before proceeding."
        dateLine={dateLine}
        hotelName={getHotelDisplayName(selectedHotel)}
        hotelImageUrl={hotelThumb}
        hotelLightboxImages={hotelLightboxImages}
        hotelAddressLine={addressLine}
        onShowOnMap={() => {
          const lat = selectedHotel.latitude;
          const lng = selectedHotel.longitude;
          if (lat != null && lng != null) {
            window.open(`https://www.google.com/maps/search/?api=1&query=${lat},${lng}`, '_blank');
          }
        }}
        selectedRoomCard={
          <HotelDetailRoomCard
            room={selectedRoom}
            stayNights={nights}
            showReserveButton={false}
            matchHotelSummaryImage
          />
        }
        hotelAmountLabel={`🏨 Hotel Amount (${nights} night${nights !== 1 ? 's' : ''})`}
        hotelAmountDisplay={formatHotelPrice(hotelAmount, currency)}
        platformFeeLabel={`💼 Platform Fee (${platformFeePercentage}%)`}
        platformFeeDisplay={formatHotelPrice(platformFee, currency)}
        totalAmountDisplay={formatHotelPrice(
          totalChargedForDisplay,
          currency
        )}
        totalSubtext={
          voucherDiscMajor > 0
            ? `after promo · taxes and fees included · ${completeGuests.length} guest${completeGuests.length !== 1 ? 's' : ''}`
            : `taxes and fees included · ${completeGuests.length} guest${completeGuests.length !== 1 ? 's' : ''}`
        }
        guestForms={
          <Box ref={guestFormsRef} style={{ width: '100%' }}>
            {roomBlocksWithStart.map(({ roomNumber, slots, startIndex }, blockIndex) => {
              const roomGuests = guests.slice(startIndex, startIndex + slots.length);
              return (
                <GuestForm
                  key={roomNumber}
                  roomNumber={roomNumber}
                  globalSlotStartIndex={startIndex}
                  savedPassengerByGuestIndex={savedPassengerByGuestIndex}
                  onSavedPassengerModeChange={handleSavedPassengerModeChange}
                  slots={slots}
                  guests={roomGuests}
                  onChange={(localIndex, field, value) =>
                    updateGuest(startIndex + localIndex, field, value)
                  }
                  touched={touched}
                  isLeadGuest={blockIndex === 0}
                  savedPassengers={savedPassengers}
                  onSelectSaved={(localIndex, p) =>
                    handleSelectSavedPassenger(startIndex, localIndex, p)
                  }
                  onEditPassenger={(passengerId) =>
                    setPassengerModal({
                      open: true,
                      editPassengerId: passengerId,
                    })
                  }
                />
              );
            })}
          </Box>
        }
        contactSection={
          <Box
            mt={4}
            p="sm"
            style={{
              borderRadius: 12,
              backgroundColor: 'var(--mantine-color-green-1)',
              border: '1px solid var(--mantine-color-green-6)',
              width: '100%',
            }}
          >
            <Group align="center" gap="xs" mb="sm">
              <Mail size={18} color="var(--mantine-color-green-8)" />
              <Text fw={600} size="sm">
                Contact information
              </Text>
            </Group>
            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
              <TextInput
                label="Email"
                type="email"
                value={contactEmail}
                onChange={(e) => setContactEmailState(e.currentTarget.value)}
                size="sm"
                required
                error={
                  touched && !validateEmail(contactEmail)
                    ? contactEmail
                      ? 'Enter a valid email'
                      : 'Email is required'
                    : undefined
                }
              />
              <Group gap={0} align="flex-start" wrap="nowrap">
                <CountrySelect
                  variant="phone"
                  label="Code"
                  value={contactPhoneCountryCode}
                  onChange={setContactPhoneCountryCode}
                  size="small"
                  required
                  error={touched && !contactPhoneCountryCode.trim()}
                />
                <TextInput
                  label="Phone"
                  value={contactPhoneLocal}
                  onChange={(e) => setContactPhoneLocal(e.currentTarget.value)}
                  size="sm"
                  required
                  placeholder="e.g. 5551234567"
                  error={
                    touched && !validatePhoneWithCountryCode(contactPhoneCountryCode, contactPhoneLocal)
                      ? contactPhoneCountryCode || contactPhoneLocal
                        ? 'Enter a valid phone number (E.164)'
                        : 'Phone number is required'
                      : undefined
                  }
                  style={{ flex: 1 }}
                />
              </Group>
            </SimpleGrid>
            <Textarea
              label="Special requests (optional)"
              value={specialRequests}
              onChange={(e) => setSpecialRequestsState(e.currentTarget.value)}
              size="sm"
              rows={2}
              mt="md"
            />
          </Box>
        }
        selectedSummaryTitle={`Selected for booking: ${completeGuests.length} passenger${completeGuests.length !== 1 ? 's' : ''}`}
        selectedGuestBullets={selectedBullets.length ? selectedBullets : ['—']}
        footerPrimaryLabel="Continue to payment"
        onContinue={handleContinueToPayment}
        continueLoading={isCreatingRevolutOrder}
        onFooterBack={() => void handleFooterBack()}
        preFooterContent={
          showUsdVoucher ? (
            <PromoCodeField
              emphasized
              bookingType="hotel"
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
                  setHotelVoucher({
                    redemptionId: v.redemptionId,
                    discountCents: v.discountCents,
                    checkoutVoyaReference: v.checkoutVoyaReference,
                    code: v.code,
                    reservationExpiresAt: v.reservationExpiresAt ?? null,
                  })
                )
              }
              onCleared={() => dispatch(setHotelVoucher(null))}
            />
          ) : null
        }
      />

      <PassengerFormDialog
        open={passengerModal.open}
        onClose={closePassengerModal}
        onSubmit={handlePassengerDialogUpdate}
        initialData={passengerModalEditData ?? undefined}
        isUpdate
      />
    </Box>
  );
}

import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Box,
  Button,
  Card,
  Checkbox,
  Container,
  Divider,
  Group,
  Loader,
  Select,
  SimpleGrid,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { Mail, IdCard, User } from 'lucide-react';
import { CountrySelect } from '@/components/CountrySelect';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import {
  setPassengers as setPassengersInRedux,
  setContact,
  setPostalCode,
  setFareRules,
  setSavedPassengerId,
  clearSavedPassengerIds,
  updatePassenger as updatePassengerInRedux,
  selectPassengers,
  selectContact,
  selectPostalCode,
  selectSavedPassengerIds,
  selectSessionId,
  selectSearchFormParams,
  selectRevalidationResponse,
  selectSelectedFlightData,
  selectMulticitySelectedLegs,
  setRevalidationResponse,
  setSelectedFlightData,
  type PassengerDetails,
} from '@/store/slices/flightBookingSlice';
import { useGetFareRulesMutation } from '@/api/flightsApi';
import {
  useGetPassengersQuery,
  useCreatePassengerMutation,
} from '@/api/usersApi';
import { trackEvent } from '@/utils/gtm';
import { showErrorToast } from '@/utils/toast';
import { buildFlightSearchRedirectTarget } from '../utils/redirectToSearch';
import { parseFlightBookingState } from '../utils/bookingNavigationState';
import {
  getSortedMulticityLegSelections,
  hasMulticitySelection,
} from '../utils/multicityPricing';
import type { PassengerFareBreakdownItemCamel } from '@/types/flightBackend';
import {
  storedPassengerToFormData,
  formatSavedPassengerLabel,
  hasValidPassportData,
  validateAdultAge,
  validateChildAge,
  validateInfantAge,
  type PassengerFormData,
} from '../utils/passengerStorageUtils';

interface PassengerSlot {
  index: number;
  /** 1-based index within this passenger type for display (Adult 1, Adult 2, Child 1, …) */
  typeIndex: number;
  type: 'Adult' | 'Child' | 'Infant';
  isMain: boolean;
}

export type { PassengerFormData } from '../utils/passengerStorageUtils';

const initialPassenger: PassengerFormData = {
  title: '',
  firstName: '',
  lastName: '',
  dateOfBirth: '',
  nationality: '',
  passportNumber: '',
  passportExpiry: '',
  passportCountry: '',
};

const ADULT_TITLES = [
  { value: 'Mr', label: 'Mr' },
  { value: 'Mrs', label: 'Mrs' },
  { value: 'Miss', label: 'Miss' },
];

const MINOR_TITLES = [
  { value: 'Master', label: 'Master' },
  { value: 'Miss', label: 'Miss' },
];

function getTravellerCountsFromBreakdown(
  passengerBreakdown: PassengerFareBreakdownItemCamel[]
): {
  adults: number;
  children: number;
  infants: number;
} {
  let adults = 0,
    children = 0,
    infants = 0;
  for (const pax of passengerBreakdown) {
    const info = pax.passengerTypeInfo;
    const type = (info?.passengerType ?? '').toUpperCase();
    const count = info?.passengerCount ?? info?.quantity ?? 1;
    if (type === 'ADT') adults += count;
    else if (type === 'CHD') children += count;
    else if (type === 'INF') infants += count;
  }
  if (adults === 0 && children === 0 && infants === 0) adults = 1;
  return { adults, children, infants };
}

function buildPassengerSlots(adults: number, children: number, infants: number): PassengerSlot[] {
  const slots: PassengerSlot[] = [];
  let index = 1;
  for (let i = 0; i < adults; i++) {
    slots.push({ index: index++, typeIndex: i + 1, type: 'Adult', isMain: i === 0 });
  }
  for (let i = 0; i < children; i++) {
    slots.push({ index: index++, typeIndex: i + 1, type: 'Child', isMain: false });
  }
  for (let i = 0; i < infants; i++) {
    slots.push({ index: index++, typeIndex: i + 1, type: 'Infant', isMain: false });
  }
  return slots;
}

/**
 * Passenger Info Page
 * Collects passenger details before booking (inspired by backend dev_ui flight-booker).
 */
function toFormData(d: PassengerDetails): PassengerFormData {
  return {
    title: d.title,
    firstName: d.firstName,
    lastName: d.lastName,
    dateOfBirth: d.dateOfBirth,
    nationality: d.nationality,
    passportNumber: d.passportNumber ?? '',
    passportExpiry: d.passportExpiry ?? '',
    passportCountry: d.passportCountry ?? '',
  };
}

function toDetails(p: PassengerFormData, type: 'adult' | 'child' | 'infant'): PassengerDetails {
  return {
    type,
    title: p.title,
    firstName: p.firstName,
    lastName: p.lastName,
    dateOfBirth: p.dateOfBirth,
    nationality: p.nationality,
    passportNumber: p.passportNumber || undefined,
    passportExpiry: p.passportExpiry || undefined,
    passportCountry: p.passportCountry || undefined,
  };
}

export function PassengerInfoPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useAppDispatch();
  const reduxPassengers = useAppSelector(selectPassengers);
  const reduxContact = useAppSelector(selectContact);
  const reduxPostalCode = useAppSelector(selectPostalCode);
  const searchFormParams = useAppSelector(selectSearchFormParams);
  const reduxRevalidationResponse = useAppSelector(selectRevalidationResponse);
  const reduxSelectedFlightData = useAppSelector(selectSelectedFlightData);
  const savedPassengerIds = useAppSelector(selectSavedPassengerIds);
  const multicitySelectedLegs = useAppSelector(selectMulticitySelectedLegs);

  const state = parseFlightBookingState(location.state) ?? null;
  const revalidateResponse = state?.revalidateResponse ?? reduxRevalidationResponse;
  const selectedFlightData = state?.selectedFlightData ?? reduxSelectedFlightData;

  const segmentCount = searchFormParams.segments?.length ?? 0;
  const isMulticityTrip =
    searchFormParams.tripType === 'multi-city' && segmentCount >= 2;
  const hasMcSelection =
    isMulticityTrip && hasMulticitySelection(multicitySelectedLegs);
  const multicityFirst = hasMcSelection
    ? getSortedMulticityLegSelections(multicitySelectedLegs)[0]
    : undefined;
  const effectiveRevalidate =
    hasMcSelection && multicityFirst
      ? multicityFirst.revalidateResponse
      : revalidateResponse;
  const reduxSessionId = useAppSelector(selectSessionId);
  // Prefer search session_id (from state, Redux, or localStorage)
  const searchSessionId =
    state?.searchSessionId ??
    reduxSessionId ??
    (typeof localStorage !== 'undefined' ? localStorage.getItem('sessionId') : null) ??
    null;

  const [contactEmail, setContactEmail] = useState('');
  const [contactPhoneCountryCode, setContactPhoneCountryCode] = useState('');
  const [contactPhone, setContactPhone] = useState('');
  const [contactPostal, setContactPostal] = useState('');
  const [passengers, setPassengers] = useState<PassengerFormData[]>([]);
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [submitting, setSubmitting] = useState(false);
  const [saveForFuture, setSaveForFuture] = useState(false);
  const [getFareRules] = useGetFareRulesMutation();
  const { data: savedPassengers = [] } = useGetPassengersQuery();
  const [createPassenger] = useCreatePassengerMutation();

  const { adults, children, infants } = useMemo(() => {
    if (!effectiveRevalidate) return { adults: 1, children: 0, infants: 0 };
    const first = effectiveRevalidate.validatedFareItineraries?.[0];
    const pricing = first?.updatedPricing ?? first?.pricing;
    const breakdown = pricing?.passengerFareBreakdown ?? [];
    return getTravellerCountsFromBreakdown(breakdown);
  }, [effectiveRevalidate]);

  const passengerSlots = useMemo(
    () => buildPassengerSlots(adults, children, infants),
    [adults, children, infants]
  );

  // Sync to Redux when receiving via location.state (enables tab-switch persistence)
  useEffect(() => {
    if (state?.revalidateResponse) {
      dispatch(setRevalidationResponse(state.revalidateResponse));
    }
    if (state?.selectedFlightData) {
      dispatch(setSelectedFlightData(state.selectedFlightData));
    }
  }, [state?.revalidateResponse, state?.selectedFlightData, dispatch]);

  useEffect(() => {
    if (isMulticityTrip && !hasMcSelection) {
      navigate(buildFlightSearchRedirectTarget(searchFormParams), { replace: true });
      return;
    }
    if (!hasMcSelection && (!revalidateResponse || !selectedFlightData)) {
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

  // Sync passengers with Redux (same strategy as backend dev_ui passenger_data)
  useEffect(() => {
    if (passengerSlots.length === 0) return;
    if (reduxPassengers.length === passengerSlots.length) {
      setPassengers(reduxPassengers.map(toFormData));
    } else {
      const next = passengerSlots.map(() => ({ ...initialPassenger }));
      setPassengers(next);
      dispatch(clearSavedPassengerIds());
      dispatch(
        setPassengersInRedux(
          next.map((p, i) =>
            toDetails(p, passengerSlots[i]!.type.toLowerCase() as 'adult' | 'child' | 'infant')
          )
        )
      );
    }
  }, [passengerSlots.length, reduxPassengers.length, reduxPassengers, dispatch]);

  // Hydrate contact/postal from Redux when available
  useEffect(() => {
    if (reduxContact.email || reduxContact.country_code || reduxContact.phone) {
      setContactEmail(reduxContact.email);
      setContactPhoneCountryCode(reduxContact.country_code);
      setContactPhone(reduxContact.phone);
    }
    if (reduxPostalCode != null && reduxPostalCode !== '') {
      setContactPostal(reduxPostalCode);
    }
  }, []);

  const updatePassenger = (slotIndex: number, field: keyof PassengerFormData, value: string) => {
    setPassengers((prev) => {
      const next = [...prev];
      if (!next[slotIndex]) next[slotIndex] = { ...initialPassenger };
      next[slotIndex] = { ...next[slotIndex], [field]: value };
      return next;
    });
    dispatch(updatePassengerInRedux({ index: slotIndex, details: { [field]: value } }));
  };

  const handleContinue = async () => {
    setTouched({ _all: true });

    // Sync contact to Redux before navigating
    dispatch(
      setContact({
        email: contactEmail.trim(),
        country_code: contactPhoneCountryCode.trim(),
        phone: contactPhone.trim(),
      })
    );
    dispatch(setPostalCode(contactPostal.trim() || null));

    // Age validation is intentionally checked first (before required fields). This surfaces
    // business-rule violations (wrong passenger type for DOB) before generic field errors.
    for (let i = 0; i < passengerSlots.length; i++) {
      const slot = passengerSlots[i]!;
      const p = passengers[i];
      const err =
        slot.type === 'Adult'
          ? validateAdultAge(p?.dateOfBirth)
          : slot.type === 'Child'
            ? validateChildAge(p?.dateOfBirth)
            : validateInfantAge(p?.dateOfBirth);
      if (err) {
        showErrorToast(`${slot.type} ${slot.typeIndex}: ${err}`);
        return;
      }
    }

    // Validate required fields
    const hasContact = contactEmail.trim() && contactPhoneCountryCode.trim() && contactPhone.trim();
    const allPassengersValid = passengers.every(
      (p) => p.title && p.firstName?.trim() && p.lastName?.trim() && p.dateOfBirth && p.nationality
    );
    const requiredFields: string[] =
      (effectiveRevalidate?.validatedFareItineraries?.[0] as { requiredBookingFields?: string[] })
        ?.requiredBookingFields ?? (effectiveRevalidate as { requiredFields?: string[] })?.requiredFields ?? [];
    const needsPassport = requiredFields.some((f: string) => f?.toLowerCase() === 'passport');
    const passportValid =
      !needsPassport ||
      passengers.every((p, i) => {
        if (savedPassengerIds[i]) return true; // Backend resolves
        return hasValidPassportData(p);
      });
    if (!hasContact || !allPassengersValid || !passportValid) return;

    // CRITICAL: Sync passengers to Redux before navigating
    // This ensures ReviewBookingPage has the passenger data
    dispatch(
      setPassengersInRedux(
        passengers.map((p, i) =>
          toDetails(p, passengerSlots[i]!.type.toLowerCase() as 'adult' | 'child' | 'infant')
        )
      )
    );

    // Save passengers for future bookings when checkbox is checked
    if (saveForFuture) {
      const mainEmail = contactEmail.trim();
      const mainPhone =
        contactPhoneCountryCode.trim() && contactPhone.trim()
          ? `+${contactPhoneCountryCode.trim()}${contactPhone.trim()}`
          : null;
      for (let i = 0; i < passengers.length; i++) {
        const p = passengers[i]!;
        const slot = passengerSlots[i]!;
        const isMain = slot.isMain;
        try {
          await createPassenger({
            title: p.title,
            firstName: p.firstName.trim(),
            lastName: p.lastName.trim(),
            dateOfBirth: p.dateOfBirth,
            nationality: p.nationality,
            email: isMain ? mainEmail || null : null,
            phone: isMain ? mainPhone : null,
            passportNumber: p.passportNumber || null,
            passportExpiry: p.passportExpiry || null,
            passportCountry: p.passportCountry || null,
            type: slot.type.toLowerCase() as 'adult' | 'child' | 'infant',
          }).unwrap();
        } catch {
          // Non-blocking: continue to review even if save fails
        }
      }
    }

    trackEvent('flight_passenger_details_completed', {
      passenger_count: passengers.length,
    });

    const rr = effectiveRevalidate;
    if (!searchSessionId || !rr?.fareSourceCode) return;

    setSubmitting(true);
    try {
      const fareRulesResult = await getFareRules({
        sessionId: searchSessionId,
        fareSourceCode: rr.fareSourceCode,
      }).unwrap();
      dispatch(setFareRules(fareRulesResult));
      navigate('/flights/review-booking', {
        state: {
          revalidateResponse: rr,
          selectedFlightData,
          searchSessionId,
        },
      });
    } catch (err) {
      console.warn('Failed to load fare rules:', err);
      // Still navigate so review page can show and optionally retry fare rules
      navigate('/flights/review-booking', {
        state: {
          revalidateResponse: rr,
          selectedFlightData,
          searchSessionId,
        },
      });
    } finally {
      setSubmitting(false);
    }
  };

  // Quick fill (test data) – only in non-production; syncs to Redux so review/booking have the data
  const showQuickFill = import.meta.env.VITE_ENV !== 'production';
  const handleQuickFill = () => {
    const currentYear = new Date().getFullYear();
    const testData: PassengerFormData[] = passengerSlots.map((slot, i) => {
      let dateOfBirth: string;
      if (slot.type === 'Adult') {
        dateOfBirth = `${currentYear - 25}-01-15`;
      } else if (slot.type === 'Child') {
        dateOfBirth = `${currentYear - 5}-06-01`; // ~5 years (Child 2-11)
      } else {
        dateOfBirth = `${currentYear - 1}-06-01`; // ~1 year (Infant < 2)
      }
      return {
        title: slot.type === 'Adult' ? (i === 0 ? 'Mr' : 'Mrs') : 'Master',
        firstName: `Test${slot.typeIndex}`,
        lastName: 'Passenger',
        dateOfBirth,
        nationality: 'US',
        passportNumber: `AB${12345678 + slot.index}`,
        passportExpiry: `${currentYear + 5}-12-31`,
        passportCountry: 'US',
      };
    });
    setPassengers(testData);
    dispatch(
      setPassengersInRedux(
        testData.map((p, i) =>
          toDetails(p, passengerSlots[i]!.type.toLowerCase() as 'adult' | 'child' | 'infant')
        )
      )
    );
    if (!contactEmail) setContactEmail('test@example.com');
    if (!contactPhoneCountryCode) setContactPhoneCountryCode('1');
    if (!contactPhone) setContactPhone('5551234567');
  };

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

  if (!effectiveRevalidate || !selectedFlightData) {
    return (
      <Container size="lg" py="xl">
        <Loader />
      </Container>
    );
  }

  return (
    <Container size="md" py="xl">
      <Title order={2} fw={700}>
        Passenger details
      </Title>
      <Text c="dimmed" mb="md">
        Enter details for each traveller as they appear on travel documents.
      </Text>

      {showQuickFill && (
        <Box
          mb="md"
          p="sm"
          style={{
            borderRadius: 8,
            backgroundColor: 'var(--mantine-color-navy-1)',
            border: '1px solid var(--mantine-color-navy-7)',
          }}
        >
          <Text size="sm" fw={600} mb={4}>
            Quick fill (test data)
          </Text>
          <Button
            variant="outline"
            size="xs"
            onClick={handleQuickFill}
          >
            Auto-fill all passengers
          </Button>
        </Box>
      )}

      {/* Passenger forms */}
      {passengerSlots.map((slot, slotIndex) => (
        <Card key={slot.index} mb="md" p="lg" radius="md" withBorder>
          <Group justify="space-between" align="center" gap="md" mb="sm" wrap="wrap">
            <Group align="center" gap="xs">
              <User size={20} color="var(--mantine-color-navy-7)" />
              <Title order={6} fw={600}>
                {slot.type} {slot.typeIndex}
                {slot.isMain ? ' (Main passenger)' : ''}
              </Title>
            </Group>
            {savedPassengers.length > 0 && (
              <Select
                label="Use saved passenger"
                value={savedPassengerIds[slotIndex] ?? ''}
                onChange={(id) => {
                  dispatch(
                    setSavedPassengerId({
                      index: slotIndex,
                      id: id ? id : null,
                    })
                  );
                  const saved = savedPassengers.find((s) => s.id === id);
                  const formData = saved
                    ? (() => {
                        const slotType = slot.type.toLowerCase();
                        const matchesType =
                          (saved.type ?? 'adult') === slotType ||
                          (slotType === 'adult' && !saved.type);
                        return matchesType ? storedPassengerToFormData(saved) : null;
                      })()
                    : null;
                  const data = formData ?? { ...initialPassenger };
                  const newPassengers = [...passengers];
                  while (newPassengers.length < passengerSlots.length) {
                    newPassengers.push({ ...initialPassenger });
                  }
                  if (!newPassengers[slotIndex]) newPassengers[slotIndex] = { ...initialPassenger };
                  newPassengers[slotIndex] = { ...data };
                  setPassengers(newPassengers);
                  dispatch(
                    setPassengersInRedux(
                      newPassengers.map((p, i) =>
                        toDetails(p, passengerSlots[i]!.type.toLowerCase() as 'adult' | 'child' | 'infant')
                      )
                    )
                  );
                }}
                data={[
                  { value: '', label: 'Enter manually' },
                  ...savedPassengers
                    .filter((s) => {
                      const t = (s.type ?? 'adult').toLowerCase();
                      const slotType = slot.type.toLowerCase();
                      return t === slotType;
                    })
                    .map((s) => ({ value: s.id, label: formatSavedPassengerLabel(s) })),
                ]}
                size="sm"
                style={{ minWidth: 200 }}
                allowDeselect={false}
              />
            )}
          </Group>
          <Divider mb="sm" />

          <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="sm">
            <Select
              label="Title"
              value={passengers[slotIndex]?.title ?? ''}
              onChange={(value) => updatePassenger(slotIndex, 'title', value ?? '')}
              data={(slot.type === 'Adult' ? ADULT_TITLES : MINOR_TITLES).map((opt) => ({
                value: opt.value,
                label: opt.label,
              }))}
              size="sm"
              required
              error={touched['_all'] && !(passengers[slotIndex]?.title ?? '')}
              allowDeselect={false}
            />
            <TextInput
              label="First name"
              value={passengers[slotIndex]?.firstName ?? ''}
              onChange={(e) => updatePassenger(slotIndex, 'firstName', e.currentTarget.value)}
              size="sm"
              required
              error={touched['_all'] && !(passengers[slotIndex]?.firstName ?? '').trim()}
            />
            <TextInput
              label="Last name"
              value={passengers[slotIndex]?.lastName ?? ''}
              onChange={(e) => updatePassenger(slotIndex, 'lastName', e.currentTarget.value)}
              size="sm"
              required
              error={touched['_all'] && !(passengers[slotIndex]?.lastName ?? '').trim()}
            />
          </SimpleGrid>

          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="sm" mt="sm">
            <TextInput
              label="Date of birth"
              type="date"
              value={passengers[slotIndex]?.dateOfBirth ?? ''}
              onChange={(e) => updatePassenger(slotIndex, 'dateOfBirth', e.currentTarget.value)}
              size="sm"
              required
              error={touched['_all'] && !(passengers[slotIndex]?.dateOfBirth ?? '')}
            />
            <CountrySelect
              label="Nationality"
              value={passengers[slotIndex]?.nationality ?? ''}
              onChange={(val) => updatePassenger(slotIndex, 'nationality', val)}
              fullWidth
              size="small"
              required
              showPhoneCode={false}
              error={touched['_all'] && !(passengers[slotIndex]?.nationality ?? '').trim()}
            />
          </SimpleGrid>

          {/* Passport */}
          <Box
            mt="sm"
            p="sm"
            style={{
              borderRadius: 8,
              backgroundColor: 'var(--mantine-color-gray-0)',
              border: '1px solid var(--mantine-color-gray-2)',
            }}
          >
            <Group align="center" gap="xs" mb="sm">
              <IdCard size={18} color="var(--mantine-color-navy-7)" />
              <Text fw={600} size="sm">
                Passport information
              </Text>
            </Group>
            <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="sm">
              <TextInput
                label="Passport number"
                value={passengers[slotIndex]?.passportNumber ?? ''}
                onChange={(e) => updatePassenger(slotIndex, 'passportNumber', e.currentTarget.value)}
                size="sm"
              />
              <TextInput
                label="Expiry date"
                type="date"
                value={passengers[slotIndex]?.passportExpiry ?? ''}
                onChange={(e) => updatePassenger(slotIndex, 'passportExpiry', e.currentTarget.value)}
                size="sm"
              />
              <CountrySelect
                label="Country of issue"
                value={passengers[slotIndex]?.passportCountry ?? ''}
                onChange={(val) => updatePassenger(slotIndex, 'passportCountry', val)}
                fullWidth
                size="small"
                showPhoneCode={false}
              />
            </SimpleGrid>
          </Box>

          {/* Contact (main passenger only) */}
          {slot.isMain && (
            <Box
              mt="sm"
              p="sm"
              style={{
                borderRadius: 8,
                backgroundColor: 'var(--mantine-color-green-1)',
                border: '1px solid var(--mantine-color-green-6)',
              }}
            >
              <Group align="center" gap="xs" mb="sm">
                <Mail size={18} color="var(--mantine-color-green-8)" />
                <Text fw={600} size="sm">
                  Contact information
                </Text>
              </Group>
              <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="sm">
                <TextInput
                  label="Email"
                  type="email"
                  value={contactEmail}
                  onChange={(e) => {
                    const v = e.currentTarget.value;
                    setContactEmail(v);
                    dispatch(setContact({ email: v }));
                  }}
                  size="sm"
                  required
                  error={touched['_all'] && !contactEmail.trim()}
                />
                <Group gap={0} align="flex-start" wrap="nowrap">
                  <CountrySelect
                    variant="phone"
                    label="Code"
                    value={contactPhoneCountryCode}
                    onChange={(val) => {
                      setContactPhoneCountryCode(val);
                      dispatch(setContact({ country_code: val }));
                    }}
                    size="small"
                    required
                    error={touched['_all'] && !contactPhoneCountryCode.trim()}
                  />
                  <TextInput
                    label="Phone"
                    value={contactPhone}
                    onChange={(e) => {
                      const v = e.currentTarget.value.replace(/\D/g, '');
                      setContactPhone(v);
                      dispatch(setContact({ phone: v }));
                    }}
                    inputMode="numeric"
                    style={{ flex: 1 }}
                    size="sm"
                    required
                    error={touched['_all'] && !contactPhone.trim()}
                  />
                </Group>
              </SimpleGrid>
              <TextInput
                label="Postal code"
                value={contactPostal}
                onChange={(e) => {
                  const v = e.currentTarget.value;
                  setContactPostal(v);
                  dispatch(setPostalCode(v || null));
                }}
                size="sm"
                mt="sm"
              />
            </Box>
          )}
        </Card>
      ))}

      {Object.keys(savedPassengerIds).length === 0 && (
        <Checkbox
          checked={saveForFuture}
          onChange={(e) => setSaveForFuture(e.currentTarget.checked)}
          label="Save passenger details for future bookings"
          mt="sm"
        />
      )}

      {/* Actions */}
      <Group justify="space-between" gap="md" mt="xl" wrap="wrap">
        <Button
          variant="outline"
          color="gray"
          onClick={() => navigate(-1)}
          radius="md"
        >
          Back
        </Button>
        <Button
          size="md"
          onClick={handleContinue}
          disabled={submitting}
          radius="md"
          fw={600}
          px="xl"
          leftSection={submitting ? <Loader size="xs" color="white" /> : undefined}
        >
          {submitting ? 'Loading…' : 'Review booking'}
        </Button>
      </Group>
    </Container>
  );
}

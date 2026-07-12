import { useState, useEffect } from 'react';
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Group,
  Loader,
  Select,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  UnstyledButton,
} from '@mantine/core';
import { ArrowLeft, Trash2 } from 'lucide-react';
import { CountrySelect } from '@/components/CountrySelect';
import {
  useGetPassengerQuery,
  useCreatePassengerMutation,
  useUpdatePassengerMutation,
  useDeletePassengerMutation,
} from '@/api/usersApi';
import {
  isMaskedPassportValue,
  isMaskedFrequentFlyerValue,
} from '@/features/flights/utils/passengerStorageUtils';
import type { PassengerCreateRequest } from '@/types/passengers';
import { NAVY, MUTED, LINE } from '../../profileTokens';

const TITLES = [
  { value: 'Mr', label: 'Mr' },
  { value: 'Mrs', label: 'Mrs' },
  { value: 'Ms', label: 'Ms' },
  { value: 'Dr', label: 'Dr' },
  { value: 'Miss', label: 'Miss' },
  { value: 'Master', label: 'Master' },
];

const PASSENGER_TYPES = [
  { value: 'adult', label: 'Adult' },
  { value: 'child', label: 'Child (2–11)' },
  { value: 'infant', label: 'Infant (under 2)' },
];

const initialForm: PassengerCreateRequest = {
  title: 'Mr',
  firstName: '',
  lastName: '',
  dateOfBirth: '',
  nationality: 'US',
  email: null,
  phone: null,
  passportNumber: null,
  passportExpiry: null,
  passportCountry: null,
  frequentFlyerNumber: null,
  type: 'adult',
  isPrimary: false,
};

export interface CompanionFormViewProps {
  passengerId?: string;
  onBack: () => void;
  onSuccess: () => void;
}

export function CompanionFormView({ passengerId, onBack, onSuccess }: CompanionFormViewProps) {
  const isEdit = !!passengerId;

  const { data: existing } = useGetPassengerQuery(
    { passengerId: passengerId! },
    { skip: !passengerId }
  );

  const [create, { isLoading: creating, error: createError }] = useCreatePassengerMutation();
  const [update, { isLoading: updating, error: updateError }] = useUpdatePassengerMutation();
  const [remove, { isLoading: deleting, error: deleteError }] = useDeletePassengerMutation();

  const isLoading = creating || updating || deleting;
  const apiError = createError || updateError || deleteError;

  const [form, setForm] = useState<PassengerCreateRequest>({ ...initialForm });
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (existing) {
      setForm({
        title: existing.title ?? 'Mr',
        firstName: existing.firstName,
        lastName: existing.lastName,
        dateOfBirth: existing.dateOfBirth ?? '',
        nationality: existing.nationality ?? 'US',
        email: existing.email ?? null,
        phone: existing.phone ?? null,
        passportNumber: existing.passportNumber ?? null,
        passportExpiry: existing.passportExpiry ?? null,
        passportCountry: existing.passportCountry ?? null,
        frequentFlyerNumber: existing.frequentFlyerNumber ?? null,
        type: (existing.type as 'adult' | 'child' | 'infant') ?? 'adult',
        isPrimary: false,
      });
    }
  }, [existing]);

  const updateField = (k: keyof PassengerCreateRequest, v: string | boolean | null) => {
    setForm((prev) => ({ ...prev, [k]: v ?? null }));
  };

  const handleSubmit = async () => {
    if (
      !form.firstName?.trim() ||
      !form.lastName?.trim() ||
      !form.dateOfBirth?.trim() ||
      !form.nationality?.trim()
    ) {
      setValidationError('Please fill in all required fields.');
      return;
    }
    setValidationError(null);
    try {
      if (isEdit && passengerId) {
        const body: Parameters<typeof update>[0]['body'] = {
          title: form.title,
          firstName: form.firstName,
          lastName: form.lastName,
          dateOfBirth: form.dateOfBirth,
          nationality: form.nationality,
          type: form.type,
          isPrimary: form.isPrimary ?? false,
        };
        if (!isMaskedPassportValue(form.passportNumber, 'number'))
          body.passportNumber = form.passportNumber;
        if (!isMaskedPassportValue(form.passportExpiry, 'expiry'))
          body.passportExpiry = form.passportExpiry;
        if (!isMaskedFrequentFlyerValue(form.frequentFlyerNumber))
          body.frequentFlyerNumber = form.frequentFlyerNumber;
        if (form.passportCountry) body.passportCountry = form.passportCountry;
        await update({ passengerId, body }).unwrap();
      } else {
        await create({
          ...form,
          isPrimary: form.isPrimary ?? false,
        } as PassengerCreateRequest & { isPrimary?: boolean }).unwrap();
      }
      onSuccess();
      onBack();
    } catch {
      // API error is displayed via apiError state
    }
  };

  const handleDelete = async () => {
    if (!passengerId) return;
    try {
      await remove(passengerId).unwrap();
      onSuccess();
      onBack();
    } catch {
      // deleteError state is surfaced via apiError above
    }
  };

  return (
    <Stack gap="md">
      {/* Back button */}
      <UnstyledButton
        onClick={onBack}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          color: NAVY,
          fontWeight: 600,
          fontSize: 13,
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          padding: 0,
          opacity: 1,
          transition: 'opacity 120ms',
        }}
      >
        <ArrowLeft size={16} />
        Travel companions
      </UnstyledButton>

      {/* Header row */}
      <Group justify="space-between" align="center">
        <Text style={{ fontSize: 22, fontWeight: 900, color: NAVY }}>
          {isEdit ? 'Edit companion' : 'Add companion'}
        </Text>
        {isEdit && (
          <Button
            onClick={handleDelete}
            disabled={deleting}
            leftSection={<Trash2 size={15} />}
            variant="subtle"
            color="red"
            tt="none"
            fw={600}
            fz={13}
            styles={{ root: { color: '#c62828', '&:hover': { background: '#FFF5F5' } } }}
          >
            {deleting ? <Loader size={16} color="red" /> : 'Remove'}
          </Button>
        )}
      </Group>

      {/* Error banners */}
      {(apiError || validationError) && (
        <Alert color="red" radius="md">
          {validationError ??
            (apiError && typeof apiError === 'object' && 'data' in apiError
              ? String(
                  (apiError as { data?: { detail?: string } }).data?.detail ??
                    'Failed to save. Please try again.',
                )
              : 'Failed to save. Please try again.')}
        </Alert>
      )}

      {/* Form card */}
      <Box
        style={{
          background: 'white',
          borderRadius: 14,
          border: `1px solid ${LINE}`,
          padding: 24,
        }}
      >
        <Stack gap="lg">
          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
            <Select
              label="Type"
              data={PASSENGER_TYPES}
              value={form.type ?? 'adult'}
              onChange={(v) => updateField('type', v ?? 'adult')}
              allowDeselect={false}
            />
            <Select
              label="Title"
              data={TITLES}
              value={form.title ?? 'Mr'}
              onChange={(v) => updateField('title', v ?? 'Mr')}
              allowDeselect={false}
            />
          </SimpleGrid>

          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
            <TextInput
              label="First name"
              required
              value={form.firstName}
              onChange={(e) => updateField('firstName', e.currentTarget.value)}
            />
            <TextInput
              label="Last name"
              required
              value={form.lastName}
              onChange={(e) => updateField('lastName', e.currentTarget.value)}
            />
          </SimpleGrid>

          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
            <TextInput
              label="Date of birth"
              type="date"
              required
              value={form.dateOfBirth}
              onChange={(e) => updateField('dateOfBirth', e.currentTarget.value)}
            />
            <CountrySelect
              label="Nationality"
              value={form.nationality}
              onChange={(v) => updateField('nationality', v)}
              fullWidth
              size="small"
              showPhoneCode={false}
            />
          </SimpleGrid>

          <Text style={{ fontSize: 13, fontWeight: 700, color: MUTED, paddingTop: 4 }}>
            Passport details
          </Text>

          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
            <TextInput
              label="Passport number"
              value={form.passportNumber ?? ''}
              onChange={(e) => updateField('passportNumber', e.currentTarget.value || null)}
            />
            <TextInput
              label="Expiry date"
              type="date"
              value={form.passportExpiry ?? ''}
              onChange={(e) => updateField('passportExpiry', e.currentTarget.value || null)}
            />
          </SimpleGrid>

          <CountrySelect
            label="Issuing country"
            value={form.passportCountry ?? ''}
            onChange={(v) => updateField('passportCountry', v || null)}
            fullWidth
            size="small"
            showPhoneCode={false}
          />
        </Stack>

        <Group mt="xl" justify="space-between" align="center">
          <Group gap="sm">
          <Button
            onClick={handleSubmit}
            disabled={isLoading}
            style={{
              background: NAVY,
              color: 'white',
              borderRadius: 999,
              fontWeight: 700,
              paddingLeft: 24,
              paddingRight: 24,
            }}
            styles={{ root: { '&:hover': { background: '#0e1240' } } }}
          >
            {isLoading ? <Loader size={18} color="white" /> : 'Save'}
          </Button>
          <Button
            onClick={onBack}
            variant="outline"
            style={{
              borderRadius: 999,
              borderColor: LINE,
              color: NAVY,
            }}
          >
            Cancel
          </Button>
          </Group>
          <Checkbox
            label="This is me"
            checked={form.isPrimary ?? false}
            onChange={(e) => updateField('isPrimary', e.currentTarget.checked)}
            styles={{ label: { fontWeight: 600, fontSize: 13, color: NAVY } }}
          />
        </Group>
      </Box>
    </Stack>
  );
}

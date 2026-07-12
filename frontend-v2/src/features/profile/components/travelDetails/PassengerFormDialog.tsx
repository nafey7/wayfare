/**
 * Shared passenger add/edit dialog. Used by profileOld/SavedPassengersTab and TravelDetailsSection.
 */
import { useState, useEffect } from 'react';
import {
  Alert,
  Button,
  Checkbox,
  Group,
  Modal,
  Select,
  SimpleGrid,
  Stack,
  TextInput,
} from '@mantine/core';
import { CountrySelect } from '@/components/CountrySelect';
import type { StoredPassenger, PassengerCreateRequest } from '@/types/passengers';

const TITLES = [
  { value: 'Mr', label: 'Mr' },
  { value: 'Mrs', label: 'Mrs' },
  { value: 'Miss', label: 'Miss' },
  { value: 'Master', label: 'Master' },
];

const PASSENGER_TYPES = [
  { value: 'adult', label: 'Adult' },
  { value: 'child', label: 'Child' },
  { value: 'infant', label: 'Infant' },
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

export interface PassengerFormDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: PassengerCreateRequest) => Promise<void>;
  initialData?: StoredPassenger | null;
  isUpdate?: boolean;
}

export function PassengerFormDialog({
  open,
  onClose,
  onSubmit,
  initialData,
  isUpdate = false,
}: PassengerFormDialogProps) {
  const [form, setForm] = useState<PassengerCreateRequest>(() =>
    initialData
      ? {
          title: initialData.title,
          firstName: initialData.firstName,
          lastName: initialData.lastName,
          dateOfBirth: initialData.dateOfBirth,
          nationality: initialData.nationality,
          email: initialData.email ?? null,
          phone: initialData.phone ?? null,
          passportNumber: initialData.passportNumber ?? null,
          passportExpiry: initialData.passportExpiry ?? null,
          passportCountry: initialData.passportCountry ?? null,
          frequentFlyerNumber: initialData.frequentFlyerNumber ?? null,
          type: (initialData.type as 'adult' | 'child' | 'infant') ?? 'adult',
          isPrimary: initialData.isPrimary ?? false,
        }
      : { ...initialForm }
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setForm(
        initialData
          ? {
              title: initialData.title,
              firstName: initialData.firstName,
              lastName: initialData.lastName,
              dateOfBirth: initialData.dateOfBirth,
              nationality: initialData.nationality,
              email: initialData.email ?? null,
              phone: initialData.phone ?? null,
              passportNumber: initialData.passportNumber ?? null,
              passportExpiry: initialData.passportExpiry ?? null,
              passportCountry: initialData.passportCountry ?? null,
              frequentFlyerNumber: initialData.frequentFlyerNumber ?? null,
              type: (initialData.type as 'adult' | 'child' | 'infant') ?? 'adult',
              isPrimary: initialData.isPrimary ?? false,
            }
          : { ...initialForm }
      );
    }
  }, [open, initialData]);

  const update = (k: keyof PassengerCreateRequest, v: string | null) => {
    setForm((prev) => ({ ...prev, [k]: v || null }));
  };

  const handleClose = () => {
    // Reset to initial blank form; `useEffect` on `open` re-populates from `initialData` on next open.
    setForm({ ...initialForm });
    setError(null);
    onClose();
  };

  const handleSubmit = async () => {
    const required = ['title', 'firstName', 'lastName', 'dateOfBirth', 'nationality'] as const;
    for (const k of required) {
      if (!form[k]?.trim()) {
        setError('Please fill in all required fields.');
        return;
      }
    }
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit(form);
      handleClose();
    } catch {
      setError('Failed to save passenger. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      opened={open}
      onClose={handleClose}
      title={isUpdate ? 'Edit passenger' : 'Add passenger'}
      size="md"
      radius="md"
      centered
    >
      <Stack gap="md">
        {error && <Alert color="red">{error}</Alert>}
        <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md">
          <Select
            label="Title"
            data={TITLES}
            value={form.title}
            onChange={(v) => update('title', v ?? 'Mr')}
            allowDeselect={false}
            size="sm"
          />
          <TextInput
            label="First name"
            value={form.firstName}
            onChange={(e) => update('firstName', e.currentTarget.value)}
            size="sm"
            required
          />
          <TextInput
            label="Last name"
            value={form.lastName}
            onChange={(e) => update('lastName', e.currentTarget.value)}
            size="sm"
            required
          />
        </SimpleGrid>
        <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
          <TextInput
            label="Date of birth"
            type="date"
            value={form.dateOfBirth}
            onChange={(e) => update('dateOfBirth', e.currentTarget.value)}
            size="sm"
            required
          />
          <CountrySelect
            label="Nationality"
            value={form.nationality}
            onChange={(v) => update('nationality', v)}
            fullWidth
            size="small"
            showPhoneCode={false}
          />
          <TextInput
            label="Email"
            type="email"
            value={form.email ?? ''}
            onChange={(e) => update('email', e.currentTarget.value || null)}
            size="sm"
          />
          <TextInput
            label="Phone"
            value={form.phone ?? ''}
            onChange={(e) => update('phone', e.currentTarget.value || null)}
            size="sm"
          />
          <TextInput
            label="Passport number"
            value={form.passportNumber ?? ''}
            onChange={(e) => update('passportNumber', e.currentTarget.value || null)}
            size="sm"
          />
          <TextInput
            label="Passport expiry"
            type="date"
            value={form.passportExpiry ?? ''}
            onChange={(e) => update('passportExpiry', e.currentTarget.value || null)}
            size="sm"
          />
          <CountrySelect
            label="Passport country"
            value={form.passportCountry ?? ''}
            onChange={(v) => update('passportCountry', v || null)}
            fullWidth
            size="small"
            showPhoneCode={false}
          />
          <Select
            label="Type"
            data={PASSENGER_TYPES}
            value={form.type ?? 'adult'}
            onChange={(v) => update('type', (v as 'adult' | 'child' | 'infant') ?? 'adult')}
            allowDeselect={false}
            size="sm"
          />
        </SimpleGrid>
        {isUpdate && (
          <Checkbox
            checked={form.isPrimary ?? false}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, isPrimary: e.currentTarget.checked }))
            }
            label="Mark as self"
            color="brand.6"
          />
        )}
        <Group justify="flex-end" gap="xs" mt="md">
          <Button variant="subtle" onClick={handleClose} disabled={submitting} tt="none">
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={submitting} tt="none" fw={600}>
            {submitting ? 'Saving…' : isUpdate ? 'Update' : 'Add'}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

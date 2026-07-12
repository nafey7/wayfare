import type { ReactElement } from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';
import { mantineTheme } from '@/theme';
import type { StoredPassenger } from '@/types/passengers';
import { GuestForm } from './GuestForm';

function renderWithTheme(ui: ReactElement) {
  return render(<MantineProvider theme={mantineTheme} env="test">{ui}</MantineProvider>);
}

const adultSlot = { isChild: false, label: 'Adult 1' };

function minimalPassenger(
  p: Pick<StoredPassenger, 'id' | 'firstName' | 'lastName' | 'title' | 'dateOfBirth' | 'nationality'>,
): StoredPassenger {
  return {
    userId: 'u1',
    isPrimary: false,
    hotelTitle: undefined,
    typeHotel: undefined,
    email: null,
    phone: null,
    passportNumber: null,
    passportExpiry: null,
    passportCountry: null,
    frequentFlyerNumber: null,
    type: 'adult',
    createdAt: '',
    updatedAt: '',
    ...p,
  };
}

describe('GuestForm', () => {
  it('calls onSavedPassengerModeChange with manual when selecting Enter manually', async () => {
    const user = userEvent.setup();
    const onMode = vi.fn();
    const guest = { title: 'Mr' as const, firstName: '', lastName: '', roomNumber: 1, isChild: false };
    const saved = [
      minimalPassenger({
        id: 'sp1',
        title: 'Mr',
        firstName: 'Amy',
        lastName: 'Alpha',
        dateOfBirth: '1990-01-01',
        nationality: 'US',
      }),
    ];
    renderWithTheme(
      <GuestForm
        roomNumber={1}
        globalSlotStartIndex={0}
        savedPassengerByGuestIndex={{}}
        onSavedPassengerModeChange={onMode}
        slots={[adultSlot]}
        guests={[guest]}
        onChange={vi.fn()}
        touched={false}
        savedPassengers={saved}
        onSelectSaved={vi.fn()}
      />,
    );
    await user.click(screen.getByRole('radio', { name: /Enter manually/i }));
    expect(onMode).toHaveBeenCalledWith(0, 'manual');
  });

  it('selects saved passenger and calls onSelectSaved with guest fields', async () => {
    const user = userEvent.setup();
    const onMode = vi.fn();
    const onSelect = vi.fn();
    const saved = [
      minimalPassenger({
        id: 'sp1',
        title: 'Mr',
        firstName: 'Amy',
        lastName: 'Alpha',
        dateOfBirth: '1990-01-01',
        nationality: 'US',
      }),
    ];
    renderWithTheme(
      <GuestForm
        roomNumber={1}
        globalSlotStartIndex={0}
        savedPassengerByGuestIndex={{}}
        onSavedPassengerModeChange={onMode}
        slots={[adultSlot]}
        guests={[{ title: 'Mr', firstName: '', lastName: '', roomNumber: 1, isChild: false }]}
        onChange={vi.fn()}
        touched
        savedPassengers={saved}
        onSelectSaved={onSelect}
      />,
    );
    await user.click(screen.getByRole('radio', { name: /Amy Alpha/i }));
    expect(onMode).toHaveBeenCalledWith(0, 'sp1');
    expect(onSelect).toHaveBeenCalledWith(
      0,
      expect.objectContaining({
        firstName: 'Amy',
        lastName: 'Alpha',
        title: 'Mr',
        dateOfBirth: '1990-01-01',
      }),
    );
  });
});

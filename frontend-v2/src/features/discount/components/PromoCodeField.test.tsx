import type { ReactElement } from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';
import { render, screen, waitFor } from '@testing-library/react';
import { MantineProvider } from '@mantine/core';

import { PromoCodeField } from './PromoCodeField';

const applyVoucher = vi.fn();
const releaseVoucher = vi.fn();
const showErrorToast = vi.fn();

const mockFrontendConfig = {
  chatFeedbackEnabled: false,
  publicChatEnabled: false,
  langgraphFlightsEnabled: false,
  langgraphHotelsEnabled: false,
  environment: 'test',
  voucherReservationTtlMinutes: 15,
};

vi.mock('../hooks/useVoucherRedemption', () => ({
  useVoucherRedemption: () => ({
    applyVoucher,
    releaseVoucher,
    applying: false,
    releasing: false,
    busy: false,
  }),
}));

vi.mock('@/api', () => ({
  useGetFrontendConfigQuery: () => ({ data: mockFrontendConfig }),
}));

vi.mock('@/utils/toast', () => ({
  showErrorToast: (message: string) => showErrorToast(message),
}));

function renderWithTheme(ui: ReactElement) {
  return render(<MantineProvider env="test">{ui}</MantineProvider>);
}

describe('PromoCodeField', () => {
  beforeEach(() => {
    applyVoucher.mockReset();
    releaseVoucher.mockReset();
    showErrorToast.mockReset();
  });

  it('calls applyVoucher on Apply', async () => {
    const user = userEvent.setup();
    applyVoucher.mockResolvedValue({
      ok: true,
      applied: {
        redemptionId: 'rid',
        discountCents: 500,
        code: 'VOYA-ABCD-EFGH',
        reservationExpiresAt: '2026-01-01T00:00:00.000Z',
      },
      newTotalCents: 9500,
    });
    const onApplied = vi.fn();
    const onCleared = vi.fn();

    renderWithTheme(
      <PromoCodeField
        bookingType="flight"
        amountCents={10000}
        currencyCode="USD"
        applied={null}
        onApplied={onApplied}
        onCleared={onCleared}
      />
    );

    await user.type(screen.getByLabelText('Code'), 'VOYA-TEST-CODE');
    await user.click(screen.getByRole('button', { name: 'Apply' }));

    expect(applyVoucher).toHaveBeenCalled();
    expect(onApplied).toHaveBeenCalled();
  });

  it('shows all apply API failures in error toast, not inline', async () => {
    const user = userEvent.setup();
    applyVoucher.mockResolvedValue({ ok: false, error: 'Not found', reservedConflict: false });

    renderWithTheme(
      <PromoCodeField
        bookingType="hotel"
        amountCents={10000}
        currencyCode="USD"
        applied={null}
        onApplied={vi.fn()}
        onCleared={vi.fn()}
      />
    );

    await user.type(screen.getByLabelText('Code'), 'BAD');
    await user.click(screen.getByRole('button', { name: 'Apply' }));

    await waitFor(() => expect(showErrorToast).toHaveBeenCalledWith('Not found'));
    expect(screen.queryByText('Not found')).not.toBeInTheDocument();
  });

  it('reserved conflict also uses error toast only', async () => {
    const user = userEvent.setup();
    const msg =
      'This promo is in use on another booking. Try again in about 15 minutes, or use a different code.';
    applyVoucher.mockResolvedValue({ ok: false, error: msg, reservedConflict: true });

    renderWithTheme(
      <PromoCodeField
        bookingType="flight"
        amountCents={10000}
        currencyCode="USD"
        applied={null}
        onApplied={vi.fn()}
        onCleared={vi.fn()}
      />
    );

    await user.type(screen.getByLabelText('Code'), 'VOYA-BUSY');
    await user.click(screen.getByRole('button', { name: 'Apply' }));

    await waitFor(() => expect(showErrorToast).toHaveBeenCalledWith(msg));
    expect(screen.queryByText(msg)).not.toBeInTheDocument();
  });

  it('calls release and onCleared when Remove', async () => {
    const user = userEvent.setup();
    releaseVoucher.mockResolvedValue({ ok: true });
    const onCleared = vi.fn();

    renderWithTheme(
      <PromoCodeField
        bookingType="flight"
        amountCents={10000}
        currencyCode="USD"
        applied={{
          redemptionId: 'r1',
          discountCents: 100,
          code: 'VOYA-X',
          checkoutVoyaReference: 'VOYA-REFTEST01',
        }}
        onApplied={vi.fn()}
        onCleared={onCleared}
      />
    );

    await user.click(screen.getByRole('button', { name: 'Remove' }));
    expect(releaseVoucher).toHaveBeenCalledWith('r1', 'user_removed');
    expect(onCleared).toHaveBeenCalled();
  });

  it('when emphasized and applied, shows reserved-for-checkout notice', () => {
    renderWithTheme(
      <PromoCodeField
        emphasized
        bookingType="flight"
        amountCents={10000}
        currencyCode="USD"
        applied={{
          redemptionId: 'r1',
          discountCents: 100,
          code: 'VOYA-X',
          checkoutVoyaReference: 'VOYA-REFTEST01',
          reservationExpiresAt: '2030-01-01T12:00:00.000Z',
        }}
        onApplied={vi.fn()}
        onCleared={vi.fn()}
      />
    );

    expect(screen.getByText('Code reserved for this booking')).toBeInTheDocument();
    expect(
      screen.getByText((content) => content.includes('held for this checkout until'))
    ).toBeInTheDocument();
  });
});

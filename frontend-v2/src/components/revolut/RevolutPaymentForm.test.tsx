import type { ReactNode } from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';
import { RevolutPaymentForm } from './RevolutPaymentForm';

const mockSubmit = vi.fn();
const mockValidate = vi.fn();

vi.mock('@revolut/checkout', () => ({
  isRevolutCheckoutError: vi.fn(() => false),
  default: vi.fn(async () => ({
    createCardField: vi.fn(
      async (opts: {
        onStatusChange?: (s: { empty: boolean; invalid: boolean }) => void;
        onSuccess?: () => void;
        onError?: (e: { message?: string }) => void;
      }) => {
        opts.onStatusChange?.({ empty: false, invalid: false });
        return {
          validate: mockValidate,
          submit: mockSubmit,
        };
      }
    ),
  })),
}));

vi.mock('@/utils/devLog', () => ({ devLog: vi.fn() }));

function Wrapper({ children }: { children: ReactNode }) {
  return <MantineProvider env="test">{children}</MantineProvider>;
}

describe('RevolutPaymentForm', () => {
  beforeEach(() => {
    mockSubmit.mockClear();
    mockValidate.mockClear();
  });

  it('runs onBeforeSubmit before card submit when GDS book-before-pay', async () => {
    const user = userEvent.setup();
    const onBeforeSubmit = vi.fn().mockResolvedValue(undefined);
    const onSuccess = vi.fn();
    const onError = vi.fn();

    render(
      <Wrapper>
        <RevolutPaymentForm
          orderToken="tok_1"
          orderId="ord_1"
          customerEmail="payer@example.com"
          amount={10000}
          currency="usd"
          onBeforeSubmit={onBeforeSubmit}
          onSuccess={onSuccess}
          onError={onError}
        />
      </Wrapper>
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /pay now/i })).not.toBeDisabled();
    });

    await user.click(screen.getByRole('button', { name: /pay now/i }));

    await waitFor(() => {
      expect(onBeforeSubmit).toHaveBeenCalledTimes(1);
      expect(mockSubmit).toHaveBeenCalledTimes(1);
    });
    expect(onError).not.toHaveBeenCalled();
    expect(mockSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        name: expect.any(String),
        email: 'payer@example.com',
      }),
    );
  });

  it('does not call Revolut submit when onBeforeSubmit rejects', async () => {
    const user = userEvent.setup();
    const onBeforeSubmit = vi.fn().mockRejectedValue(new Error('book failed'));
    const onError = vi.fn();

    render(
      <Wrapper>
        <RevolutPaymentForm
          orderToken="tok_1"
          orderId="ord_1"
          amount={10000}
          currency="usd"
          onBeforeSubmit={onBeforeSubmit}
          onSuccess={vi.fn()}
          onError={onError}
        />
      </Wrapper>
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /pay now/i })).not.toBeDisabled();
    });

    await user.click(screen.getByRole('button', { name: /pay now/i }));

    await waitFor(() => {
      expect(onBeforeSubmit).toHaveBeenCalled();
      expect(onError).toHaveBeenCalledWith('book failed', undefined);
    });
    expect(mockSubmit).not.toHaveBeenCalled();
  });

  it('does not call Revolut submit when customerEmail is missing', async () => {
    const user = userEvent.setup();
    const onError = vi.fn();

    render(
      <Wrapper>
        <RevolutPaymentForm
          orderToken="tok_1"
          orderId="ord_1"
          amount={10000}
          currency="usd"
          onSuccess={vi.fn()}
          onError={onError}
        />
      </Wrapper>,
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /pay now/i })).not.toBeDisabled();
    });

    await user.click(screen.getByRole('button', { name: /pay now/i }));

    await waitFor(() => {
      expect(onError).toHaveBeenCalled();
    });
    expect(String(onError.mock.calls[0]?.[0])).toContain('contact email');
    expect(mockSubmit).not.toHaveBeenCalled();
  });

  it('passes gdsBookingConflict409 when onBeforeSubmit throws a marked 409 error', async () => {
    const user = userEvent.setup();
    const conflictErr = new Error('supplier out of sync') as Error & { gdsBookingConflict409?: true };
    conflictErr.gdsBookingConflict409 = true;
    const onBeforeSubmit = vi.fn().mockRejectedValue(conflictErr);
    const onError = vi.fn();

    render(
      <Wrapper>
        <RevolutPaymentForm
          orderToken="tok_1"
          orderId="ord_1"
          customerEmail="payer@example.com"
          amount={10000}
          currency="usd"
          onBeforeSubmit={onBeforeSubmit}
          onSuccess={vi.fn()}
          onError={onError}
        />
      </Wrapper>
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /pay now/i })).not.toBeDisabled();
    });

    await user.click(screen.getByRole('button', { name: /pay now/i }));

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith('supplier out of sync', { gdsBookingConflict409: true });
    });
    expect(mockSubmit).not.toHaveBeenCalled();
  });
});

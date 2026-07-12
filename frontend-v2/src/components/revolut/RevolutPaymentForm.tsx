import { useEffect, useRef, useState } from 'react';
import RevolutCheckout from '@revolut/checkout';
import { Button, Loader, Text } from '@mantine/core';

import { formatRevolutPaymentUserMessage } from '@/utils/revolutPaymentErrors';

/** Card field from SDK: submit, validate, and optional destroy */
interface RevolutCardField {
  submit: (options?: { name?: string; email?: string; phone?: string }) => void;
  validate: () => void;
  destroy?: () => void;
}

/** Revolut requires cardholder name to be at least two words. */
function cardholderNameForRevolut(name: string | undefined): string {
  const trimmed = (name ?? '').trim();
  const words = trimmed.split(/\s+/).filter(Boolean);
  return words.length >= 2 ? trimmed : 'Card Holder';
}

export interface RevolutPaymentFormProps {
  /** Public order ID (token) from create-order or existing-order */
  orderToken: string;
  /** Revolut order ID (internal) – passed to onSuccess for backend issue_ticket/book */
  orderId: string;
  mode?: 'prod' | 'sandbox';
  /** Customer name for Revolut submit */
  customerName?: string;
  /** Email for Revolut `submit()` — avoids SDK error `error.email-is-not-specified`. */
  customerEmail?: string;
  /** E.164 or formatted phone for Revolut `submit()` when available */
  customerPhone?: string;
  amount: number; // cents
  currency: string;
  /** Called immediately when user clicks Pay */
  onSubmitStart?: () => void;
  /**
   * If set (e.g. GDS flight booking), runs after card validation and before Revolut `submit()`.
   * Use for booking-first flows. Throw or reject to abort payment (no charge).
   */
  onBeforeSubmit?: () => Promise<void>;
  onSuccess: (orderId: string) => void;
  /** Second arg set when book-before-pay fails with HTTP 409 (non-retryable). */
  onError: (message: string, meta?: { gdsBookingConflict409?: boolean }) => void;
  disabled?: boolean;
  submitLabel?: string;
}

/**
 * Revolut Checkout card field form using @revolut/checkout.
 * Parent creates order via revolutPaymentsApi, passes orderToken + orderId; on success use orderId for issue_ticket/book.
 */
export function RevolutPaymentForm({
  orderToken,
  orderId,
  mode = 'sandbox',
  customerName = '',
  customerEmail = '',
  customerPhone = '',
  amount,
  currency,
  onSubmitStart,
  onBeforeSubmit,
  onSuccess,
  onError,
  disabled = false,
  submitLabel = 'Pay now',
}: RevolutPaymentFormProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cardFieldRef = useRef<RevolutCardField | null>(null);

  // Track if the field is empty or invalid to prevent infinite loading
  const fieldStatusRef = useRef({ empty: true, invalid: false });

  const [isSdkLoaded, setIsSdkLoaded] = useState(false);
  const [submitLoading, setSubmitLoading] = useState(false);

  const onSuccessRef = useRef(onSuccess);
  const onErrorRef = useRef(onError);
  onSuccessRef.current = onSuccess;
  onErrorRef.current = onError;

  const formattedAmount = new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: currency.toUpperCase(),
  }).format(amount / 100);

  useEffect(() => {
    if (!orderToken || !containerRef.current) {
      return;
    }

    let cardFieldInstance: RevolutCardField | null = null;

    async function init() {
      try {
        const checkout = await RevolutCheckout(orderToken, mode);
        if (!checkout?.createCardField) {
          onErrorRef.current('Revolut Checkout failed to load');
          return;
        }

        const cardField = await Promise.resolve(
          checkout.createCardField({
            target: containerRef.current!,
            onSuccess: () => {
              setSubmitLoading(false);
              onSuccessRef.current(orderId);
            },
            onError: (err: unknown) => {
              setSubmitLoading(false);
              const msg = formatRevolutPaymentUserMessage(err, mode);
              onErrorRef.current(msg);
            },
            onStatusChange: (status: { empty: boolean; invalid: boolean }) => {
              // Keep track of the field's validity without causing React re-renders
              fieldStatusRef.current = {
                empty: status.empty,
                invalid: status.invalid,
              };
            },
            onValidation: () => {
              // Do not set isSdkLoaded false here – validation messages (e.g. empty field) would disable the Pay button
            },
            styles: {
              default: { color: '#000', fontSize: '16px' },
              invalid: { borderColor: '#ff6b6b' },
            },
          })
        );

        cardFieldInstance = cardField as RevolutCardField;
        cardFieldRef.current = cardFieldInstance;
        setIsSdkLoaded(true);
      } catch (error: unknown) {
        onErrorRef.current(error instanceof Error ? error.message : 'Failed to load payment form');
      }
    }

    init();

    return () => {
      if (cardFieldInstance?.destroy) {
        cardFieldInstance.destroy();
      }
      cardFieldRef.current = null;
      setIsSdkLoaded(false);
    };
  }, [orderToken, orderId, mode]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!cardFieldRef.current || !isSdkLoaded || disabled || submitLoading) return;

    // 1. Check if the Revolut field is empty or has validation errors
    const { empty, invalid } = fieldStatusRef.current;

    if (empty || invalid) {
      // 2. Highlight the errors visually inside the iframe
      if (typeof cardFieldRef.current.validate === 'function') {
        cardFieldRef.current.validate();
      }
      // 3. Throw the toast error and stop execution so button stays enabled
      onError('Please enter valid card details.');
      return;
    }

    if (onBeforeSubmit) {
      setSubmitLoading(true);
      try {
        await onBeforeSubmit();
      } catch (err) {
        setSubmitLoading(false);
        const message = err instanceof Error ? err.message : 'Booking failed';
        const gdsBookingConflict409 =
          err instanceof Error &&
          (err as Error & { gdsBookingConflict409?: true }).gdsBookingConflict409 === true;
        onError(message, gdsBookingConflict409 ? { gdsBookingConflict409: true } : undefined);
        return;
      }
    }

    const emailTrim = customerEmail?.trim() ?? '';
    if (!emailTrim) {
      onError(
        'Add your contact email on the previous step (or sign in so we can use your account email). Revolut needs it to take payment.',
      );
      return;
    }

    // Only proceed to Revolut capture after optional pre-step (e.g. GDS bookFlight) succeeds
    onSubmitStart?.();
    if (!onBeforeSubmit) {
      setSubmitLoading(true);
    }
    try {
      const phoneTrim = customerPhone?.trim() ?? '';
      cardFieldRef.current.submit({
        name: cardholderNameForRevolut(customerName),
        email: emailTrim,
        ...(phoneTrim ? { phone: phoneTrim } : {}),
      });
    } catch (err) {
      onError(formatRevolutPaymentUserMessage(err, mode));
      setSubmitLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <Text size="sm" c="dimmed" mb="md">
        Amount: {formattedAmount}
      </Text>
      <div
        ref={containerRef}
        style={{ minHeight: 50, marginBottom: 16, width: '100%' }}
      />
      <Button
        type="submit"
        fullWidth
        size="md"
        tt="none"
        fw={600}
        disabled={!isSdkLoaded || disabled || submitLoading}
        style={{ opacity: isSdkLoaded ? 1 : 0.7 }}
      >
        {submitLoading ? <Loader size={24} color="white" /> : submitLabel}
      </Button>
    </form>
  );
}

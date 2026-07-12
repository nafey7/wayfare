/** Maps Revolut Checkout widget errors to toast copy. LCC + flight discount was the main failing flow (generic “something went wrong”). */
import { isRevolutCheckoutError } from '@revolut/checkout';

const ERROR_HINTS: Partial<Record<string, string>> = {
  'error.email-is-not-specified':
    'Payment needs an email address. Go back and add your contact email, then try again.',
  'error.invalid-email':
    'The email for this booking is invalid. Update your contact details and try again.',
  'error.invalid-name':
    'Cardholder name must be a full name (first and last name).',
  'error.payment-gateway':
    'The card processor returned an error. Try again in a moment or use another card.',
  'error.declined': 'Your card was declined. Try a different card or contact your bank.',
  'error.insufficient-funds': 'Insufficient funds on this card.',
  'error.3ds-failed':
    'Bank verification (3D Secure) failed or was cancelled. Try again.',
  'error.expired-card': 'This card has expired. Use a different card.',
  'error.incorrect-cvv-code':
    'The security code (CVV) was not accepted. Check and try again.',
  'error.order-not-found':
    'This payment session is no longer valid. Go back and open payment again.',
  'error.order-already-completed': 'This payment was already completed.',
  'error.order-is-cancelled':
    'This payment session was cancelled. Start checkout again.',
  'error.order-customer-id-is-not-set':
    'Payment setup is incomplete. Refresh the page and try again, or contact support.',
};

/**
 * Turn Revolut Checkout / widget errors into a short message for toasts.
 */
export function formatRevolutPaymentUserMessage(
  err: unknown,
  mode: 'prod' | 'sandbox' = 'sandbox',
): string {
  const asError = err instanceof Error ? err : undefined;
  if (isRevolutCheckoutError(asError)) {
    const hint = ERROR_HINTS[asError.type];
    if (hint) return hint;
    if (asError.message?.trim()) return asError.message.trim();
  }
  if (err instanceof Error && err.message.trim()) {
    return err.message.trim();
  }
  if (typeof err === 'string' && err.trim()) {
    return err.trim();
  }
  return mode === 'sandbox'
    ? 'Payment could not be completed. For sandbox, confirm you are using Revolut test cards; otherwise try again or use another card.'
    : 'Payment could not be completed. Please try again or use another card.';
}

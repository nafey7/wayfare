/**
 * Formatting utilities for prices and other display values
 */

/**
 * Format a price amount with currency symbol
 * @param amount - The numeric amount
 * @param currency - ISO 4217 currency code (default: USD)
 * @param showFraction - Whether to show decimal places (default: false)
 * @returns Formatted price string (e.g., "$499" or "$499.99")
 */
export function formatPrice(
  amount: number | undefined | null,
  currency = 'USD',
  showFraction = false
): string {
  if (!amount) return 'N/A';
  try {
    const formatter = new Intl.NumberFormat('en', {
      style: 'currency',
      currency,
      minimumFractionDigits: showFraction ? 2 : 0,
      maximumFractionDigits: showFraction ? 2 : 0,
      currencyDisplay: 'narrowSymbol',
    });
    return formatter.format(amount);
  } catch {
    return `${currency} ${amount}`;
  }
}

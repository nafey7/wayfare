export const DEFAULT_TRIP_CURRENCY_SYMBOL = '$' as const;
export const DEFAULT_TRIP_CURRENCY_CODE = 'USD' as const;

export function formatTripPrice(amount: number, symbol: string = DEFAULT_TRIP_CURRENCY_SYMBOL): string {
  return `${symbol}${amount.toLocaleString()}`;
}

import { DEFAULT_CURRENCY } from './flightUtils';

/**
 * Narrow shape of `getTripDetails` / email-link `pricing` used to read total fare for payment.
 */
export interface TripDetailsPricingBlock {
  fareTotals?: FareTotalsBlock;
}

interface FareTotalsBlock {
  totalFare?: FareAmountFields;
  validatedFareTotals?: { totalFare?: FareAmountFields };
}

interface FareAmountFields {
  amount?: unknown;
  currency?: string;
}

export interface ParsedTripDetailsFare {
  amount: number;
  currency: string;
}

/**
 * Extract total fare amount and currency from trip-details `pricing` (payment / email-link flows).
 */
export function parseFareAmountFromTripDetails(
  tripDetails: Record<string, unknown>,
): ParsedTripDetailsFare {
  const pricingBlock = tripDetails?.pricing as TripDetailsPricingBlock | undefined;
  const fareTotals = pricingBlock?.fareTotals;
  const totalFareObj =
    fareTotals?.totalFare ??
    fareTotals?.validatedFareTotals?.totalFare ??
    ({} as FareAmountFields);
  const amount = totalFareObj.amount;
  const n = amount != null ? (typeof amount === 'number' ? amount : parseFloat(String(amount))) : 0;
  const currency = (totalFareObj.currency ?? DEFAULT_CURRENCY).toUpperCase();
  return { amount: Number.isFinite(n) ? n : 0, currency };
}

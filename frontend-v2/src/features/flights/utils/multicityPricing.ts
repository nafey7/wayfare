import type { MulticityLegSelection } from '@/store/slices/flightBookingSlice';
import { DEFAULT_FLIGHT_PLATFORM_FEE_PERCENTAGE } from '@/features/flights/constants/platformFee';
import { parseFareFromRevalidateResponse } from './flightUtils';

/** Minimal leg shape for building one trip line (search API legs or form segments). */
export type MulticityTripChainLeg = {
  origin: string;
  destination: string;
  legIndex?: number;
};

/**
 * Single itinerary line for multi-city: e.g. LHR -> JFK -> AMS -> JFK
 * (consecutive duplicate airport codes are omitted).
 */
export function buildMulticityTripChain(legs: MulticityTripChainLeg[]): string {
  if (!legs.length) return '';
  const sorted = [...legs].sort((a, b) => (a.legIndex ?? 0) - (b.legIndex ?? 0));
  const chain: string[] = [];
  for (const leg of sorted) {
    const o = (leg.origin ?? '').trim();
    const d = (leg.destination ?? '').trim();
    if (!chain.length) {
      if (o) chain.push(o);
      if (d && d !== chain[chain.length - 1]) chain.push(d);
    } else {
      const last = chain[chain.length - 1]!;
      if (o && o !== last) chain.push(o);
      if (d && d !== chain[chain.length - 1]) chain.push(d);
    }
  }
  return chain.join(' -> ');
}

/** Synthetic group id for Revolut metadata and booking events (Phase 6). */
export function generateMulticityGroupReference(): string {
  return `VOYA-MC-${crypto.randomUUID()}`;
}

export function getSortedMulticityLegSelections(
  legs: Record<number, MulticityLegSelection>
): MulticityLegSelection[] {
  return Object.keys(legs)
    .map((k) => Number(k))
    .filter((n) => Number.isFinite(n))
    .sort((a, b) => a - b)
    .map((idx) => legs[idx])
    .filter((x): x is MulticityLegSelection => x != null);
}

/** True when at least one leg has a selection — use for flow gates (details → payment). */
export function hasMulticitySelection(
  legs: Record<number, MulticityLegSelection>
): boolean {
  return getSortedMulticityLegSelections(legs).length > 0;
}

/**
 * All legs have a selection (indices 0..expectedLegCount-1).
 * For optional UI only (e.g. “all legs selected”); do not use to block navigation.
 */
export function isMulticitySelectionFull(
  legs: Record<number, MulticityLegSelection>,
  expectedLegCount: number
): boolean {
  if (expectedLegCount < 2) return false;
  for (let i = 0; i < expectedLegCount; i++) {
    if (!legs[i]) return false;
  }
  return true;
}

/** @deprecated Use {@link isMulticitySelectionFull} — same behavior. */
export const isMulticitySelectionComplete = isMulticitySelectionFull;

function normalizeFareCurrency(code: string | undefined): string {
  return (code ?? '').trim().toUpperCase();
}

/**
 * Sum validated totals across legs. When all legs share one ISO currency, `hasMixedCurrencies` is false
 * and `currency` is suitable for a single Revolut charge. If legs disagree, `hasMixedCurrencies` is true
 * (numeric total is not meaningful for one payment — callers should block checkout).
 */
export function aggregateMulticityFare(legs: Record<number, MulticityLegSelection>): {
  totalAmount: number;
  currency: string;
  platformFeePercentage: number;
  hasMixedCurrencies: boolean;
} {
  const sorted = getSortedMulticityLegSelections(legs);
  let total = 0;
  let fallbackRawCurrency = 'USD';
  let platformFeePct = DEFAULT_FLIGHT_PLATFORM_FEE_PERCENTAGE;
  if (sorted.length > 0) {
    const firstPricing = parseFareFromRevalidateResponse(
      sorted[0]!.revalidateResponse
    );
    if (firstPricing.platformFeePercentage != null) {
      platformFeePct = firstPricing.platformFeePercentage;
    }
  }
  let referenceNorm = '';
  let hasMixedCurrencies = false;
  for (const leg of sorted) {
    const p = parseFareFromRevalidateResponse(leg.revalidateResponse);
    total += p.amount;
    if (p.currency?.trim()) {
      fallbackRawCurrency = p.currency.trim();
    }
    const norm = normalizeFareCurrency(p.currency);
    if (norm) {
      if (!referenceNorm) {
        referenceNorm = norm;
      } else if (norm !== referenceNorm) {
        hasMixedCurrencies = true;
      }
    }
  }
  const displayCurrency =
    referenceNorm || normalizeFareCurrency(fallbackRawCurrency) || fallbackRawCurrency;
  return {
    totalAmount: total,
    currency: displayCurrency,
    platformFeePercentage: platformFeePct,
    hasMixedCurrencies,
  };
}

export function isLegLccFromSelection(leg: MulticityLegSelection): boolean {
  const it = leg.revalidateResponse?.validatedFareItineraries?.[0];
  const pricing = it?.updatedPricing ?? it?.pricing;
  return pricing?.fareType === 'WebFare';
}

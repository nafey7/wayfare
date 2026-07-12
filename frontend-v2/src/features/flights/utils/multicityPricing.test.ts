import { describe, it, expect } from 'vitest';
import type { MulticityLegSelection } from '@/store/slices/flightBookingSlice';
import type { MulticityLegSearchResultCamel } from '@/types/flightBackend';
import { DEFAULT_FLIGHT_PLATFORM_FEE_PERCENTAGE } from '@/features/flights/constants/platformFee';
import {
  aggregateMulticityFare,
  buildMulticityTripChain,
  getSortedMulticityLegSelections,
  hasMulticitySelection,
  isMulticitySelectionFull,
  isLegLccFromSelection,
} from './multicityPricing';

function mockLeg(
  legIndex: number,
  totalFare: number,
  currency: string,
  fareType: 'WebFare' | 'Public'
): MulticityLegSelection {
  return {
    legIndex,
    sessionId: `s-${legIndex}`,
    fareSourceCode: `f-${legIndex}`,
    selectedFlightData: {
      id: `${legIndex}::x`,
      aircraftName: 'A',
      flightNumber: '1',
      tags: [],
      passengers: 1,
      passengerCounts: { adults: 1, children: 0, infants: 0 },
      legs: [],
      price: totalFare,
    },
    revalidateResponse: {
      sessionId: `s-${legIndex}`,
      fareSourceCode: `f-${legIndex}`,
      isFareAvailable: true,
      validatedFareItineraries: [
        {
          flightLegs: [],
          updatedPricing: {
            fareType,
            fareTotals: {
              totalFare: { amount: String(totalFare), currency },
              platformFeePercentage: 5,
            },
            validatedFareTotals: {
              totalFare: { amount: String(totalFare), currency },
              platformFeePercentage: 5,
            },
          },
        },
      ],
    },
  };
}

describe('multicityPricing', () => {
  it('buildMulticityTripChain joins legs with deduped consecutive airports', () => {
    const legs: MulticityLegSearchResultCamel[] = [
      {
        legIndex: 0,
        origin: 'LHR',
        destination: 'JFK',
        departureDate: '',
        sessionId: '',
        supplier: '',
        fareItineraries: [],
      },
      {
        legIndex: 1,
        origin: 'JFK',
        destination: 'AMS',
        departureDate: '',
        sessionId: '',
        supplier: '',
        fareItineraries: [],
      },
      {
        legIndex: 2,
        origin: 'AMS',
        destination: 'JFK',
        departureDate: '',
        sessionId: '',
        supplier: '',
        fareItineraries: [],
      },
    ];
    expect(buildMulticityTripChain(legs)).toBe('LHR -> JFK -> AMS -> JFK');
  });

  it('hasMulticitySelection is false when empty and true with any leg', () => {
    expect(hasMulticitySelection({})).toBe(false);
    expect(hasMulticitySelection({ 0: mockLeg(0, 100, 'USD', 'Public') })).toBe(true);
    expect(
      hasMulticitySelection({
        0: mockLeg(0, 100, 'USD', 'Public'),
        1: mockLeg(1, 200, 'USD', 'Public'),
      })
    ).toBe(true);
  });

  it('isMulticitySelectionFull requires all indices 0..n-1', () => {
    expect(isMulticitySelectionFull({ 0: mockLeg(0, 100, 'USD', 'Public') }, 2)).toBe(false);
    expect(
      isMulticitySelectionFull(
        { 0: mockLeg(0, 100, 'USD', 'Public'), 1: mockLeg(1, 200, 'USD', 'Public') },
        2
      )
    ).toBe(true);
  });

  it('getSortedMulticityLegSelections sorts by leg index', () => {
    const legs: Record<number, MulticityLegSelection> = {
      2: mockLeg(2, 1, 'USD', 'Public'),
      0: mockLeg(0, 2, 'USD', 'Public'),
      1: mockLeg(1, 3, 'USD', 'Public'),
    };
    const sorted = getSortedMulticityLegSelections(legs);
    expect(sorted.map((l) => l.legIndex)).toEqual([0, 1, 2]);
  });

  it('aggregateMulticityFare sums leg totals', () => {
    const legs: Record<number, MulticityLegSelection> = {
      0: mockLeg(0, 100, 'EUR', 'Public'),
      1: mockLeg(1, 50, 'EUR', 'WebFare'),
    };
    const agg = aggregateMulticityFare(legs);
    expect(agg.totalAmount).toBe(150);
    expect(agg.currency).toBe('EUR');
    expect(agg.hasMixedCurrencies).toBe(false);
  });

  it('aggregateMulticityFare uses normalized reference currency when legs use mixed casing', () => {
    const legs: Record<number, MulticityLegSelection> = {
      0: mockLeg(0, 100, 'eur', 'Public'),
      1: mockLeg(1, 50, 'EUR', 'Public'),
    };
    const agg = aggregateMulticityFare(legs);
    expect(agg.currency).toBe('EUR');
    expect(agg.hasMixedCurrencies).toBe(false);
  });

  it('aggregateMulticityFare flags mixed currencies', () => {
    const legs: Record<number, MulticityLegSelection> = {
      0: mockLeg(0, 100, 'USD', 'Public'),
      1: mockLeg(1, 50, 'EUR', 'Public'),
    };
    const agg = aggregateMulticityFare(legs);
    expect(agg.hasMixedCurrencies).toBe(true);
  });

  it('aggregateMulticityFare uses first leg platform fee only (not last leg)', () => {
    const leg0 = mockLeg(0, 100, 'USD', 'Public');
    const leg1 = mockLeg(1, 50, 'USD', 'Public');
    const u1 = leg1.revalidateResponse.validatedFareItineraries![0]!.updatedPricing!;
    u1.validatedFareTotals!.platformFeePercentage = 12;
    const agg = aggregateMulticityFare({ 0: leg0, 1: leg1 });
    expect(agg.platformFeePercentage).toBe(5);
  });

  it('aggregateMulticityFare falls back when first leg omits platform fee', () => {
    const leg0 = mockLeg(0, 100, 'USD', 'Public');
    const u0 = leg0.revalidateResponse.validatedFareItineraries![0]!.updatedPricing!;
    delete (u0.validatedFareTotals as { platformFeePercentage?: number }).platformFeePercentage;
    const leg1 = mockLeg(1, 50, 'USD', 'Public');
    const u1 = leg1.revalidateResponse.validatedFareItineraries![0]!.updatedPricing!;
    u1.validatedFareTotals!.platformFeePercentage = 12;
    const agg = aggregateMulticityFare({ 0: leg0, 1: leg1 });
    expect(agg.platformFeePercentage).toBe(DEFAULT_FLIGHT_PLATFORM_FEE_PERCENTAGE);
  });

  it('isLegLccFromSelection detects WebFare', () => {
    const lcc = mockLeg(0, 10, 'USD', 'WebFare');
    const gds = mockLeg(0, 10, 'USD', 'Public');
    expect(isLegLccFromSelection(lcc)).toBe(true);
    expect(isLegLccFromSelection(gds)).toBe(false);
  });
});

import { describe, it, expect, vi, beforeEach } from 'vitest';
import onboardingReducer, {
  clearPersistedOnboarding,
  confirmLocation,
  resetOnboarding,
  setTripDetails,
} from './onboardingSlice';
import { PENDING_ONBOARDING_PREFERENCES_PAYLOAD_KEY } from '@/features/onboarding/utils/pendingOnboardingPreferencesSync';
import type { DetectedLocation, OnboardingState, OnboardingTripDetails } from '@/types/onboarding';

const ONBOARDING_LSO_KEY = 'voya_onboarding';

const initialTripForTest: OnboardingTripDetails = {
  origin: '',
  destination: '',
  departureDate: null,
  returnDate: null,
  passengers: { adults: 1, children: 0, infants: 0 },
  tripType: 'roundTrip',
  budgetMindset: null,
  travelPace: null,
  primaryGoals: [],
  freeText: '',
};

const sampleState: OnboardingState = {
  step: 1,
  detectedLocation: null,
  locationSkipped: false,
  tripDetails: initialTripForTest,
};

const sampleDetectedLocation: DetectedLocation = {
  country: 'United States',
  countryCode: 'US',
  city: 'New York',
  iata: '',
  currency: 'USD',
  currencySymbol: '$',
};

describe('onboardingSlice', () => {
  let store: Record<string, string>;

  beforeEach(() => {
    store = {};
    vi.stubGlobal('localStorage', {
      getItem: vi.fn((k: string) => store[k] ?? null),
      setItem: vi.fn((k: string, v: string) => {
        store[k] = v;
      }),
      removeItem: vi.fn((k: string) => {
        delete store[k];
      }),
    });
  });

  it('setTripDetails merges into trip and persists', () => {
    const s: OnboardingState = { ...sampleState, tripDetails: { ...initialTripForTest } };
    const next = onboardingReducer(
      s,
      setTripDetails({ destination: 'Lisbon' })
    );
    expect(next.tripDetails.destination).toBe('Lisbon');
    expect(localStorage.setItem).toHaveBeenCalled();
    const call = (localStorage.setItem as ReturnType<typeof vi.fn>).mock.calls.at(-1) as
      | [string, string]
      | undefined;
    expect(call?.[0]).toBe(ONBOARDING_LSO_KEY);
    const parsed = JSON.parse(call?.[1] ?? '') as OnboardingState;
    expect(parsed.tripDetails.destination).toBe('Lisbon');
  });

  it('setTripDetails with travel pace upserts pending preferences payload', () => {
    const s: OnboardingState = { ...sampleState, tripDetails: { ...initialTripForTest } };
    onboardingReducer(s, setTripDetails({ travelPace: 'relaxed' }));
    const raw = store[PENDING_ONBOARDING_PREFERENCES_PAYLOAD_KEY];
    expect(raw).toBeTruthy();
    expect(JSON.parse(raw!)).toEqual({
      travelStyle: { travelPace: 'relaxed' },
    });
  });

  it('resetOnboarding returns default shape and overwrites localStorage', () => {
    const s: OnboardingState = {
      ...sampleState,
      step: 3,
      tripDetails: {
        ...initialTripForTest,
        destination: 'Tokyo',
        travelPace: 'packed',
      },
    };
    store[PENDING_ONBOARDING_PREFERENCES_PAYLOAD_KEY] = JSON.stringify({
      travelStyle: { travelPace: 'packed' },
    });
    const next = onboardingReducer(s, resetOnboarding());
    expect(next.step).toBe(1);
    expect(next.tripDetails.destination).toBe('');
    expect(JSON.parse(store[PENDING_ONBOARDING_PREFERENCES_PAYLOAD_KEY]!)).toEqual({
      travelStyle: { travelPace: 'packed' },
    });
  });

  it('confirmLocation stores detection without iata and sets origin to city · country', () => {
    const s: OnboardingState = { ...sampleState, tripDetails: { ...initialTripForTest } };
    const withIata: DetectedLocation = { ...sampleDetectedLocation, iata: 'LHR' };
    const next = onboardingReducer(s, confirmLocation(withIata));
    expect(next.detectedLocation).toEqual({ ...withIata, iata: '' });
    expect(next.tripDetails.origin).toBe('New York · United States');
  });

  it('confirmLocation sets origin to city only when country is missing', () => {
    const s: OnboardingState = { ...sampleState, tripDetails: { ...initialTripForTest } };
    const loc: DetectedLocation = {
      ...sampleDetectedLocation,
      country: '',
      iata: 'NYC',
    };
    const next = onboardingReducer(s, confirmLocation(loc));
    expect(next.tripDetails.origin).toBe('New York');
  });

  it('clearPersistedOnboarding removes the storage key', () => {
    clearPersistedOnboarding();
    expect(localStorage.removeItem).toHaveBeenCalledWith(ONBOARDING_LSO_KEY);
  });
});

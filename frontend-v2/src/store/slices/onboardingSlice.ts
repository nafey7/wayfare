import { createSlice } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';
import type { RootState } from '@/store';
import { upsertPendingOnboardingPreferencesStashFromTrip } from '@/features/onboarding/utils/pendingOnboardingPreferencesSync';
import type {
  DetectedLocation,
  OnboardingState,
  OnboardingStep,
  OnboardingTripDetails,
  PrimaryGoal,
} from '@/types/onboarding';

const ONBOARDING_KEY = 'voya_onboarding';

const initialTripDetails: OnboardingTripDetails = {
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

const defaultState: OnboardingState = {
  step: 1,
  detectedLocation: null,
  locationSkipped: false,
  tripDetails: initialTripDetails,
};

function loadOnboarding(): OnboardingState {
  try {
    const raw = localStorage.getItem(ONBOARDING_KEY);
    if (!raw) return defaultState;
    const parsed = JSON.parse(raw) as Partial<OnboardingState> & {
      tripDetails?: Partial<OnboardingTripDetails>;
    };
    return {
      ...defaultState,
      ...parsed,
      tripDetails: { ...initialTripDetails, ...parsed.tripDetails },
    };
  } catch {
    return defaultState;
  }
}

function saveOnboarding(state: OnboardingState): void {
  try {
    localStorage.setItem(ONBOARDING_KEY, JSON.stringify(state));
  } catch {
    /* best effort */
  }
}

function persistOnboardingState(state: OnboardingState): void {
  saveOnboarding(state);
  upsertPendingOnboardingPreferencesStashFromTrip(state.tripDetails);
}

function getInitialOnboardingState(): OnboardingState {
  const loaded = loadOnboarding();
  upsertPendingOnboardingPreferencesStashFromTrip(loaded.tripDetails);
  return loaded;
}

export function clearPersistedOnboarding(): void {
  try {
    localStorage.removeItem(ONBOARDING_KEY);
  } catch {
    /* best effort */
  }
}

const onboardingSlice = createSlice({
  name: 'onboarding',
  initialState: getInitialOnboardingState(),
  reducers: {
    setStep(state, action: PayloadAction<OnboardingStep>) {
      state.step = action.payload;
      persistOnboardingState(state);
    },
    setDetectedLocation(
      state,
      action: PayloadAction<DetectedLocation | null>
    ) {
      state.detectedLocation = action.payload;
      state.locationSkipped = false;
      persistOnboardingState(state);
    },
    confirmLocation(state, action: PayloadAction<DetectedLocation>) {
      const loc = action.payload;
      state.detectedLocation = { ...loc, iata: '' };
      state.locationSkipped = false;
      const city = loc.city?.trim() ?? '';
      const country = loc.country?.trim() ?? '';
      state.tripDetails.origin =
        city && country ? `${city} · ${country}` : city;
      persistOnboardingState(state);
    },
    skipLocation(state) {
      state.locationSkipped = true;
      state.tripDetails.origin = '';
      persistOnboardingState(state);
    },
    setTripDetails(
      state,
      action: PayloadAction<Partial<OnboardingTripDetails>>
    ) {
      state.tripDetails = { ...state.tripDetails, ...action.payload };
      persistOnboardingState(state);
    },
    togglePrimaryGoal(state, action: PayloadAction<PrimaryGoal>) {
      const goal = action.payload;
      const current = state.tripDetails.primaryGoals;
      state.tripDetails.primaryGoals = current.includes(goal)
        ? current.filter((g) => g !== goal)
        : [...current, goal];
      persistOnboardingState(state);
    },
    resetOnboarding() {
      saveOnboarding(defaultState);
      return defaultState;
    },
  },
});

export const {
  setStep,
  setDetectedLocation,
  confirmLocation,
  skipLocation,
  setTripDetails,
  togglePrimaryGoal,
  resetOnboarding,
} = onboardingSlice.actions;

export default onboardingSlice.reducer;

export const selectOnboardingStep = (state: RootState): OnboardingStep =>
  state.onboarding.step;

export const selectDetectedLocation = (
  state: RootState
): DetectedLocation | null => state.onboarding.detectedLocation;

export const selectLocationSkipped = (state: RootState): boolean =>
  state.onboarding.locationSkipped;

export const selectOnboardingTripDetails = (
  state: RootState
): OnboardingTripDetails => state.onboarding.tripDetails;

export const selectHasCompletedLocationStep = (state: RootState): boolean =>
  state.onboarding.detectedLocation !== null ||
  state.onboarding.locationSkipped;

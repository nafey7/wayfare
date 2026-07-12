import type { BudgetMindset, Passengers, TripType } from './trip';

export type TravelPace = 'relaxed' | 'balanced' | 'packed' | 'ultraEfficient';

export type PrimaryGoal =
  | 'business'
  | 'culture'
  | 'food'
  | 'nature'
  | 'family'
  | 'luxury'
  | 'hidden'
  | 'nightlife'
  | 'photography';

export type OnboardingStep = 1 | 2 | 3;

export interface DetectedLocation {
  country: string;
  countryCode: string;
  city: string;
  iata: string;
  currency: string;
  currencySymbol: string;
}

export interface OnboardingTripDetails {
  origin: string;
  destination: string;
  departureDate: string | null;
  returnDate: string | null;
  passengers: Passengers;
  tripType: Extract<TripType, 'oneWay' | 'roundTrip'>;
  budgetMindset: BudgetMindset | null;
  travelPace: TravelPace | null;
  primaryGoals: PrimaryGoal[];
  freeText: string;
}

export interface OnboardingState {
  step: OnboardingStep;
  detectedLocation: DetectedLocation | null;
  locationSkipped: boolean;
  tripDetails: OnboardingTripDetails;
}

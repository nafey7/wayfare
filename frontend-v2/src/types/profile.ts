/**
 * Profile aggregate and preferences types.
 * Aligned with backend ProfileAggregateResponse and UserPreferencesResponse.
 * API returns snake_case; frontend uses camelCase (transform at API boundary).
 */

/** Travel style preferences */
export interface TravelStylePreferences {
  travelPace?: string | null;
  budgetMindset?: string | null;
  accommodation?: string | null;
  activityDensity?: string | null;
  primaryGoals: string[];
  gettingAround: string[];
}

/** Flight preferences */
export interface FlightsPreferences {
  seatPreference?: string | null;
  maxStops?: string | null;
  preferredAirlines: string[];
  departureWindow: [string, string];
}

/** Hotel preferences */
export interface HotelsPreferences {
  bedType?: string | null;
  roomType?: string | null;
  amenities: string[];
  hotelStyle: string[];
  locationPreference: string[];
  cancellation: string[];
}

/** Full preferences response */
export interface UserPreferences {
  documentExists: boolean;
  preferenceChips: string[];
  travelStyle: TravelStylePreferences;
  flights: FlightsPreferences;
  hotels: HotelsPreferences;
}

/** User subset for profile page header */
export interface ProfileUser {
  id: string;
  email: string;
  firstName?: string | null;
  lastName?: string | null;
  profileImage?: string | null;
  photoKey?: string | null;
  photoUrls?: { sm: string; md: string; lg: string } | null;
  mobile?: string | null;
  role?: string | null; // kept in sync with backend; admin gate reads selectCurrentUser (auth slice), not this field
}

/** Profile aggregate: user + preferences + passengers */
export interface ProfileAggregate {
  user: ProfileUser;
  preferences: UserPreferences;
  passengers: Array<{
    id: string;
    userId: string;
    isPrimary?: boolean;
    title: string;
    hotelTitle?: string;
    typeHotel?: string;
    firstName: string;
    lastName: string;
    dateOfBirth: string;
    nationality: string;
    email: string | null;
    phone: string | null;
    passportNumber: string | null;
    passportExpiry: string | null;
    passportCountry: string | null;
    frequentFlyerNumber: string | null;
    type: string | null;
    createdAt: string;
    updatedAt: string;
  }>;
}

/** Partial update for preferences (all fields optional) */
export interface PreferencesUpdateRequest {
  preferenceChips?: string[];
  travelStyle?: Partial<TravelStylePreferences>;
  flights?: Partial<FlightsPreferences>;
  hotels?: Partial<HotelsPreferences>;
}

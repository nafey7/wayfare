/**
 * User profile update request
 */
export interface UserUpdateRequest {
  firstName?: string;
  lastName?: string;
  mobile?: string;
  profileImage?: string;
  timezone?: string;
  address?: UserAddress;
  travelStyleDescription?: string;
}

/**
 * User address
 */
export interface UserAddress {
  street: string;
  city: string;
  state?: string;
  postalCode: string;
  country: string;
}

/**
 * User preferences
 */
export interface UserPreferences {
  currency?: string;
  language?: string;
  notifications?: {
    email: boolean;
    push: boolean;
    sms: boolean;
  };
  travelPreferences?: {
    cabinClass?: 'economy' | 'premium_economy' | 'business' | 'first';
    seatPreference?: 'window' | 'aisle' | 'middle';
    mealPreference?: string;
  };
}

/**
 * Public user info (for display)
 */
export interface UserPublic {
  id: string;
  email: string;
  firstName?: string;
  lastName?: string;
}

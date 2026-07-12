/**
 * Passenger storage API types (issue #418).
 * Backend stores passenger/guest details per user with field-level encryption for sensitive PII.
 * API returns snake_case; frontend uses camelCase. Transform at API boundary.
 */

/** Create passenger request (camelCase for API layer to convert to snake_case) */
export interface PassengerCreateRequest {
  title: string;
  firstName: string;
  lastName: string;
  dateOfBirth: string;
  nationality: string;
  email?: string | null;
  phone?: string | null;
  passportNumber?: string | null;
  passportExpiry?: string | null;
  passportCountry?: string | null;
  frequentFlyerNumber?: string | null;
  type?: 'adult' | 'child' | 'infant' | null;
  /** Account owner (self) passenger; one primary per user. */
  isPrimary?: boolean;
}

/** Update passenger request (partial, camelCase) */
export interface PassengerUpdateRequest {
  title?: string | null;
  firstName?: string | null;
  lastName?: string | null;
  dateOfBirth?: string | null;
  nationality?: string | null;
  email?: string | null;
  phone?: string | null;
  passportNumber?: string | null;
  passportExpiry?: string | null;
  passportCountry?: string | null;
  frequentFlyerNumber?: string | null;
  type?: 'adult' | 'child' | 'infant' | null;
  /** Account owner (self) passenger; one primary per user. */
  isPrimary?: boolean;
}

/** Stored passenger response (sensitive fields masked: ****4589, 2028-**-**) */
export interface StoredPassenger {
  id: string;
  userId: string;
  /** Account owner (self) passenger; one primary per user. */
  isPrimary?: boolean;
  title: string;
  /** Server-derived for hotel context (child slot: Master/Miss). Use for child slots. */
  hotelTitle?: string;
  /** Server-derived for hotel context. 18+ = adult, 0–17 = child. Use for hotel guest form filtering. */
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
}

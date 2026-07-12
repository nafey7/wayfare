import type { PassengerDetails, BookingContact } from '@/store/slices/flightBookingSlice';
import { hasValidPassportData } from './passengerStorageUtils';

/**
 * Revalidation response shape (camelCase; from API transformResponse or Redux)
 */
export interface RevalidateResponseForBooking {
  validatedFareItineraries?: unknown[];
  returnFareSourceCode?: string | null;
  requiredFields?: string[];
}

export interface BuildBookingRequestParams {
  sessionId: string;
  fareSourceCode: string;
  passengers: PassengerDetails[];
  contact: BookingContact;
  paymentId: string | null;
  revalidateResponse: RevalidateResponseForBooking | null;
  /** Slot index → saved passenger id; backend fetches travel_documents from DB */
  savedPassengerIds?: Record<number, string>;
  /** Optional. When provided, postal_code is sent as { code, country }; otherwise null. */
  postalCode?: string | null;
  /**
   * Billing country (ISO code, e.g. 'NL'). Used for postal_code.country when postalCode is set.
   * Derive from user profile or primary passenger nationality; default 'NL' when not provided.
   */
  billingCountry?: string | null;
  /** When true, fare_type defaults to 'WebFare' when not in revalidation. */
  isLCC?: boolean;
  /** When set, backend links booking_events to this saved itinerary after validation. */
  savedItineraryId?: string | null;
  /** Multicity: same group id on each leg booking event (backend snake_case). */
  parentVoyaBookingReference?: string | null;
  /** Multistay: itinerary leg index (0-based) for backend ordering of group legs. */
  multistayLegIndex?: number;
  /**
   * VOYA ref for GDS Pay Now flow (from create-order).
   * Passed as clientReference to FlightLogic create_booking.
   */
  voyaBookingReference?: string | null;
  voucherRedemptionId?: string | null;
}

/**
 * Build flight booking request payload in camelCase for frontend/API layer.
 * API layer (flightsApi bookFlight) converts to snake_case when sending.
 * Shared by PaymentPage (LCC book-after-pay and GDS book-before-pay).
 */
export function buildBookingRequest(params: BuildBookingRequestParams): Record<string, unknown> {
  const {
    sessionId,
    fareSourceCode,
    passengers,
    contact,
    paymentId,
    revalidateResponse,
    savedPassengerIds = {},
    postalCode,
    billingCountry,
    isLCC = false,
    savedItineraryId,
    parentVoyaBookingReference,
    multistayLegIndex,
    voyaBookingReference,
    voucherRedemptionId,
  } = params;

  const adults: Array<Record<string, unknown>> = [];
  const children: Array<Record<string, unknown>> = [];
  const infants: Array<Record<string, unknown>> = [];

  passengers.forEach((p, i) => {
    const hasSavedRef = !!savedPassengerIds[i];
    const passengerData: Record<string, unknown> = {
      personalInfo: {
        name: {
          title: p.title,
          firstName: p.firstName,
          lastName: p.lastName,
        },
        dateOfBirth: p.dateOfBirth,
        nationality: p.nationality,
      },
    };
    if (hasSavedRef) {
      passengerData.savedPassengerId = savedPassengerIds[i];
      // Omit travelDocuments; backend fetches from DB
    } else {
      passengerData.travelDocuments = hasValidPassportData(p)
        ? {
            passportNumber: p.passportNumber,
            passportExpiry: p.passportExpiry,
            passportCountry: p.passportCountry,
          }
        : null;
    }

    if (p.type === 'adult') {
      adults.push(passengerData);
    } else if (p.type === 'child') {
      children.push(passengerData);
    } else if (p.type === 'infant') {
      infants.push(passengerData);
    }
  });

  const passengerGroups: Record<string, unknown> = {};
  if (adults.length > 0) passengerGroups.adults = adults;
  if (children.length > 0) passengerGroups.children = children;
  if (infants.length > 0) passengerGroups.infants = infants;

  const itinerary = revalidateResponse?.validatedFareItineraries?.[0] as Record<string, unknown> | undefined;
  const pricing = itinerary?.updatedPricing ?? itinerary?.pricing;
  const fareType =
    (pricing as { fareType?: string } | undefined)?.fareType ?? (isLCC ? 'WebFare' : 'Public');
  const requiresPassport = (itinerary as { requiresPassport?: boolean })?.requiresPassport ?? false;
  const requiredFields =
    (itinerary as { requiredBookingFields?: string[] })?.requiredBookingFields ??
    revalidateResponse?.requiredFields ??
    [];

  const phoneNumber = contact.phone ? contact.phone.replace(/\s+/g, '') : '';
  const contactPhone =
    phoneNumber && contact.country_code
      ? `+${contact.country_code}${phoneNumber}`
      : phoneNumber || null;

  const bookingRequest: Record<string, unknown> = {
    sessionId,
    fareSourceCode,
    requiresPassport,
    fareType,
    paymentId,
    clientReference: voyaBookingReference ?? null,
    contactInformation: {
      email: contact.email,
      phone: contactPhone,
    },
    bookingNotes: null,
    passengerGroups,
    requiredFields,
    cancellationPolicyText: null,
    postalCode:
      postalCode && postalCode.trim()
        ? { code: postalCode.trim(), country: (billingCountry && billingCountry.trim()) || 'NL' }
        : null,
  };

  const returnFareCode = revalidateResponse?.returnFareSourceCode;
  if (returnFareCode) {
    bookingRequest.inboundFareSourceCode = returnFareCode;
  }

  if (savedItineraryId && String(savedItineraryId).trim()) {
    bookingRequest.savedItineraryId = String(savedItineraryId).trim();
  }
  if (parentVoyaBookingReference?.trim()) {
    bookingRequest.parentVoyaBookingReference = parentVoyaBookingReference.trim();
  }
  if (
    typeof multistayLegIndex === 'number' &&
    Number.isFinite(multistayLegIndex) &&
    multistayLegIndex >= 0
  ) {
    bookingRequest.multistayLegIndex = multistayLegIndex;
  }

  if (voucherRedemptionId && String(voucherRedemptionId).trim()) {
    bookingRequest.voucherRedemptionId = String(voucherRedemptionId).trim();
  }

  return bookingRequest;
}

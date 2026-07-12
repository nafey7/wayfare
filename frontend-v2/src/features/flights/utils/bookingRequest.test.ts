import { describe, it, expect } from 'vitest';
import { buildBookingRequest } from './bookingRequest';
import type { PassengerDetails, BookingContact } from '@/store/slices/flightBookingSlice';

const basePassengers: PassengerDetails[] = [
  {
    type: 'adult',
    title: 'Mr',
    firstName: 'John',
    lastName: 'Doe',
    dateOfBirth: '1990-01-15',
    nationality: 'US',
    passportNumber: 'P1234567',
    passportExpiry: '2030-12-31',
    passportCountry: 'US',
  },
];

const baseContact: BookingContact = {
  email: 'john@example.com',
  country_code: '1',
  phone: '5551234567',
};

const baseRevalidate = {
  validatedFareItineraries: [
    {
      updatedPricing: { fareType: 'Public' as const },
      requiresPassport: true,
      requiredBookingFields: [],
    },
  ],
  returnFareSourceCode: null as string | null,
};

describe('buildBookingRequest', () => {
  it('produces camelCase payload with sessionId and fareSourceCode', () => {
    const result = buildBookingRequest({
      sessionId: 'sess-123',
      fareSourceCode: 'FSC-456',
      passengers: basePassengers,
      contact: baseContact,
      paymentId: null,
      revalidateResponse: baseRevalidate,
    });
    expect(result.sessionId).toBe('sess-123');
    expect(result.fareSourceCode).toBe('FSC-456');
    expect(result.parentVoyaBookingReference).toBeUndefined();
    expect(result.contactInformation).toEqual({
      email: 'john@example.com',
      phone: '+15551234567',
    });
  });

  it('includes parentVoyaBookingReference when provided', () => {
    const result = buildBookingRequest({
      sessionId: 's',
      fareSourceCode: 'f',
      passengers: basePassengers,
      contact: baseContact,
      paymentId: null,
      revalidateResponse: baseRevalidate,
      parentVoyaBookingReference: 'VOYA-MC-test',
    });
    expect(result.parentVoyaBookingReference).toBe('VOYA-MC-test');
  });

  it('includes multistayLegIndex when parent and valid index are provided', () => {
    const result = buildBookingRequest({
      sessionId: 's',
      fareSourceCode: 'f',
      passengers: basePassengers,
      contact: baseContact,
      paymentId: null,
      revalidateResponse: baseRevalidate,
      parentVoyaBookingReference: 'VOYA-MC-test',
      multistayLegIndex: 2,
    });
    expect(result.multistayLegIndex).toBe(2);
  });

  it('includes passengerGroups.adults with personalInfo and travelDocuments when passport present', () => {
    const result = buildBookingRequest({
      sessionId: 's',
      fareSourceCode: 'f',
      passengers: basePassengers,
      contact: baseContact,
      paymentId: null,
      revalidateResponse: baseRevalidate,
    });
    const groups = result.passengerGroups as { adults: unknown[] };
    expect(groups.adults).toHaveLength(1);
    const first = groups.adults[0] as Record<string, unknown>;
    expect(first.personalInfo).toEqual({
      name: { title: 'Mr', firstName: 'John', lastName: 'Doe' },
      dateOfBirth: '1990-01-15',
      nationality: 'US',
    });
    expect(first.travelDocuments).toEqual({
      passportNumber: 'P1234567',
      passportExpiry: '2030-12-31',
      passportCountry: 'US',
    });
  });

  it('omits travelDocuments when passport fields missing', () => {
    const noPassport: PassengerDetails[] = [
      {
        type: 'adult',
        title: 'Mrs',
        firstName: 'Jane',
        lastName: 'Doe',
        dateOfBirth: '1992-05-20',
        nationality: 'GB',
      },
    ];
    const result = buildBookingRequest({
      sessionId: 's',
      fareSourceCode: 'f',
      passengers: noPassport,
      contact: baseContact,
      paymentId: null,
      revalidateResponse: baseRevalidate,
    });
    const groups = result.passengerGroups as { adults: unknown[] };
    expect((groups.adults[0] as Record<string, unknown>).travelDocuments).toBeNull();
  });

  it('splits adults, children, infants into passengerGroups', () => {
    const passengers: PassengerDetails[] = [
      { ...basePassengers[0]!, type: 'adult' },
      {
        type: 'child',
        title: 'Master',
        firstName: 'Jim',
        lastName: 'Doe',
        dateOfBirth: '2015-06-01',
        nationality: 'US',
      },
    ];
    const result = buildBookingRequest({
      sessionId: 's',
      fareSourceCode: 'f',
      passengers,
      contact: baseContact,
      paymentId: null,
      revalidateResponse: baseRevalidate,
    });
    const groups = result.passengerGroups as { adults: unknown[]; children?: unknown[] };
    expect(groups.adults).toHaveLength(1);
    expect(groups.children).toHaveLength(1);
  });

  it('sets fareType from revalidation and isLCC fallback', () => {
    const result = buildBookingRequest({
      sessionId: 's',
      fareSourceCode: 'f',
      passengers: basePassengers,
      contact: baseContact,
      paymentId: null,
      revalidateResponse: baseRevalidate,
      isLCC: true,
    });
    expect(result.fareType).toBe('Public'); // from itinerary
  });

  it('uses WebFare when isLCC true and revalidation has no fareType', () => {
    const result = buildBookingRequest({
      sessionId: 's',
      fareSourceCode: 'f',
      passengers: basePassengers,
      contact: baseContact,
      paymentId: null,
      revalidateResponse: { validatedFareItineraries: [{}], returnFareSourceCode: null },
      isLCC: true,
    });
    expect(result.fareType).toBe('WebFare');
  });

  it('includes inboundFareSourceCode when revalidate has returnFareSourceCode', () => {
    const result = buildBookingRequest({
      sessionId: 's',
      fareSourceCode: 'f',
      passengers: basePassengers,
      contact: baseContact,
      paymentId: null,
      revalidateResponse: { ...baseRevalidate, returnFareSourceCode: 'RET-789' },
    });
    expect(result.inboundFareSourceCode).toBe('RET-789');
  });

  it('includes postalCode when provided with billing country', () => {
    const result = buildBookingRequest({
      sessionId: 's',
      fareSourceCode: 'f',
      passengers: basePassengers,
      contact: baseContact,
      paymentId: null,
      revalidateResponse: baseRevalidate,
      postalCode: '1234AB',
      billingCountry: 'NL',
    });
    expect(result.postalCode).toEqual({ code: '1234AB', country: 'NL' });
  });

  it('defaults billing country to NL when postalCode set but billingCountry missing', () => {
    const result = buildBookingRequest({
      sessionId: 's',
      fareSourceCode: 'f',
      passengers: basePassengers,
      contact: baseContact,
      paymentId: null,
      revalidateResponse: baseRevalidate,
      postalCode: '1234AB',
    });
    expect(result.postalCode).toEqual({ code: '1234AB', country: 'NL' });
  });

  it('sets paymentId when provided', () => {
    const result = buildBookingRequest({
      sessionId: 's',
      fareSourceCode: 'f',
      passengers: basePassengers,
      contact: baseContact,
      paymentId: 'pi_xxx',
      revalidateResponse: baseRevalidate,
    });
    expect(result.paymentId).toBe('pi_xxx');
  });

  it('includes savedItineraryId when provided', () => {
    const savedItineraryId = '507f1f77bcf86cd799439022'; // pragma: allowlist secret
    const result = buildBookingRequest({
      sessionId: 's',
      fareSourceCode: 'f',
      passengers: basePassengers,
      contact: baseContact,
      paymentId: null,
      revalidateResponse: baseRevalidate,
      savedItineraryId,
    });
    expect(result.savedItineraryId).toBe(savedItineraryId);
  });

  it('sends savedPassengerId and omits travelDocuments when saved passenger selected', () => {
    const passengers: PassengerDetails[] = [
      { ...basePassengers[0]!, passportNumber: undefined, passportExpiry: undefined, passportCountry: undefined },
    ];
    const result = buildBookingRequest({
      sessionId: 's',
      fareSourceCode: 'f',
      passengers,
      contact: baseContact,
      paymentId: null,
      revalidateResponse: baseRevalidate,
      savedPassengerIds: { 0: 'saved-id-123' },
    });
    const groups = result.passengerGroups as { adults: Record<string, unknown>[] };
    const first = groups.adults[0];
    expect(first).toBeDefined();
    expect(first!.savedPassengerId).toBe('saved-id-123');
    expect(first!.travelDocuments).toBeUndefined();
  });
});

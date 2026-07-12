import { describe, expect, it } from 'vitest';
import type { FlightBookingListItem } from '@/types/flights';
import { formatListAmountMajor, mapFlightMyBookingToRow } from './mapFlightBookingEvent';

describe('mapFlightMyBookingToRow', () => {
  it('maps departure IATA and reference for navigation', () => {
    const item = {
      voyaBookingReference: 'VOYA-ABC123',
      action: 'BOOKED',
      timestamp: '2026-04-01T12:00:00.000Z',
      dateBooked: null,
      amount: 199.5,
      departureAirportIata: 'JFK',
      ticketStatus: 'Confirmed',
    } as FlightBookingListItem;
    const row = mapFlightMyBookingToRow(item);
    expect(row.summaryLine).toContain('JFK');
    expect(row.canNavigate).toBe(true);
    expect(row.reference).toBe('VOYA-ABC123');
    expect(row.amountLabel).toBeTruthy();
  });

  it('uses trip leg summaries for date label and route summary (one-way)', () => {
    const item = {
      voyaBookingReference: 'VOYA-OW',
      action: 'BOOKED',
      timestamp: '2026-01-10T12:00:00.000Z',
      dateBooked: '2026-01-10T12:00:00.000Z',
      amount: null,
      departureAirportIata: 'LHR',
      ticketStatus: null,
      flightLegSummaries: [
        {
          departureDate: '2026-06-01',
          originIata: 'JFK',
          destinationIata: 'LHR',
        },
      ],
    } as FlightBookingListItem;
    const row = mapFlightMyBookingToRow(item);
    expect(row.dateLabel).toMatch(/Jun 1, 2026/);
    expect(row.summaryLine).toBe('Flight · JFK → LHR');
    expect(row.departureIata).toBe('JFK');
  });

  it('formats classic round-trip leg summaries as JFK ⇆ LHR', () => {
    const item = {
      voyaBookingReference: 'VOYA-RT',
      action: 'BOOKED',
      timestamp: '2026-01-10T12:00:00.000Z',
      dateBooked: null,
      amount: null,
      departureAirportIata: 'JFK',
      ticketStatus: null,
      flightTripType: 'round_trip' as const,
      flightLegSummaries: [
        {
          departureDate: '2026-04-06',
          originIata: 'JFK',
          destinationIata: 'LHR',
        },
        {
          departureDate: '2026-04-12',
          originIata: 'LHR',
          destinationIata: 'JFK',
        },
      ],
    } as FlightBookingListItem;
    const row = mapFlightMyBookingToRow(item);
    expect(row.dateLabel).toMatch(/Apr 6, 2026 – Apr 12, 2026/);
    expect(row.summaryLine).toBe('Flight · JFK ⇆ LHR');
    expect(row.primaryRouteLine).toBe('JFK ⇆ LHR');
    expect(row.secondaryRouteLine).toBeNull();
  });

  it('keeps two-line route for open-jaw round trip', () => {
    const item = {
      voyaBookingReference: 'VOYA-RT-OJ',
      action: 'BOOKED',
      timestamp: '2026-01-10T12:00:00.000Z',
      dateBooked: null,
      amount: null,
      departureAirportIata: 'JFK',
      ticketStatus: null,
      flightTripType: 'round_trip' as const,
      flightLegSummaries: [
        {
          departureDate: '2026-04-06',
          originIata: 'JFK',
          destinationIata: 'LHR',
        },
        {
          departureDate: '2026-04-20',
          originIata: 'LHR',
          destinationIata: 'CDG',
        },
      ],
    } as FlightBookingListItem;
    const row = mapFlightMyBookingToRow(item);
    expect(row.summaryLine).toBe('Flight · JFK → LHR · LHR → CDG');
    expect(row.primaryRouteLine).toBe('JFK → LHR');
    expect(row.secondaryRouteLine).toBe('Return · LHR → CDG');
  });

  it('falls back to booked-at date when leg summaries are absent', () => {
    const item = {
      voyaBookingReference: 'VOYA-FB',
      action: 'BOOKED',
      timestamp: '2026-03-15T10:00:00.000Z',
      dateBooked: '2026-03-15T10:00:00.000Z',
      amount: null,
      departureAirportIata: 'SFO',
      ticketStatus: null,
    } as FlightBookingListItem;
    const row = mapFlightMyBookingToRow(item);
    expect(row.dateLabel).toMatch(/Mar 15, 2026/);
  });

  it('disables navigation without reference', () => {
    const item = {
      voyaBookingReference: null,
      action: 'PENDING',
      timestamp: '2026-04-01T12:00:00.000Z',
      dateBooked: null,
      amount: null,
      departureAirportIata: null,
      ticketStatus: null,
    } as unknown as FlightBookingListItem;
    const row = mapFlightMyBookingToRow(item);
    expect(row.canNavigate).toBe(false);
    expect(row.summaryLine).toBe('Flight booking');
  });

  it('prefers persisted route_legs over trip_details leg summaries for route and airline', () => {
    const item = {
      voyaBookingReference: 'VOYA-SNAP',
      action: 'BOOKED',
      timestamp: '2026-04-01T12:00:00.000Z',
      dateBooked: '2026-04-01T12:00:00.000Z',
      amount: null,
      departureAirportIata: 'JFK',
      ticketStatus: null,
      flightTripType: 'one_way' as const,
      primaryMarketingAirlineName: 'British Airways',
      routeLegs: [
        {
          legIndex: 0,
          departureIata: 'JFK',
          arrivalIata: 'LHR',
          segmentCount: 1,
          segments: [{ departureIata: 'JFK', arrivalIata: 'LHR' }],
        },
      ],
    } as FlightBookingListItem;
    const row = mapFlightMyBookingToRow(item);
    expect(row.summaryLine).toBe('Flight · JFK → LHR');
    expect(row.primaryRouteLine).toBe('JFK → LHR');
    expect(row.secondaryRouteLine).toBeNull();
    expect(row.airlineLabel).toBe('British Airways');
    expect(row.departureIata).toBe('JFK');
  });

  it('formats symmetric round-trip route snapshot as JFK ⇆ LHR', () => {
    const item = {
      voyaBookingReference: 'VOYA-RT2',
      action: 'BOOKED',
      timestamp: '2026-04-01T12:00:00.000Z',
      dateBooked: null,
      amount: null,
      departureAirportIata: 'JFK',
      ticketStatus: null,
      flightTripType: 'round_trip' as const,
      routeLegs: [
        {
          legIndex: 0,
          departureIata: 'JFK',
          arrivalIata: 'LHR',
          segmentCount: 1,
          segments: [{ departureIata: 'JFK', arrivalIata: 'LHR' }],
        },
        {
          legIndex: 1,
          departureIata: 'LHR',
          arrivalIata: 'JFK',
          segmentCount: 1,
          segments: [{ departureIata: 'LHR', arrivalIata: 'JFK' }],
        },
      ],
    } as FlightBookingListItem;
    const row = mapFlightMyBookingToRow(item);
    expect(row.primaryRouteLine).toBe('JFK ⇆ LHR');
    expect(row.secondaryRouteLine).toBeNull();
    expect(row.summaryLine).toBe('Flight · JFK ⇆ LHR');
  });
});

describe('formatListAmountMajor', () => {
  it('returns null for null amount', () => {
    expect(formatListAmountMajor(null)).toBeNull();
  });
});

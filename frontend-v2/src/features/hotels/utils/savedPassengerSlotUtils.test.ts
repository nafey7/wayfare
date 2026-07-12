import { describe, expect, it } from 'vitest';
import type { HotelGuestDetails } from '@/types/hotels';
import type { StoredPassenger } from '@/types/passengers';
import {
  applySavedPassengerSelectionWithDedup,
  inferInitialSavedPassengerMap,
  normalizedNameKey,
} from './savedPassengerSlotUtils';

describe('normalizedNameKey', () => {
  it('lowercases and trims', () => {
    expect(normalizedNameKey('  Jane ', ' DOE ')).toBe('jane\0doe');
  });
});

function mockPassenger(overrides: Partial<StoredPassenger> & Pick<StoredPassenger, 'id' | 'firstName' | 'lastName'>): StoredPassenger {
  return {
    userId: 'u1',
    title: 'Mr',
    dateOfBirth: '1990-01-01',
    nationality: 'US',
    email: null,
    phone: null,
    passportNumber: null,
    passportExpiry: null,
    passportCountry: null,
    frequentFlyerNumber: null,
    type: 'adult',
    createdAt: '',
    updatedAt: '',
    ...overrides,
  } as StoredPassenger;
}

describe('inferInitialSavedPassengerMap', () => {
  const adultP = mockPassenger({
    id: 'p1',
    firstName: 'Jane',
    lastName: 'Doe',
  });

  it('returns prev when every slot is filled and nothing is stale', () => {
    const prev = { 0: 'manual' as const };
    const guests: HotelGuestDetails[] = [
      {
        title: 'Mr',
        firstName: '',
        lastName: '',
        roomNumber: 1,
        isChild: false,
      },
    ];
    expect(inferInitialSavedPassengerMap(prev, [adultP], guests, 1)).toBe(prev);
  });

  it('fills gaps from name match and assigns each saved id once', () => {
    const pA = mockPassenger({
      id: 'a',
      firstName: 'Amy',
      lastName: 'Adams',
    });
    const pB = mockPassenger({
      id: 'b',
      firstName: 'Bob',
      lastName: 'Brown',
    });
    const guests: HotelGuestDetails[] = [
      {
        title: 'Mr',
        firstName: 'Amy',
        lastName: 'Adams',
        roomNumber: 1,
        isChild: false,
      },
      {
        title: 'Mr',
        firstName: 'Bob',
        lastName: 'Brown',
        roomNumber: 1,
        isChild: false,
      },
    ];
    const prev = {};
    expect(inferInitialSavedPassengerMap(prev, [pA, pB], guests, 2)).toEqual({
      0: 'a',
      1: 'b',
    });
  });

  it('uses manual for second slot when same passenger id would repeat', () => {
    const guests: HotelGuestDetails[] = [
      {
        title: 'Mr',
        firstName: 'Jane',
        lastName: 'Doe',
        roomNumber: 1,
        isChild: false,
      },
      {
        title: 'Mr',
        firstName: 'Jane',
        lastName: 'Doe',
        roomNumber: 1,
        isChild: false,
      },
    ];
    const prev = {};
    expect(inferInitialSavedPassengerMap(prev, [adultP], guests, 2)).toEqual({
      0: 'p1',
      1: 'manual',
    });
  });
});

describe('applySavedPassengerSelectionWithDedup', () => {
  it('clears the same id from other slots when assigning', () => {
    const prev = { 0: 'a' as const, 1: 'b' as const };
    expect(
      applySavedPassengerSelectionWithDedup(prev, 1, 'a', 2)
    ).toEqual({
      0: 'manual',
      1: 'a',
    });
  });

  it('sets manual without clearing other ids', () => {
    const prev = { 0: 'a' as const, 1: 'b' as const };
    expect(
      applySavedPassengerSelectionWithDedup(prev, 0, 'manual', 2)
    ).toEqual({
      0: 'manual',
      1: 'b',
    });
  });
});

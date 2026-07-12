import { describe, it, expect } from 'vitest';
import { isGuestSlotComplete } from './guestSlotComplete';
import type { HotelGuestDetails } from '@/types/hotels';

const adultSlot = { isChild: false };
const childSlot = { isChild: true };

describe('isGuestSlotComplete', () => {
  it('treats missing guest as complete until touched', () => {
    expect(isGuestSlotComplete(undefined, adultSlot, false)).toBe(true);
    expect(isGuestSlotComplete(undefined, adultSlot, true)).toBe(false);
  });

  it('requires title and trimmed names for adults', () => {
    const ok: HotelGuestDetails = {
      title: 'Mr',
      firstName: 'A',
      lastName: 'B',
      roomNumber: 1,
      isChild: false,
    };
    expect(isGuestSlotComplete(ok, adultSlot, true)).toBe(true);
    expect(isGuestSlotComplete({ ...ok, firstName: '  ' }, adultSlot, true)).toBe(false);
    expect(isGuestSlotComplete({ ...ok, title: '' as HotelGuestDetails['title'] }, adultSlot, true)).toBe(false);
  });

  it('requires age in range for children', () => {
    const base: HotelGuestDetails = {
      title: 'Master',
      firstName: 'C',
      lastName: 'D',
      roomNumber: 1,
      isChild: true,
      age: 5,
    };
    expect(isGuestSlotComplete(base, childSlot, true)).toBe(true);
    expect(isGuestSlotComplete({ ...base, age: undefined }, childSlot, true)).toBe(false);
    expect(isGuestSlotComplete({ ...base, age: 18 }, childSlot, true)).toBe(false);
  });
});

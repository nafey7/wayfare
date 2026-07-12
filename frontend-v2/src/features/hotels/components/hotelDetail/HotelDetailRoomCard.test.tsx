import type { ReactElement } from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MantineProvider } from '@mantine/core';
import { mantineTheme } from '@/theme';
import type { RoomRate } from '@/types/hotels';
import { HotelDetailRoomCard } from './HotelDetailRoomCard';

function renderWithTheme(ui: ReactElement) {
  return render(<MantineProvider theme={mantineTheme} env="test">{ui}</MantineProvider>);
}

function baseRoom(overrides: Partial<RoomRate> = {}): RoomRate {
  return {
    rateBasisId: 'rb-test',
    roomType: 'Superior Double',
    mealPlan: 'Room only',
    totalPrice: 580,
    currency: 'USD',
    pricePerNight: 290,
    images: [],
    maxOccupancy: { adults: 2, children: 0 },
    ...overrides,
  };
}

describe('HotelDetailRoomCard', () => {
  it('shows scarcity copy when few rooms remain', () => {
    renderWithTheme(
      <HotelDetailRoomCard room={baseRoom({ roomsAvailable: 2 })} stayNights={2} showReserveButton={false} />,
    );
    expect(screen.getByText('2 rooms left')).toBeInTheDocument();
  });

  it('does not show scarcity when inventory is ample', () => {
    renderWithTheme(
      <HotelDetailRoomCard room={baseRoom({ roomsAvailable: 10 })} stayNights={2} showReserveButton={false} />,
    );
    expect(screen.queryByText(/rooms left/)).not.toBeInTheDocument();
  });

  it('shows strikethrough original price when original total is meaningfully above current total', () => {
    const room = baseRoom({
      totalPrice: 580,
      originalTotalPrice: 640,
    });
    renderWithTheme(<HotelDetailRoomCard room={room} stayNights={2} showReserveButton={false} />);
    expect(screen.getByText(/\$640/)).toBeInTheDocument();
  });
});

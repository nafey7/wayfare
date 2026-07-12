import type { ReactNode } from 'react';

import { MantineProvider } from '@mantine/core';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { mantineTheme } from '@/theme';
import type { ChatHotelInfo } from '@/types/api.helpers';

import { InlineHotelCard } from './InlineHotelCard';

function Wrapper({ children }: { children: ReactNode }) {
  return (
    <MantineProvider theme={mantineTheme} env="test">
      {children}
    </MantineProvider>
  );
}

function makeHotel(overrides: Partial<ChatHotelInfo> = {}): ChatHotelInfo {
  return {
    hotel_id: 'h1',
    hotel_name: 'Mandarin Oriental',
    city: 'Tokyo',
    country: 'Japan',
    address: '2-1-1 Nihonbashi Muromachi',
    per_night_price: 250,
    currency: 'USD',
    hotel_rating: 5,
    ...overrides,
  };
}

describe('InlineHotelCard', () => {
  it('renders check-in label with price + book button', () => {
    render(
      <Wrapper>
        <InlineHotelCard hotel={makeHotel()} phase="check-in" onBook={vi.fn()} />
      </Wrapper>
    );
    expect(screen.getByText(/Hotel check-in/i)).toBeInTheDocument();
    expect(screen.getByText(/Mandarin Oriental/)).toBeInTheDocument();
    expect(screen.getByText(/\/night/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /book this/i })).toBeInTheDocument();
  });

  it('renders check-out label without price or book button', () => {
    render(
      <Wrapper>
        <InlineHotelCard hotel={makeHotel()} phase="check-out" />
      </Wrapper>
    );
    expect(screen.getByText(/Hotel check-out/i)).toBeInTheDocument();
    expect(screen.getByText(/Mandarin Oriental/)).toBeInTheDocument();
    // No "/night" on check-out — guest is leaving, not booking.
    expect(screen.queryByText(/\/night/)).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /book this/i })
    ).not.toBeInTheDocument();
  });

  it('renders address when present, else falls back to city', () => {
    render(
      <Wrapper>
        <InlineHotelCard
          hotel={makeHotel({ address: '', city: 'Tokyo' })}
          phase="check-in"
        />
      </Wrapper>
    );
    expect(screen.getByText('Tokyo')).toBeInTheDocument();
  });

  it('falls back to total_price (labelled "total") when per_night_price absent', () => {
    // A partial payload with only ``total_price`` must NOT mislabel the total
    // as a per-night rate. The suffix is "total" instead.
    render(
      <Wrapper>
        <InlineHotelCard
          hotel={makeHotel({ per_night_price: undefined, total_price: 500 })}
          phase="check-in"
        />
      </Wrapper>
    );
    expect(screen.getByText('total')).toBeInTheDocument();
    expect(screen.queryByText(/\/night/)).not.toBeInTheDocument();
  });

  it('renders no price when neither per_night_price nor total_price present', () => {
    render(
      <Wrapper>
        <InlineHotelCard
          hotel={makeHotel({ per_night_price: undefined, total_price: undefined })}
          phase="check-in"
        />
      </Wrapper>
    );
    expect(screen.queryByText(/\/night/)).not.toBeInTheDocument();
    expect(screen.queryByText('total')).not.toBeInTheDocument();
  });

  it('calls onBook with the full hotel object on check-in click', async () => {
    const onBook = vi.fn();
    const hotel = makeHotel();
    const { default: userEvent } = await import('@testing-library/user-event');
    const user = userEvent.setup();
    render(
      <Wrapper>
        <InlineHotelCard hotel={hotel} phase="check-in" onBook={onBook} />
      </Wrapper>
    );
    await user.click(screen.getByRole('button', { name: /book this/i }));
    expect(onBook).toHaveBeenCalledWith(hotel);
  });

  it('gracefully handles missing fields', () => {
    render(
      <Wrapper>
        <InlineHotelCard hotel={{ hotel_name: 'Some Hotel' }} phase="check-in" />
      </Wrapper>
    );
    expect(screen.getByText(/Hotel check-in/i)).toBeInTheDocument();
    expect(screen.getByText(/Some Hotel/)).toBeInTheDocument();
  });

  it('renders fallback name when hotel_name is absent', () => {
    const legacy: ChatHotelInfo = { name: 'Old Field Name' };
    render(
      <Wrapper>
        <InlineHotelCard hotel={legacy} phase="check-in" />
      </Wrapper>
    );
    expect(screen.getByText(/Old Field Name/)).toBeInTheDocument();
  });
});

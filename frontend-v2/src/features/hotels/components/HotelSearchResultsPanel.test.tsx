import type { ReactNode } from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { MantineProvider } from '@mantine/core';
import { mantineTheme } from '@/theme';
import { trackEvent } from '@/utils/gtm';
import type { ExtractedHotelSearchData } from '@/types/api.helpers';
import { HotelSearchResultsPanel } from './HotelSearchResultsPanel';
import { resetHotelSearchResultsShownDedupeForTests } from '@/features/hotels/utils/hotelSearchResultsAnalyticsDedupe';

vi.mock('@/utils/gtm', () => ({ trackEvent: vi.fn() }));

vi.mock('@/features/chat/components/hotels/ExpandableHotelCardList', () => ({
  ExpandableHotelCardList: ({ hotels }: { hotels: Array<{ hotel_name?: string }> }) => (
    <div data-testid="expandable-list">
      {hotels?.map((h) => h.hotel_name ?? '').filter(Boolean).join(', ')}
    </div>
  ),
}));

vi.mock('@/features/chat/components/hotels/useBestHotelsWithValidImages', () => ({
  useBestHotelsWithValidImages: (mapped: unknown[] | null | undefined) => ({
    hotels: mapped ?? [],
    isLoading: false,
  }),
}));

function makeHotel(name: string) {
  return {
    hotel_id: name,
    token_id: `t-${name}`,
    hotel_name: `Hotel ${name}`,
    total_price: 100,
    currency: 'EUR',
  };
}

function makeExtracted(hotels: Array<Record<string, unknown>>): ExtractedHotelSearchData {
  return {
    session_id: 'test-session',
    hotels,
    data: {
      search_params: {
        destination_city: 'Paris',
        check_in_date: '2026-06-01',
        check_out_date: '2026-06-03',
        rooms: 1,
        adults: 2,
      },
      summary: {
        total_hotels: hotels.length,
        nights: 2,
        price_range: { min: 90, currency: 'EUR' },
      },
    },
  };
}

function Wrapper({ children }: { children: ReactNode }) {
  return (
    <MantineProvider theme={mantineTheme} env="test">
      <MemoryRouter>{children}</MemoryRouter>
    </MantineProvider>
  );
}

describe('HotelSearchResultsPanel', () => {
  beforeEach(() => {
    resetHotelSearchResultsShownDedupeForTests();
    vi.mocked(trackEvent).mockClear();
  });

  it('renders the flat hotel list with no tabs and no "Show All Hotels" CTA (#1034)', () => {
    const data = makeExtracted([makeHotel('a'), makeHotel('b'), makeHotel('c')]);

    render(
      <Wrapper>
        <HotelSearchResultsPanel data={data} source="recommendations" />
      </Wrapper>
    );

    expect(screen.queryByRole('tablist')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /show all hotels/i })).not.toBeInTheDocument();
    expect(screen.getByTestId('expandable-list')).toHaveTextContent('Hotel a, Hotel b, Hotel c');
  });

  it('falls back to legacy categories.best_value.hotels when flat array is absent', () => {
    const legacy: ExtractedHotelSearchData = {
      session_id: 'test-session',
      hotels: [],
      data: {
        search_params: { destination_city: 'Paris' },
        summary: { total_hotels: 1 },
        categories: {
          cheapest: { hotels: [] },
          highest_rated: { hotels: [] },
          best_value: { hotels: [makeHotel('legacy')] },
        },
      },
    };

    render(
      <Wrapper>
        <HotelSearchResultsPanel data={legacy} source="recommendations" />
      </Wrapper>
    );

    expect(screen.getByTestId('expandable-list')).toHaveTextContent('Hotel legacy');
  });

  it('fires hotel_search_results_shown once per dedupe key on rerender', () => {
    const data = makeExtracted([makeHotel('a')]);

    const { rerender } = render(
      <Wrapper>
        <HotelSearchResultsPanel data={data} source="recommendations" />
      </Wrapper>
    );

    expect(trackEvent).toHaveBeenCalledTimes(1);
    expect(trackEvent).toHaveBeenCalledWith(
      'hotel_search_results_shown',
      expect.objectContaining({ source: 'recommendations' })
    );

    rerender(
      <Wrapper>
        <HotelSearchResultsPanel data={data} source="recommendations" />
      </Wrapper>
    );

    expect(trackEvent).toHaveBeenCalledTimes(1);
  });

  it('returns null when the hotel list is empty', () => {
    const data = makeExtracted([]);

    render(
      <Wrapper>
        <HotelSearchResultsPanel data={data} source="recommendations" />
      </Wrapper>
    );

    expect(screen.queryByTestId('expandable-list')).not.toBeInTheDocument();
    expect(screen.queryByRole('tablist')).not.toBeInTheDocument();
  });
});

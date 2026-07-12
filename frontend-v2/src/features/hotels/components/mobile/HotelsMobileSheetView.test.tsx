import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';
import { mantineTheme } from '@/theme';
import type { Hotel } from '@/types/hotels';
import { HotelsMobileSheetView } from './HotelsMobileSheetView';

// Stub heavy children that are unrelated to the toolbar wiring under test.
vi.mock('@vis.gl/react-google-maps', () => ({
  APIProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));
vi.mock('../HotelMobileMapView', () => ({
  HotelMobileMapView: () => null,
}));
vi.mock('../HotelCard', () => ({
  HotelCard: () => null,
}));
vi.mock('../HotelPinCard', () => ({
  HotelPinCard: () => null,
}));
vi.mock('lucide-react', () => ({
  SlidersHorizontal: () => null,
  Filter: () => null,
  ArrowUpDown: () => null,
}));

const hotel: Hotel = {
  id: 'h1',
  name: 'Test Hotel',
  starRating: 4,
} as unknown as Hotel;

function renderSheet(overrides: Partial<React.ComponentProps<typeof HotelsMobileSheetView>> = {}) {
  const props: React.ComponentProps<typeof HotelsMobileSheetView> = {
    hotels: [hotel],
    nights: 2,
    selectingTokenId: null,
    onHotelSelect: vi.fn(),
    onOpenFilters: vi.fn(),
    activeFilterCount: 0,
    sortBy: 'preference-match',
    onSortChange: vi.fn(),
    sortMenuItems: [
      { value: 'preference-match', label: 'Your preferences' },
      { value: 'price-low', label: 'Price' },
    ],
    onChangePreferences: vi.fn(),
    ...overrides,
  };
  return { ...render(
    <MantineProvider theme={mantineTheme}>
      <HotelsMobileSheetView {...props} />
    </MantineProvider>,
  ), props };
}

describe('HotelsMobileSheetView — MobileSortToolbar wiring', () => {
  it('renders the Sort, Change preferences, and Filters affordances in the header', () => {
    renderSheet();
    expect(screen.getByRole('button', { name: /^sort$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /change preferences/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^filters$/i })).toBeInTheDocument();
  });

  it('shows the active filter count on the Filters button', () => {
    renderSheet({ activeFilterCount: 3 });
    expect(screen.getByRole('button', { name: /filters \(3\)/i })).toBeInTheDocument();
  });

  it('wires Change preferences and Filters callbacks', async () => {
    const user = userEvent.setup();
    const { props } = renderSheet();

    await user.click(screen.getByRole('button', { name: /change preferences/i }));
    expect(props.onChangePreferences).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole('button', { name: /^filters$/i }));
    expect(props.onOpenFilters).toHaveBeenCalledTimes(1);
  });

  it('wires the sort menu to onSortChange', async () => {
    const user = userEvent.setup();
    const { props } = renderSheet();

    await user.click(screen.getByRole('button', { name: /^sort$/i }));
    await user.click(await screen.findByRole('menuitem', { name: /^price$/i }));

    expect(props.onSortChange).toHaveBeenCalledWith('price-low');
  });
});

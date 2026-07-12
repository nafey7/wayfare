import type { Meta, StoryObj } from '@storybook/react-vite';
import { within, expect, fn } from 'storybook/test';
import { useState } from 'react';
import { HotelFiltersDialog } from './HotelFiltersDialog';
import {
  mockFilterableHotels,
  defaultHotelFilterState,
  mockActiveFilterState,
} from '../__fixtures__/mockHotelData';
import type { HotelFilterState } from '../__fixtures__/mockHotelData';

function StatefulDialog(props: { initialState?: HotelFilterState; filteredCount?: number }) {
  const [filterState, setFilterState] = useState<HotelFilterState>(
    props.initialState ?? defaultHotelFilterState
  );
  return (
    <HotelFiltersDialog
      opened
      onClose={fn()}
      filterState={filterState}
      onFilterChange={setFilterState}
      allHotels={mockFilterableHotels}
      filteredHotelCount={props.filteredCount ?? mockFilterableHotels.length}
    />
  );
}

const meta: Meta<typeof HotelFiltersDialog> = {
  title: 'Hotels/HotelFiltersDialog',
  component: HotelFiltersDialog,
  parameters: { layout: 'fullscreen' },
};

export default meta;
type Story = StoryObj<typeof HotelFiltersDialog>;

/** Default: opened dialog with no active filters. */
export const Default: Story = {
  render: () => <StatefulDialog />,
  play: async () => {
    const body = within(document.body);
    expect(body.getByRole('heading', { name: 'Filters', level: 2 })).toBeInTheDocument();
    expect(body.getByText('Star rating')).toBeInTheDocument();
    expect(body.getByText('Fare type')).toBeInTheDocument();
    const btn = body.getByRole('button', { name: /Show \d+ hotels?/ });
    expect(btn).toBeInTheDocument();
  },
};

/** With active filters pre-populated. */
export const WithActiveFilters: Story = {
  render: () => (
    <StatefulDialog initialState={mockActiveFilterState} filteredCount={3} />
  ),
  play: async () => {
    const body = within(document.body);
    expect(body.getByRole('heading', { name: 'Filters', level: 2 })).toBeInTheDocument();
    const btn = body.getByRole('button', { name: /Show 3 hotels/ });
    expect(btn).toBeInTheDocument();
    const fourStar = body.getByRole('checkbox', { name: /4 stars/i });
    expect(fourStar).toBeChecked();
  },
};

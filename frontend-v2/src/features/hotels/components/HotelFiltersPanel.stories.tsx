import type { Meta, StoryObj } from '@storybook/react-vite';
import { within, expect, fn } from 'storybook/test';
import { useState } from 'react';
import { HotelFiltersPanel } from './HotelFiltersPanel';
import {
  mockFilterableHotels,
  defaultHotelFilterState,
  mockActiveFilterState,
} from '../__fixtures__/mockHotelData';
import type { HotelFilterState } from '../__fixtures__/mockHotelData';

function StatefulFiltersPanel(props: { initialState: HotelFilterState }) {
  const [filterState, setFilterState] = useState(props.initialState);
  return (
    <HotelFiltersPanel
      filterState={filterState}
      onFilterChange={setFilterState}
      allHotels={mockFilterableHotels}
    />
  );
}

const meta: Meta<typeof HotelFiltersPanel> = {
  title: 'Hotels/HotelFiltersPanel',
  component: HotelFiltersPanel,
  parameters: { layout: 'padded' },
  args: {
    filterState: defaultHotelFilterState,
    onFilterChange: fn(),
    allHotels: mockFilterableHotels,
  },
};

export default meta;
type Story = StoryObj<typeof HotelFiltersPanel>;

/** Default state: no active filters, all accordions expanded. */
export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Filters')).toBeInTheDocument();
    expect(canvas.getByText('Price')).toBeInTheDocument();
    expect(canvas.getByText('Star rating')).toBeInTheDocument();
    expect(canvas.getByText('Fare type')).toBeInTheDocument();
  },
};

/** With active filters: 4- and 5-star ratings selected, name query set. */
export const WithActiveFilters: Story = {
  render: () => <StatefulFiltersPanel initialState={mockActiveFilterState} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Filters')).toBeInTheDocument();
    const reset = canvas.getByRole('button', { name: /Reset all/i });
    expect(reset).not.toBeDisabled();
    const fourStar = canvas.getByRole('checkbox', { name: /4 stars/i });
    expect(fourStar).toBeChecked();
    const fiveStar = canvas.getByRole('checkbox', { name: /5 stars/i });
    expect(fiveStar).toBeChecked();
  },
};

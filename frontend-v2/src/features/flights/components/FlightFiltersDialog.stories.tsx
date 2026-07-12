import { useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, within } from 'storybook/test';
import { FlightFiltersDialog } from './FlightFiltersDialog';
import type { FlightFilterState } from '../utils/flightFilters';
import {
  defaultFlightFilterState,
  mockFilterableFlights,
  mockFilterStateActive,
} from '../__fixtures__/mockFlightSearchData';

const meta: Meta<typeof FlightFiltersDialog> = {
  title: 'Flights/FlightFiltersDialog',
  component: FlightFiltersDialog,
  parameters: { layout: 'fullscreen' },
};

export default meta;
type Story = StoryObj<typeof FlightFiltersDialog>;

function Controlled({ initialFilters, ...rest }: Omit<React.ComponentProps<typeof FlightFiltersDialog>, 'opened' | 'onClose' | 'filterState' | 'onFilterChange'> & { initialFilters?: FlightFilterState }) {
  const [opened, setOpened] = useState(true);
  const [filterState, setFilterState] = useState<FlightFilterState>(
    initialFilters ?? defaultFlightFilterState
  );
  return (
    <FlightFiltersDialog
      {...rest}
      opened={opened}
      onClose={() => setOpened(false)}
      filterState={filterState}
      onFilterChange={setFilterState}
    />
  );
}

/** One-way search — no inbound tabs. */
export const OneWay: Story = {
  render: () => (
    <Controlled
      allFlights={mockFilterableFlights}
      isRoundTrip={false}
      filteredFlightCount={mockFilterableFlights.length}
    />
  ),
  play: async () => {
    const body = within(document.body);
    expect(body.getByText('Filter flights')).toBeInTheDocument();
    expect(body.getByText('Price')).toBeInTheDocument();
    expect(body.getByText('Stops')).toBeInTheDocument();
    expect(body.getByLabelText('Close filters')).toBeInTheDocument();
  },
};

/** Round-trip search — shows Outbound/Inbound tabs for stops, duration, departure/arrival time, airports. */
export const RoundTrip: Story = {
  render: () => (
    <Controlled
      allFlights={mockFilterableFlights}
      isRoundTrip={true}
      filteredFlightCount={mockFilterableFlights.length}
    />
  ),
  play: async () => {
    const body = within(document.body);
    expect(body.getByText('Filter flights')).toBeInTheDocument();
    // Round-trip surfaces Outbound/Inbound tabs in the Stops section
    expect(body.getAllByRole('tab', { name: 'Outbound' })[0]).toBeInTheDocument();
    expect(body.getAllByRole('tab', { name: 'Inbound' })[0]).toBeInTheDocument();
  },
};

/** Pre-populated active filters — footer shows non-zero flight count. */
export const ActiveFilters: Story = {
  render: () => (
    <Controlled
      allFlights={mockFilterableFlights}
      isRoundTrip={false}
      filteredFlightCount={2}
      initialFilters={mockFilterStateActive}
    />
  ),
  play: async () => {
    const body = within(document.body);
    // Footer shows filtered count
    expect(body.getByRole('button', { name: /Show 2 flights/i })).toBeInTheDocument();
    // "Clear all" is available
    expect(body.getByRole('button', { name: /Clear all/i })).toBeInTheDocument();
  },
};

/** Zero results — footer reflects empty results. */
export const NoResults: Story = {
  render: () => (
    <Controlled
      allFlights={mockFilterableFlights}
      isRoundTrip={false}
      filteredFlightCount={0}
      initialFilters={mockFilterStateActive}
    />
  ),
  play: async () => {
    const body = within(document.body);
    expect(body.getByRole('button', { name: /Show 0 flights/i })).toBeInTheDocument();
  },
};

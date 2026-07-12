import { useEffect } from 'react';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, fn, waitFor, within } from 'storybook/test';
import { FlightSearchBar } from './FlightSearchBar';
import { useAppDispatch } from '@/store/hooks';
import {
  setFrom,
  setTo,
  setTripType,
  setMultiCitySegments,
} from '@/store/slices/flightBookingSlice';

/**
 * Legacy `FlightSearchBar` (the one used on /flights/search via the index re-export).
 * `FlightSearchBarV2` is the current page-level bar; this component is kept for
 * backwards compatibility and Mantine migration coverage. Story dispatches Redux
 * state to keep it hermetic — same pattern as `FlightSearchBarV2.stories.tsx`.
 */
const meta: Meta<typeof FlightSearchBar> = {
  title: 'Flights/FlightSearchBar',
  component: FlightSearchBar,
  parameters: { layout: 'padded' },
  decorators: [
    (Story) => (
      <div style={{ maxWidth: 1100 }}>
        <Story />
      </div>
    ),
  ],
  args: {
    onSearch: fn(),
    isSearching: false,
  },
};

export default meta;
type Story = StoryObj<typeof FlightSearchBar>;

export const Default: Story = {
  render: function Render(args) {
    const dispatch = useAppDispatch();
    useEffect(() => {
      dispatch(setTripType('one-way'));
      dispatch(setFrom({ value: '' }));
      dispatch(setTo({ value: '' }));
    }, [dispatch]);
    return <FlightSearchBar {...args} />;
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() => {
      expect(canvas.getByRole('button', { name: /search/i })).toBeInTheDocument();
    });
    expect(canvas.getAllByRole('textbox').length).toBeGreaterThan(0);
    expect(canvas.getAllByPlaceholderText(/city or airport/i).length).toBeGreaterThanOrEqual(2);
  },
};

export const WithRoute: Story = {
  render: function Render(args) {
    const dispatch = useAppDispatch();
    useEffect(() => {
      dispatch(setTripType('one-way'));
      dispatch(
        setFrom({
          value: 'AMS',
          airport: {
            iata: 'AMS',
            name: 'Amsterdam Airport Schiphol',
            city: 'Amsterdam',
            country: 'Netherlands',
          },
        })
      );
      dispatch(
        setTo({
          value: 'BCN',
          airport: {
            iata: 'BCN',
            name: 'Barcelona El Prat Airport',
            city: 'Barcelona',
            country: 'Spain',
          },
        })
      );
    }, [dispatch]);
    return <FlightSearchBar {...args} />;
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() => {
      expect(canvas.getAllByDisplayValue(/AMS|Amsterdam/i).length).toBeGreaterThan(0);
    });
  },
};

export const Multicity: Story = {
  render: function Render(args) {
    const dispatch = useAppDispatch();
    useEffect(() => {
      dispatch(setTripType('multi-city'));
      dispatch(
        setMultiCitySegments([
          {
            from: 'LHR',
            to: 'JFK',
            date: '2026-07-01',
            fromAirport: { iata: 'LHR', name: 'London Heathrow Airport', city: 'London', country: 'United Kingdom' },
            toAirport: { iata: 'JFK', name: 'John F. Kennedy International Airport', city: 'New York', country: 'United States' },
          },
          {
            from: 'JFK',
            to: 'CDG',
            date: '2026-07-08',
            fromAirport: { iata: 'JFK', name: 'John F. Kennedy International Airport', city: 'New York', country: 'United States' },
            toAirport: { iata: 'CDG', name: 'Paris Charles de Gaulle Airport', city: 'Paris', country: 'France' },
          },
        ])
      );
    }, [dispatch]);
    return <FlightSearchBar {...args} />;
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() => {
      expect(canvas.getAllByDisplayValue(/LHR|London/i).length).toBeGreaterThan(0);
    });
  },
};

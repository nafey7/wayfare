import { useEffect } from 'react';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, waitFor, within } from 'storybook/test';
import { FlightSearchBarV2 } from './FlightSearchBarV2';
import { useAppDispatch } from '@/store/hooks';
import {
  setFrom,
  setTo,
  setTripType,
  setMultiCitySegments,
  openFlightRouteModal,
} from '@/store/slices/flightBookingSlice';

/**
 * FlightSearchBarV2 is a Mantine Modal that reads route state from Redux.
 * Each story must dispatch openFlightRouteModal() so the modal is visible.
 * Mantine modals portal to document.body, so play functions query document.body
 * rather than canvasElement.
 */
const meta: Meta<typeof FlightSearchBarV2> = {
  title: 'Flights/FlightSearchBarV2',
  component: FlightSearchBarV2,
  parameters: { layout: 'padded' },
};

export default meta;
type Story = StoryObj<typeof FlightSearchBarV2>;

/**
 * Default empty state — one-way, no route selected.
 * Modal shows "From" / "To" labels with empty inputs.
 */
export const Default: Story = {
  render: function Render() {
    const dispatch = useAppDispatch();
    useEffect(() => {
      dispatch(setTripType('one-way'));
      dispatch(setFrom({ value: '' }));
      dispatch(setTo({ value: '' }));
      dispatch(openFlightRouteModal());
    }, [dispatch]);
    return <FlightSearchBarV2 />;
  },
  play: async () => {
    const canvas = within(document.body as HTMLElement);
    await waitFor(() => {
      expect(canvas.getByText('From')).toBeInTheDocument();
    });
    expect(canvas.getByText('To')).toBeInTheDocument();
  },
};

/**
 * One-way with AMS → BCN route pre-set via Redux dispatch.
 * The AirportAutocomplete inputs show the raw IATA codes as their values.
 */
export const WithRoute: Story = {
  render: function Render() {
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
      dispatch(openFlightRouteModal());
    }, [dispatch]);
    return <FlightSearchBarV2 />;
  },
  play: async () => {
    const canvas = within(document.body as HTMLElement);
    await waitFor(() => {
      expect(canvas.getByDisplayValue('AMS')).toBeInTheDocument();
    });
    expect(canvas.getByDisplayValue('BCN')).toBeInTheDocument();
  },
};

/**
 * Multi-city mode — two legs (LHR → JFK → CDG).
 * The multi-city modal renders per-leg AirportAutocomplete inputs with IATA codes.
 */
export const Multicity: Story = {
  render: function Render() {
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
      dispatch(openFlightRouteModal());
    }, [dispatch]);
    return <FlightSearchBarV2 />;
  },
  play: async () => {
    const canvas = within(document.body as HTMLElement);
    await waitFor(() => {
      expect(canvas.getByDisplayValue('LHR')).toBeInTheDocument();
    });
    expect(canvas.getAllByDisplayValue('JFK').length).toBeGreaterThanOrEqual(1);
  },
};

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ThemeProvider } from '@mui/material/styles';
import { MantineProvider } from '@mantine/core';
import { lightTheme, mantineTheme } from '@/theme';

import type { FlightCardProps } from './FlightCard';
import { FlightCard } from './FlightCard';

vi.mock('@/api/flightsApi', () => ({
  useResolveAirportQuery: () => ({ data: null }),
}));

function makeMockFlight(
  overrides: Partial<FlightCardProps['flight']> = {},
): FlightCardProps['flight'] {
  return {
    id: 'flight-1',
    aircraftName: 'A320',
    tags: [],
    passengers: 1,
    price: 450,
    legs: [
      {
        departure: {
          city: 'London',
          airport: 'LHR',
          date: 'Mon, 1 Jan',
          time: '10:00',
        },
        arrival: {
          city: 'Paris',
          airport: 'CDG',
          date: 'Mon, 1 Jan',
          time: '12:00',
        },
        duration: '2h',
        totalTimeDisplay: '2h',
        stops: 0,
        stopsText: 'Non Stop',
        airlinesInfo: [{ name: 'Test Air', code: 'TA', flights: ['TA123'] }],
      },
    ],
    ...overrides,
  };
}

function renderFlightCard(props: Partial<FlightCardProps> = {}) {
  const flight = props.flight ?? makeMockFlight();
  return render(
    <ThemeProvider theme={lightTheme}>
      <MantineProvider theme={mantineTheme}>
        <FlightCard flight={flight} onSelect={props.onSelect} isSelecting={props.isSelecting} />
      </MantineProvider>
    </ThemeProvider>,
  );
}

describe('FlightCard', () => {
  it('opens the details dialog when the info button is clicked', async () => {
    const user = userEvent.setup();
    renderFlightCard();

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Flight details' }));

    expect(await screen.findByRole('dialog')).toBeInTheDocument();
  });

  it('calls onSelect when the card is clicked and does not open the details dialog', async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    renderFlightCard({ onSelect });

    await user.click(screen.getByText(/10:00/));

    expect(onSelect).toHaveBeenCalledWith('flight-1');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});

import type { ReactNode } from 'react';

import { MantineProvider } from '@mantine/core';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { mantineTheme } from '@/theme';
import type { FlightInfo } from '@/types/api.helpers';

import { InlineFlightCard } from './InlineFlightCard';

function Wrapper({ children }: { children: ReactNode }) {
  return (
    <MantineProvider theme={mantineTheme} env="test">
      {children}
    </MantineProvider>
  );
}

function makeFlight(overrides: Partial<FlightInfo> = {}): FlightInfo {
  return {
    id: 'f1',
    airline: 'British Airways',
    airline_code: 'BA',
    flight_number: 'BA304',
    origin_code: 'LHR',
    destination_code: 'CDG',
    departure_time: '10:00',
    departure_date: '2026-06-20',
    arrival_time: '12:30',
    arrival_date: '2026-06-20',
    duration: '1h 30m',
    duration_minutes: 90,
    stops: 0,
    price: 250,
    currency: 'USD',
    ...overrides,
  };
}

describe('InlineFlightCard', () => {
  it('renders outbound label by default', () => {
    render(
      <Wrapper>
        <InlineFlightCard flight={makeFlight()} />
      </Wrapper>
    );
    expect(screen.getByText(/Outbound flight/i)).toBeInTheDocument();
    expect(screen.queryByText(/Return flight/i)).not.toBeInTheDocument();
  });

  it('renders return label when leg=inbound', () => {
    render(
      <Wrapper>
        <InlineFlightCard flight={makeFlight()} leg="inbound" />
      </Wrapper>
    );
    expect(screen.getByText(/Return flight/i)).toBeInTheDocument();
  });

  it('renders origin → destination + times', () => {
    render(
      <Wrapper>
        <InlineFlightCard flight={makeFlight()} />
      </Wrapper>
    );
    // The route + times are rendered as one string with "→" between them.
    expect(screen.getByText(/LHR.*10:00.*→.*CDG.*12:30/)).toBeInTheDocument();
  });

  it('renders airline + flight number', () => {
    render(
      <Wrapper>
        <InlineFlightCard flight={makeFlight()} />
      </Wrapper>
    );
    expect(screen.getByText(/British Airways/)).toBeInTheDocument();
    expect(screen.getByText(/BA304/)).toBeInTheDocument();
  });

  it('renders Direct label when stops=0', () => {
    render(
      <Wrapper>
        <InlineFlightCard flight={makeFlight({ stops: 0 })} />
      </Wrapper>
    );
    expect(screen.getByText(/Direct/)).toBeInTheDocument();
  });

  it('renders multi-stop label when stops>1', () => {
    render(
      <Wrapper>
        <InlineFlightCard flight={makeFlight({ stops: 2 })} />
      </Wrapper>
    );
    expect(screen.getByText(/2 stops/)).toBeInTheDocument();
  });

  it('Book button is disabled when no onBook handler', () => {
    render(
      <Wrapper>
        <InlineFlightCard flight={makeFlight()} />
      </Wrapper>
    );
    const button = screen.getByRole('button', { name: /book this/i });
    expect(button).toBeDisabled();
  });

  it('calls onBook with the full flight object on click', async () => {
    const onBook = vi.fn();
    const flight = makeFlight();
    const { default: userEvent } = await import('@testing-library/user-event');
    const user = userEvent.setup();
    render(
      <Wrapper>
        <InlineFlightCard flight={flight} onBook={onBook} />
      </Wrapper>
    );
    await user.click(screen.getByRole('button', { name: /book this/i }));
    expect(onBook).toHaveBeenCalledWith(flight);
  });

  it('gracefully handles missing fields', () => {
    // Defensive: backend may emit a partial flight (no airline / flight_number / etc).
    // The card must render without crashing. The runtime is tolerant of
    // missing fields even though FlightInfo declares them as required.
    const partial = { origin_code: 'LHR', destination_code: 'CDG' } as unknown as FlightInfo;
    render(
      <Wrapper>
        <InlineFlightCard flight={partial} />
      </Wrapper>
    );
    expect(screen.getByText(/Outbound flight/i)).toBeInTheDocument();
    expect(screen.getByText(/LHR.*→.*CDG/)).toBeInTheDocument();
  });
});

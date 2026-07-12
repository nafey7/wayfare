import { useState } from 'react';
import { Box, Button, Collapse } from '@mantine/core';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { FlightDetailsCard } from './FlightDetailsCard';
import type { MappedFlight } from '@/types/flight';
import type { FlightSearchParams } from '@/types/flight';

interface ExpandableFlightCardListProps {
  flights: MappedFlight[];
  searchParams?: Pick<FlightSearchParams, 'passengers' | 'adults' | 'children' | 'infants'>;
  /** When true, show all flights expanded with no show more/show less toggle (e.g. on /flights/recommendations) */
  showAllFlights?: boolean;
  /** Curated category label to show as a badge on each card (e.g. "Best Value", "Cheapest", "Fastest") */
  categoryLabel?: string;
}

export function ExpandableFlightCardList({
  flights,
  searchParams,
  showAllFlights = false,
  categoryLabel,
}: ExpandableFlightCardListProps) {
  const [expanded, setExpanded] = useState(showAllFlights);

  return (
    <Box>
      {flights.length > 0 && flights[0] && (
        <FlightDetailsCard
          flight={flights[0]}
          key={flights[0].id || 0}
          searchParams={searchParams}
          categoryLabel={categoryLabel}
        />
      )}

      {flights.length > 1 && (
        <>
          <Collapse in={expanded || showAllFlights}>
            <Box style={{ marginTop: 16 }}>
              {flights.slice(1).map((flight, index) => (
                <FlightDetailsCard
                  flight={flight}
                  key={flight.id || index + 1}
                  searchParams={searchParams}
                  categoryLabel={categoryLabel}
                />
              ))}
            </Box>
          </Collapse>

          {!showAllFlights && (
            <Button
              fullWidth
              variant="subtle"
              onClick={() => setExpanded(!expanded)}
              rightSection={expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              style={{ marginTop: 8 }}
            >
              {expanded ? 'Show Less' : `Show More flights`}
            </Button>
          )}
        </>
      )}
    </Box>
  );
}

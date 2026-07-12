import { Box, Text } from '@mantine/core';
import { FlightCard, type FlightCardProps, type FlightCardPassengerCounts } from './FlightCard';
import type { FlightLeg } from '@/types/flight';

interface FlightResultsProps {
  flights: Array<{
    id: string;
    aircraftName: string;
    tags: string[];
    passengers: number;
    passengerCounts?: FlightCardPassengerCounts;
    legs: FlightLeg[];
    price: number;
    discount?: number;
  }>;
  onFlightSelect?: (flightId: string) => void;
  selectingFlightId?: string | null;
  /** When set, that card shows a persistent selected outline (e.g. multicity per-leg choice) */
  selectedFlightId?: string | null;
}

export function FlightResults({
  flights,
  onFlightSelect,
  selectingFlightId,
  selectedFlightId,
}: FlightResultsProps) {
  return (
    <Box>
      <Box className="flights-list-container" style={{ overflowAnchor: 'none' }}>
        {flights.length === 0 ? (
          <Text c="dimmed" ta="center" py="md">
            No flights found. Try adjusting your search criteria.
          </Text>
        ) : (
          flights.map((flight) => (
            <FlightCard
              key={flight.id}
              flight={flight as FlightCardProps['flight']}
              onSelect={onFlightSelect}
              isSelecting={selectingFlightId === flight.id}
              isSelected={selectedFlightId != null && selectedFlightId === flight.id}
            />
          ))
        )}
      </Box>
    </Box>
  );
}

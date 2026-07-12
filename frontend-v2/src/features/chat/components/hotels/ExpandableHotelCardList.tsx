import { useState } from 'react';
import { Button, Collapse, Stack } from '@mantine/core';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { HotelDetailsCard, type HotelSearchParams } from './HotelDetailsCard';
import type { MappedHotel } from '@/features/chat/utils/hotelUtils';

interface ExpandableHotelCardListProps {
  hotels: MappedHotel[];
  searchParams?: HotelSearchParams;
  /** When true, show all hotels with no show more/less toggle. */
  showAllHotels?: boolean;
  /** Value signal badge shown on the first hotel card e.g. "Best Value", "Cheapest" */
  valueBadge?: string;
}

export function ExpandableHotelCardList({
  hotels,
  searchParams = {},
  showAllHotels = false,
  valueBadge,
}: ExpandableHotelCardListProps) {
  const [expanded, setExpanded] = useState(showAllHotels);

  const first = hotels?.[0];
  if (!first || hotels.length === 0) {
    return null;
  }

  return (
    <Stack gap="xs">
      <HotelDetailsCard
        hotel={first}
        searchParams={searchParams}
        key={first.token_id || first.product_id || 0}
        valueBadge={valueBadge}
      />

      {hotels.length > 1 ? (
        <>
          <Collapse in={expanded || showAllHotels}>
            <Stack gap="xs">
              {hotels.slice(1).map((hotel, index) => (
                <HotelDetailsCard
                  hotel={hotel}
                  searchParams={searchParams}
                  key={hotel.token_id || hotel.product_id || index + 1}
                />
              ))}
            </Stack>
          </Collapse>

          {!showAllHotels && (
            <Button
              fullWidth
              variant="subtle"
              onClick={() => setExpanded(!expanded)}
              rightSection={expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            >
              {expanded ? 'Show Less' : `Show ${hotels.length - 1} More Hotels`}
            </Button>
          )}
        </>
      ) : null}
    </Stack>
  );
}

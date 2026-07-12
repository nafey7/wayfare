import { useNavigate, useLocation } from 'react-router-dom';
import { Group, UnstyledButton } from '@mantine/core';
import { Hotel, PlaneTakeoff } from 'lucide-react';
import type { LinkedBookings } from '@/types/itineraries';
import {
  itinerarySavedFlightBookingsList,
  itinerarySavedHotelBookingsList,
  itineraryChatFlightBookingsList,
  itineraryChatHotelBookingsList,
  flightBookingDetail,
  hotelBookingDetail,
} from '@/features/routing';

export interface LinkedBookingChipsProps {
  /** Saved itinerary id (route param when viewing a persisted itinerary). */
  itineraryId: string;
  linkedBookings?: LinkedBookings | null;
}

const chipBaseStyle: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 6,
  height: 26,
  padding: '0 12px',
  borderRadius: 16,
  fontSize: 12,
  fontWeight: 500,
  border: '1px solid var(--mantine-color-default-border)',
  backgroundColor: 'transparent',
  color: 'var(--mantine-color-dark-8)',
};

const chipDisabledStyle: React.CSSProperties = {
  opacity: 0.5,
  cursor: 'not-allowed',
};

/**
 * Flight / hotel booking chips (enabled when API returns VOYA refs for this saved itinerary).
 * Multiple refs open an itinerary-scoped list; a single ref opens booking detail directly.
 */
export function LinkedBookingChips({
  itineraryId,
  linkedBookings,
}: LinkedBookingChipsProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const isSavedLayout = location.pathname.startsWith('/itineraries/');

  const flightRefs = linkedBookings?.flightVoyaReferences ?? [];
  const hotelRefs = linkedBookings?.hotelVoyaReferences ?? [];

  const flightListPath = isSavedLayout
    ? itinerarySavedFlightBookingsList(itineraryId)
    : itineraryChatFlightBookingsList(itineraryId);
  const hotelListPath = isSavedLayout
    ? itinerarySavedHotelBookingsList(itineraryId)
    : itineraryChatHotelBookingsList(itineraryId);

  const flightDisabled = flightRefs.length === 0;
  const hotelDisabled = hotelRefs.length === 0;

  return (
    <Group
      gap="xs"
      wrap="wrap"
      pt="md"
      pl="md"
      mb="md"
      role="group"
      aria-label="Bookings linked to this itinerary"
    >
      <UnstyledButton
        disabled={flightDisabled}
        aria-disabled={flightDisabled}
        aria-label={
          flightDisabled
            ? 'Flight booking: none linked'
            : flightRefs.length === 1
              ? 'Flight booking: open details'
              : `Flight bookings: ${flightRefs.length} linked, open list`
        }
        onClick={() => {
          if (flightDisabled) return;
          if (flightRefs.length === 1) {
            const ref = flightRefs[0];
            if (!ref) return;
            navigate(flightBookingDetail(ref));
            return;
          }
          navigate(flightListPath);
        }}
        style={{ ...chipBaseStyle, ...(flightDisabled ? chipDisabledStyle : null) }}
      >
        <PlaneTakeoff size={14} />
        {flightRefs.length > 1 ? `Flight booking (${flightRefs.length})` : 'Flight booking'}
      </UnstyledButton>
      <UnstyledButton
        disabled={hotelDisabled}
        aria-disabled={hotelDisabled}
        aria-label={
          hotelDisabled
            ? 'Hotel booking: none linked'
            : hotelRefs.length === 1
              ? 'Hotel booking: open details'
              : `Hotel bookings: ${hotelRefs.length} linked, open list`
        }
        onClick={() => {
          if (hotelDisabled) return;
          if (hotelRefs.length === 1) {
            const ref = hotelRefs[0];
            if (!ref) return;
            navigate(hotelBookingDetail(ref));
            return;
          }
          navigate(hotelListPath);
        }}
        style={{ ...chipBaseStyle, ...(hotelDisabled ? chipDisabledStyle : null) }}
      >
        <Hotel size={14} />
        {hotelRefs.length > 1 ? `Hotel booking (${hotelRefs.length})` : 'Hotel booking'}
      </UnstyledButton>
    </Group>
  );
}

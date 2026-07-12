import { useState } from 'react';
import { Alert, Box, Button, Card, Collapse, Divider, Group, Loader, Stack, Text, UnstyledButton } from '@mantine/core';
import { ChevronDown, ChevronUp, Hotel as HotelIcon, Map as MapIcon, PlaneTakeoff } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { AuthenticatedImage } from '@/features/itinerary/components/AuthenticatedImage';
import { LANDING_TOKENS } from '@/features/landing/landingTokens';
import { flightBookingDetail, hotelBookingDetail, itinerarySavedView } from '@/features/routing';
import { getFlightRouteLabel } from '@/features/itinerary/utils/flightRouteLabel';
import type { LinkedBookingEventSummary, LinkedBookings } from '@/types/itineraries';
import type { SavedItineraryCardSummary } from '@/features/itinerary/utils/savedItineraryCardSummary';
import { NAVY, LINE, MUTED, MIST } from '../../profileTokens';
import styles from './UpcomingTripsSection.module.css';

export interface UpcomingTripsSectionProps {
  trips: SavedItineraryCardSummary[];
  isLoading?: boolean;
  isError?: boolean;
  onRetry?: () => void;
}

function TripImagePlaceholder() {
  return (
    <Box
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: MIST,
      }}
    >
      <MapIcon size={28} color={MUTED} />
    </Box>
  );
}

function StatusDot({ confirmed }: { confirmed: boolean }) {
  const dotColor = confirmed ? LANDING_TOKENS.confirmColor : '#F59E0B';
  const label = confirmed ? 'Confirmed' : 'Planned';
  return (
    <Box style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <Box
        style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          backgroundColor: dotColor,
          flexShrink: 0,
        }}
      />
      <Text style={{ fontSize: 13, fontWeight: 600, color: NAVY }}>{label}</Text>
    </Box>
  );
}

function FlightBookingRow({
  voyaReference,
  event,
  onClick,
}: {
  voyaReference: string;
  event?: LinkedBookingEventSummary | null;
  onClick: () => void;
}) {
  const routeLabel = getFlightRouteLabel(event);
  return (
    <UnstyledButton
      onClick={onClick}
      aria-label={`Open flight booking ${voyaReference}`}
      style={{ display: 'block', width: '100%' }}
    >
      <Box
        className={styles.flightRow}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '9px 14px',
          borderRadius: 8,
          border: '1px solid var(--mantine-color-brand-2)',
        }}
      >
        <Box
          style={{
            width: 28,
            height: 28,
            borderRadius: 6,
            flexShrink: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'var(--mantine-color-brand-1)',
            color: 'var(--mantine-color-brand-6)',
          }}
        >
          <PlaneTakeoff size={14} aria-hidden />
        </Box>
        <Box style={{ flex: 1, minWidth: 0 }}>
          <Text style={{ fontSize: 13, fontWeight: 700, color: NAVY, lineHeight: '18px' }}>
            {routeLabel}
          </Text>
          <Text
            style={{
              fontSize: 11,
              color: MUTED,
              fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
              lineHeight: '16px',
            }}
          >
            {voyaReference}
          </Text>
        </Box>
        <Text style={{ fontSize: 14, color: MUTED }}>›</Text>
      </Box>
    </UnstyledButton>
  );
}

function HotelBookingRow({
  voyaReference,
  event,
  onClick,
}: {
  voyaReference: string;
  event?: LinkedBookingEventSummary | null;
  onClick: () => void;
}) {
  const hotelLabel = event?.hotelReferenceNumber
    ? `Hotel · ${event.hotelReferenceNumber}`
    : 'Hotel Booking';
  return (
    <UnstyledButton
      onClick={onClick}
      aria-label={`Open hotel booking ${voyaReference}`}
      style={{ display: 'block', width: '100%' }}
    >
      <Box
        className={styles.hotelRow}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '9px 14px',
          borderRadius: 8,
          border: '1px solid var(--mantine-color-grape-2)',
        }}
      >
        <Box
          style={{
            width: 28,
            height: 28,
            borderRadius: 6,
            flexShrink: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'var(--mantine-color-grape-1)',
            color: 'var(--mantine-color-grape-6)',
          }}
        >
          <HotelIcon size={14} />
        </Box>
        <Box style={{ flex: 1, minWidth: 0 }}>
          <Text style={{ fontSize: 13, fontWeight: 700, color: NAVY, lineHeight: '18px' }}>
            {hotelLabel}
          </Text>
          <Text
            style={{
              fontSize: 11,
              color: MUTED,
              fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
              lineHeight: '16px',
            }}
          >
            {voyaReference}
          </Text>
        </Box>
        <Text style={{ fontSize: 14, color: MUTED }}>›</Text>
      </Box>
    </UnstyledButton>
  );
}

function BookingsPanel({
  itineraryId,
  linkedBookings,
}: {
  itineraryId: string;
  linkedBookings: LinkedBookings;
}) {
  const navigate = useNavigate();
  const flightRefs = linkedBookings.flightVoyaReferences ?? [];
  const hotelRefs = linkedBookings.hotelVoyaReferences ?? [];
  const flightEvents = linkedBookings.flightEvents ?? [];
  const hotelEvents = linkedBookings.hotelEvents ?? [];

  return (
    <Box style={{ padding: '10px 14px 14px', backgroundColor: MIST }}>
      <Stack gap={6}>
        {flightRefs.map((ref, i) => (
          <FlightBookingRow
            key={`flight-${itineraryId}-${ref}`}
            voyaReference={ref}
            event={flightEvents[i]}
            onClick={() => navigate(flightBookingDetail(ref))}
          />
        ))}
        {hotelRefs.map((ref, i) => (
          <HotelBookingRow
            key={`hotel-${itineraryId}-${ref}`}
            voyaReference={ref}
            event={hotelEvents[i]}
            onClick={() => navigate(hotelBookingDetail(ref))}
          />
        ))}
      </Stack>
    </Box>
  );
}

function TripRowCard({
  trip,
  onView,
}: {
  trip: SavedItineraryCardSummary;
  onView: () => void;
}) {
  const [bookingsOpen, setBookingsOpen] = useState(false);
  const bookingsPanelId = `bookings-panel-${trip.id}`;

  const routeLabel =
    trip.origin && trip.destinationLabel
      ? `${trip.origin} → ${trip.destinationLabel}`
      : trip.destinationLabel;

  const totalBookings =
    (trip.linkedBookings?.flightVoyaReferences?.length ?? 0) +
    (trip.linkedBookings?.hotelVoyaReferences?.length ?? 0);

  return (
    <Card
      withBorder
      padding={0}
      radius="md"
      style={{ borderColor: LINE, overflow: 'hidden', width: '100%' }}
    >
      {/* Header: status dot | route */}
      <Box
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 16px',
          background: MIST,
          borderBottom: `1px solid ${LINE}`,
        }}
      >
        <StatusDot confirmed={trip.hasLinkedBookings} />
        {routeLabel && (
          <Text style={{ fontSize: 13, color: MUTED, fontWeight: 500 }}>
            {routeLabel}
          </Text>
        )}
      </Box>

      {/* Body: image (left) | details (right) */}
      <Box
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: 16,
          padding: '16px 20px 14px',
        }}
      >
        {/* Thumbnail */}
        <Box
          style={{
            width: 120,
            height: 88,
            borderRadius: 8,
            overflow: 'hidden',
            flexShrink: 0,
            backgroundColor: MIST,
          }}
        >
          <AuthenticatedImage
            src={trip.heroImageUrl ?? undefined}
            alt=""
            sx={{ width: '100%', height: '100%', objectFit: 'cover' }}
            fallback={<TripImagePlaceholder />}
          />
        </Box>

        {/* Details */}
        <Box style={{ flex: 1, minWidth: 0 }}>
          <Text
            style={{
              fontSize: 18,
              fontWeight: 700,
              color: NAVY,
              lineHeight: '24px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {trip.destinationLabel}
          </Text>
          <Text style={{ fontSize: 14, color: MUTED, marginTop: 2 }}>
            {trip.dateRangeLabel}
          </Text>
          <Box style={{ display: 'flex', gap: 6, marginTop: 5, flexWrap: 'wrap' }}>
            <Text style={{ fontSize: 13, color: NAVY, fontWeight: 500 }}>
              {trip.nightsLabel}
            </Text>
            {trip.passengersLabel && trip.passengersLabel !== '—' && (
              <>
                <Text style={{ fontSize: 13, color: MUTED }}>·</Text>
                <Text style={{ fontSize: 13, color: NAVY, fontWeight: 500 }}>
                  {trip.passengersLabel}
                </Text>
              </>
            )}
          </Box>
        </Box>
      </Box>

      <Divider color={LINE} />

      {/* Footer */}
      <Box
        style={{
          padding: '10px 16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: trip.hasLinkedBookings ? 'space-between' : 'flex-end',
        }}
      >
        {trip.hasLinkedBookings && totalBookings > 0 && (
          <UnstyledButton
            onClick={() => setBookingsOpen((o) => !o)}
            aria-expanded={bookingsOpen}
            aria-controls={bookingsPanelId}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 5,
              fontSize: 13,
              fontWeight: 600,
              color: NAVY,
              cursor: 'pointer',
              background: 'transparent',
            }}
          >
            {bookingsOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            {totalBookings === 1 ? '1 booking' : `${totalBookings} bookings`}
          </UnstyledButton>
        )}
        <UnstyledButton
          onClick={onView}
          style={{
            fontSize: 14,
            fontWeight: 700,
            color: NAVY,
            cursor: 'pointer',
            background: 'transparent',
            textDecoration: 'none',
          }}
        >
          View itinerary →
        </UnstyledButton>
      </Box>

      {/* Expandable bookings panel */}
      {trip.hasLinkedBookings && trip.linkedBookings && (
        <Collapse in={bookingsOpen}>
          <Box id={bookingsPanelId} role="region" aria-label={`Linked bookings for ${trip.destinationLabel}`}>
            <Divider color={LINE} />
            <BookingsPanel
              itineraryId={trip.id}
              linkedBookings={trip.linkedBookings}
            />
          </Box>
        </Collapse>
      )}
    </Card>
  );
}

export function UpcomingTripsSection({
  trips,
  isLoading = false,
  isError = false,
  onRetry,
}: UpcomingTripsSectionProps) {
  const navigate = useNavigate();
  const count = trips.length;

  return (
    <Stack gap="lg">
      <Box>
        <Text
          style={{
            fontFamily: LANDING_TOKENS.fontFamily.display,
            fontWeight: 700,
            fontSize: 28,
            lineHeight: '36px',
            color: LANDING_TOKENS.textColor,
            marginBottom: 8,
          }}
        >
          Trips
        </Text>
        <Text style={{ fontSize: 13, color: MUTED, lineHeight: 1.6 }}>
          Itineraries you've generated with Voya.
        </Text>
      </Box>

      {isLoading && (
        <Group justify="center" py="lg">
          <Loader size={32} color={NAVY} />
        </Group>
      )}

      {!isLoading && isError && (
        <Stack gap="xs">
          <Alert color="yellow">Could not load saved itineraries. Try again later.</Alert>
          {onRetry && (
            <Button variant="outline" size="xs" tt="none" onClick={onRetry}>
              Retry
            </Button>
          )}
        </Stack>
      )}

      {!isLoading && !isError && count === 0 && (
        <Box
          style={{
            background: 'white',
            borderRadius: 14,
            border: `1px solid ${LINE}`,
            padding: '32px 24px',
            textAlign: 'center',
          }}
        >
          <MapIcon size={36} color={MUTED} style={{ marginBottom: 12 }} />
          <Text style={{ fontSize: 15, color: MUTED, lineHeight: 1.6 }}>
            No trips yet. Generate an itinerary in chat to see it here.
          </Text>
        </Box>
      )}

      {!isLoading && !isError && count > 0 && (
        <Stack gap="md">
          {trips.map((trip) => (
            <TripRowCard
              key={trip.id}
              trip={trip}
              onView={() => navigate(itinerarySavedView(trip.id))}
            />
          ))}
        </Stack>
      )}
    </Stack>
  );
}

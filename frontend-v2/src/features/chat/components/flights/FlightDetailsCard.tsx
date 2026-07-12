import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Notification } from '@mantine/core';
import { zIndex } from '@/theme';
import { FlightCard } from '@/features/flights/components/FlightCard';
import { useRevalidateFlightMutation } from '@/api/flightsApi';
import { useAppDispatch } from '@/store/hooks';
import { clearActiveSavedItineraryIdForBooking } from '@/store/slices/uiSlice';
import { usePublicChatConversionGate } from '@/features/chat/hooks/usePublicChatConversionGate';
import type { MappedFlight, FlightLeg, SegmentData } from '@/types/flight';
import type { FlightCardProps } from '@/features/flights/components/FlightCard';
import type { FlightSearchParams } from '@/types/flight';
import type { SelectedFlightDataFromSearch } from '@/types/flightBackend';

interface FlightDetailsCardProps {
  flight: MappedFlight;
  searchParams?: Pick<FlightSearchParams, 'passengers' | 'adults' | 'children' | 'infants'>;
  /** Curated category label to show as a badge (e.g. "Best Value", "Cheapest", "Fastest") */
  categoryLabel?: string;
}

function buildSelectedFlightDataFromChat(
  flight: MappedFlight,
  searchParams?: Pick<FlightSearchParams, 'passengers' | 'adults' | 'children' | 'infants'>
): SelectedFlightDataFromSearch {
  const flightNumber =
    flight.segments?.[0]?.flight_number || flight.outbound?.layovers?.[0]?.flight_number || '';
  const airlineName = flight.airline_names?.[0] || 'Flight';
  const adults = searchParams?.passengers?.adults ?? searchParams?.adults ?? 1;
  const children = searchParams?.passengers?.children ?? searchParams?.children ?? 0;
  const infants = searchParams?.passengers?.infants ?? searchParams?.infants ?? 0;
  const totalPassengers = adults + children + infants || 1;
  return {
    id: flight.id ?? '',
    aircraftName: airlineName,
    flightNumber,
    tags: [],
    passengers: totalPassengers,
    passengerCounts: { adults, children, infants },
    legs: [],
    price: flight.price ?? 0,
  };
}

function segmentDataToFlightLeg(seg: SegmentData, flight: MappedFlight): FlightLeg {
  const stops = seg.stops;
  const firstLayover = seg.layovers[0];
  const stopsText =
    stops === 0
      ? 'Non-stop'
      : firstLayover?.destination_code
        ? `${stops} stop (${firstLayover.destination_code})`
        : `${stops} stop${stops > 1 ? 's' : ''}`;

  const airlinesInfo: FlightLeg['airlinesInfo'] = flight.airline_code
    ? [
        {
          name: flight.airline ?? flight.airline_code,
          code: flight.airline_code,
          flights: flight.flight_number ? [flight.flight_number] : [],
          logoUrl: flight.logo_url,
        },
      ]
    : undefined;

  return {
    departure: {
      city: seg.origin_city ?? seg.origin_code ?? '',
      airport: seg.origin_code ?? '',
      date: seg.departure_date ?? '',
      time: seg.departure_time ?? '',
    },
    arrival: {
      city: seg.destination_city ?? seg.destination_code ?? '',
      airport: seg.destination_code ?? '',
      date: seg.arrival_date ?? '',
      time: seg.arrival_time ?? '',
    },
    duration: seg.flight_duration ?? seg.duration,
    totalTimeDisplay: seg.layovers.length > 0 ? seg.duration : null,
    stops,
    stopsText,
    airlinesInfo,
  };
}

function mappedFlightToFlightCardFlight(
  flight: MappedFlight,
  searchParams?: Pick<FlightSearchParams, 'passengers' | 'adults' | 'children' | 'infants'>,
  categoryLabel?: string
): FlightCardProps['flight'] {
  const adults = searchParams?.passengers?.adults ?? searchParams?.adults ?? 1;
  const children = searchParams?.passengers?.children ?? searchParams?.children ?? 0;
  const infants = searchParams?.passengers?.infants ?? searchParams?.infants ?? 0;
  const passengers = adults + children + infants || 1;

  const legs: FlightLeg[] = [segmentDataToFlightLeg(flight.outbound, flight)];
  if (flight.is_round_trip && flight.return) {
    legs.push(segmentDataToFlightLeg(flight.return, flight));
  }

  return {
    id: flight.id ?? '',
    aircraftName: flight.airline ?? '',
    flightNumber: flight.flight_number,
    journeyType: flight.is_round_trip ? 'Return' : 'OneWay',
    tags: categoryLabel ? [categoryLabel] : [],
    passengers,
    legs,
    // MappedFlight.price is the total fare; FlightCard.price is per-person
    price: (flight.price ?? 0) / passengers,
    original_total_fare: flight.original_total_fare,
    platform_fee_percentage: flight.platform_fee_percentage,
  };
}

export function FlightDetailsCard({ flight, searchParams, categoryLabel }: FlightDetailsCardProps) {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const [isLoading, setIsLoading] = useState(false);
  const { ensureAuthenticated } = usePublicChatConversionGate();
  const [error, setError] = useState({ open: false, message: '' });
  const [revalidateFlight] = useRevalidateFlightMutation();

  const handleImmediateBooking = async () => {
    if (!ensureAuthenticated('flight_book_now')) return;
    dispatch(clearActiveSavedItineraryIdForBooking());
    if (!flight.id) {
      setError({ open: true, message: 'Flight ID is missing' });
      return;
    }

    const sessionId = localStorage.getItem('sessionId') ?? '';
    if (!sessionId) {
      setError({ open: true, message: 'Search session expired. Please run a new flight search.' });
      return;
    }

    setIsLoading(true);
    try {
      const adults = searchParams?.passengers?.adults ?? searchParams?.adults ?? 1;
      const children = searchParams?.passengers?.children ?? searchParams?.children ?? 0;
      const infants = searchParams?.passengers?.infants ?? searchParams?.infants ?? 0;

      const revalidateResponse = await revalidateFlight({
        sessionId,
        fareSourceCode: flight.id,
        adults,
        children,
        infants,
      }).unwrap();

      if (revalidateResponse.isFareAvailable === false) {
        setError({
          open: true,
          message: 'This fare is no longer available or the price has changed. Please search again.',
        });
        return;
      }

      const selectedFlightData = buildSelectedFlightDataFromChat(flight, searchParams);
      const encodedFareSourceCode = encodeURIComponent(flight.id);
      navigate(`/flights/details/${encodedFareSourceCode}`, {
        state: {
          revalidateResponse,
          selectedFlightData,
          searchSessionId: sessionId,
        },
      });
    } catch (err) {
      console.error('Error revalidating flight:', err);
      const errorMessage =
        (err as { data?: { detail?: string }; status?: number })?.data?.detail ||
        ((err as { status?: number })?.status === 410
          ? 'This fare is no longer available. Please search again.'
          : 'Unable to book this flight. Please try again.');
      setError({ open: true, message: errorMessage });
    } finally {
      setIsLoading(false);
    }
  };

  const flightCardFlight = mappedFlightToFlightCardFlight(flight, searchParams, categoryLabel);

  return (
    <>
      {error.open && (
        <Notification
          color="red"
          title="Error"
          onClose={() => setError({ open: false, message: '' })}
          withCloseButton
          style={{
            position: 'fixed',
            top: 16,
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: zIndex.detailModal,
            maxWidth: 480,
          }}
        >
          {error.message}
        </Notification>
      )}
      <FlightCard
        flight={flightCardFlight}
        onSelect={() => { void handleImmediateBooking(); }}
        isSelecting={isLoading}
      />
    </>
  );
}

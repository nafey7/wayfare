import { useState, useEffect, useRef } from 'react';
import {
  Box,
  Button,
  Group,
  NumberInput,
  Stack,
  Text,
  Title,
  Alert,
} from '@mantine/core';
import { DatePickerInput } from '@mantine/dates';
import { Calendar, Users, AlertCircle, Map } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '@/store';
import { selectTripMeta, setLastItineraryState, setLastItineraryPath } from '@/store/slices/uiSlice';
import { selectSearchFormParams } from '@/store/slices/flightBookingSlice';
import { selectChatId } from '@/store/slices/chatSlice';
import { useGenerateItineraryMutation, type GenerateItineraryResult } from '@/api/itinerariesApi';
import {
  CitySearchAutocomplete,
  type CitySearchOption,
} from '@/features/onboarding/components/CitySearchAutocomplete';
import { tripCityOptionFromStored } from '@/features/onboarding/openMeteoGeocoding';
import { itineraryView } from '@/features/routing';

const NAVY = '#171B63';

function parseIsoDate(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  const d = new Date(iso);
  return isNaN(d.getTime()) ? null : d;
}

export function ItineraryPlannerForm() {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const [generateItinerary, { isLoading }] = useGenerateItineraryMutation();

  const chatId = useAppSelector(selectChatId);
  const tripMeta = useAppSelector(selectTripMeta);
  const flightParams = useAppSelector(selectSearchFormParams);

  const [origin, setOrigin] = useState<CitySearchOption | null>(null);
  const [destination, setDestination] = useState<CitySearchOption | null>(null);
  const [departureDate, setDepartureDate] = useState<Date | null>(null);
  const [returnDate, setReturnDate] = useState<Date | null>(null);
  const [adults, setAdults] = useState<number | string>(2);
  const [error, setError] = useState<string | null>(null);

  // Prevent tripMeta updates from overwriting user edits after first init.
  const hasInitialized = useRef(false);

  useEffect(() => {
    if (hasInitialized.current) return;
    const dest = tripMeta?.destination ?? '';
    const dep = parseIsoDate(tripMeta?.departure_date);
    const ret = parseIsoDate(tripMeta?.return_date);
    const adultCount = tripMeta?.adults ?? 2;
    const from = tripMeta?.origin ?? flightParams?.from ?? '';
    if (dest || dep || from) {
      setDestination(tripCityOptionFromStored(dest));
      setDepartureDate(dep);
      setReturnDate(ret);
      setAdults(adultCount);
      setOrigin(tripCityOptionFromStored(from));
      hasInitialized.current = true;
    }
  }, [tripMeta, flightParams?.from]);

  const formatDate = (d: Date | null) =>
    d ? d.toISOString().slice(0, 10) : undefined;

  const destinationText = destination?.displayLine?.trim() ?? '';
  const originText = origin?.displayLine?.trim() ?? '';
  const isValid = destinationText.length > 0 && departureDate !== null;

  const handleCreate = async () => {
    if (!isValid) {
      setError('Please enter a destination and departure date.');
      return;
    }
    setError(null);
    try {
      const result: GenerateItineraryResult = await generateItinerary({
        destination: destinationText,
        origin: originText || undefined,
        departureDate: formatDate(departureDate),
        returnDate: formatDate(returnDate),
        adults: typeof adults === 'number' ? adults : 1,
      }).unwrap();

      // When no chatId (unauthenticated / no active chat), scope under the
      // savedItineraryId to avoid the shared __anon__ bucket problem.
      const resolvedChatId = chatId ?? `saved:${result.savedItineraryId}`;
      const targetPath = itineraryView(result.savedItineraryId);

      dispatch(setLastItineraryState({
        chatId: resolvedChatId,
        state: {
          structuredItinerary: result.structuredItinerary,
          tripMeta: result.tripMeta as Record<string, unknown>,
          savedItineraryId: result.savedItineraryId,
        },
      }));
      dispatch(setLastItineraryPath({ chatId: resolvedChatId, path: targetPath }));

      navigate(targetPath);
    } catch (err: unknown) {
      const detail =
        (err as { data?: { detail?: string } })?.data?.detail ??
        'Generation failed — please try again.';
      setError(detail);
    }
  };

  const inputStyles = {
    label: { color: '#444', fontWeight: 600 as const, fontSize: 13, marginBottom: 4 },
    input: { borderColor: 'rgba(23,27,99,0.18)', fontSize: 14 },
  };

  return (
    <Box
      style={{
        background: 'white',
        borderRadius: 20,
        border: '1.5px solid rgba(23, 27, 99, 0.12)',
        padding: '32px 36px 36px',
        maxWidth: 660,
        width: '100%',
        boxShadow: '0 4px 24px rgba(23, 27, 99, 0.08)',
      }}
    >
      {/* Header */}
      <Group gap="sm" mb={4}>
        <Box
          style={{
            width: 38,
            height: 38,
            borderRadius: 10,
            background: 'rgba(23, 27, 99, 0.06)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <Map size={18} color={NAVY} />
        </Box>
        <Stack gap={2}>
          <Title order={3} fw={700} style={{ color: NAVY, lineHeight: 1.2 }}>
            Plan a trip
          </Title>
          <Text size="xs" c="dimmed">
            We'll build a full day-by-day itinerary — no chat needed.
          </Text>
        </Stack>
      </Group>

      <Box
        style={{
          height: 1,
          background: 'rgba(23, 27, 99, 0.08)',
          margin: '16px 0 20px',
        }}
      />

      {error && (
        <Alert icon={<AlertCircle size={15} />} color="red" mb="md" radius="md" py="xs">
          {error}
        </Alert>
      )}

      <Stack gap="md">
        {/* Row 1: From / To */}
        <Group gap="md" grow align="flex-start">
          <CitySearchAutocomplete
            label="Flying from"
            placeholder="Paris, New York…"
            value={origin}
            onChange={setOrigin}
          />
          <CitySearchAutocomplete
            label="Destination *"
            placeholder="London, Tokyo…"
            value={destination}
            onChange={setDestination}
          />
        </Group>

        {/* Row 2: Dates */}
        <Group gap="md" grow>
          <DatePickerInput
            label={<span>Departure <span style={{ color: 'tomato' }}>*</span></span>}
            placeholder="Pick a date"
            value={departureDate}
            onChange={setDepartureDate}
            leftSection={<Calendar size={15} color={NAVY} />}
            radius="md"
            minDate={new Date()}
            clearable
            styles={inputStyles}
          />
          <DatePickerInput
            label="Return"
            placeholder="Optional"
            value={returnDate}
            onChange={setReturnDate}
            leftSection={<Calendar size={15} color={NAVY} />}
            radius="md"
            minDate={departureDate ?? new Date()}
            clearable
            styles={inputStyles}
          />
        </Group>

        {/* Row 3: Adults + Button */}
        <Group gap="md" align="flex-end">
          <NumberInput
            label="Adults"
            value={adults}
            onChange={setAdults}
            min={1}
            max={9}
            leftSection={<Users size={15} color={NAVY} />}
            radius="md"
            style={{ width: 130 }}
            styles={inputStyles}
          />
          <Button
            onClick={() => void handleCreate()}
            loading={isLoading}
            radius="md"
            size="md"
            style={{
              flex: 1,
              background: isValid ? NAVY : undefined,
              fontWeight: 600,
            }}
            disabled={!isValid}
          >
            {isLoading ? 'Creating…' : 'Create itinerary'}
          </Button>
        </Group>
      </Stack>
    </Box>
  );
}

import { useMemo, useRef } from 'react';
import { ActionIcon, Box, Button, Group, Stack, Text } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { DatePickerInput } from '@mantine/dates';
import {
  ArrowLeftRight,
  Calendar,
  PlaneLanding,
  PlaneTakeoff,
  Plus,
  Trash2,
} from 'lucide-react';
import { AirportAutocomplete } from './AirportAutocomplete';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import {
  selectSearchFormParams,
  setMultiCitySegments,
  updateMultiCitySegment,
  type SerializableAirportOption,
  type SerializableFlightSegment,
} from '@/store/slices/flightBookingSlice';
import { today } from '@/utils/dates';

const ICON_COLOR = 'var(--mantine-color-brand-2)';
const FromIcon = () => <PlaneTakeoff size={18} color={ICON_COLOR} />;
const ToIcon = () => <PlaneLanding size={18} color={ICON_COLOR} />;
const DateIcon = () => <Calendar size={18} color={ICON_COLOR} />;

const FIELD_LABEL_PROPS = {
  size: 'xs' as const,
  c: 'dimmed',
  display: 'block' as const,
  mb: 4,
};

export interface MulticityRouteEditorProps {
  /** Label for the primary action button (default "Done"). */
  doneLabel?: string;
  /** Called when the user clicks the primary action button. */
  onDone: () => void;
  /** Show the intro hint text above the legs. */
  showHint?: boolean;
}

export function MulticityRouteEditor({
  doneLabel = 'Done',
  onDone,
  showHint = true,
}: MulticityRouteEditorProps) {
  const isMobile = useMediaQuery('(max-width: 768px)') ?? false;
  const dispatch = useAppDispatch();
  const searchFormParams = useAppSelector(selectSearchFormParams);
  const segments = searchFormParams.segments;

  const multiCitySegments = useMemo<SerializableFlightSegment[]>(() => {
    if (!segments?.length) return [];
    return segments.map((s) => ({
      from: s.from,
      to: s.to,
      date: s.date,
      fromAirport: s.fromAirport,
      toAirport: s.toAirport,
    }));
  }, [segments]);

  // Stable per-leg ids so React reconciles rows by identity, not list index.
  // Otherwise deleting a leg mid-list shifts subsequent rows up by one index,
  // and tree state (focus, popover-open, DatePicker internal state) leaks from
  // the removed row to the row that takes its place.
  const legIdSeqRef = useRef(0);
  const legIdsRef = useRef<string[]>([]);
  if (legIdsRef.current.length !== multiCitySegments.length) {
    if (multiCitySegments.length > legIdsRef.current.length) {
      const toAdd = multiCitySegments.length - legIdsRef.current.length;
      for (let i = 0; i < toAdd; i++) {
        legIdsRef.current.push(`leg-${legIdSeqRef.current++}`);
      }
    } else {
      legIdsRef.current = legIdsRef.current.slice(0, multiCitySegments.length);
    }
  }

  const handleAddLeg = () => {
    legIdsRef.current.push(`leg-${legIdSeqRef.current++}`);
    dispatch(setMultiCitySegments([...multiCitySegments, { from: '', to: '', date: null }]));
  };

  const handleDeleteLeg = (index: number) => {
    if (multiCitySegments.length <= 2) return;
    legIdsRef.current.splice(index, 1);
    dispatch(setMultiCitySegments(multiCitySegments.filter((_, i) => i !== index)));
  };

  const handleSegmentSwap = (index: number) => {
    const seg = multiCitySegments[index];
    if (!seg) return;
    dispatch(
      updateMultiCitySegment({
        index,
        segment: {
          from: seg.to,
          to: seg.from,
          date: seg.date,
          fromAirport: seg.toAirport,
          toAirport: seg.fromAirport,
        },
      }),
    );
  };

  const updateSegmentField = (index: number, patch: Partial<SerializableFlightSegment>) => {
    const seg = multiCitySegments[index];
    if (!seg) return;
    dispatch(updateMultiCitySegment({ index, segment: { ...seg, ...patch } }));
  };

  return (
    <Stack gap="md">
      {showHint && (
        <Text size="sm" c="dimmed">
          Add at least two legs. Each leg needs origin, destination, and departure date.
        </Text>
      )}
      {multiCitySegments.map((segment, index) => (
        <Group
          key={legIdsRef.current[index] ?? `leg-fallback-${index}`}
          gap="sm"
          wrap="wrap"
          align={isMobile ? 'stretch' : 'flex-end'}
          style={{ flexDirection: isMobile ? 'column' : 'row' }}
        >
          <Box style={{ flex: isMobile ? 1 : '1 1 160px', minWidth: 0 }}>
            <Text {...FIELD_LABEL_PROPS}>From</Text>
            <AirportAutocomplete
              value={segment.from}
              onChange={(value, airport) => {
                const serializable: SerializableAirportOption | undefined = airport
                  ? {
                      iata: airport.iata,
                      name: airport.name,
                      city: airport.city,
                      state: airport.state,
                      country: airport.country,
                      isCityOption: airport.isCityOption,
                    }
                  : undefined;
                updateSegmentField(index, { from: value, fromAirport: serializable });
              }}
              placeholder="City or airport"
              size="small"
              startAdornment={<FromIcon />}
              fullWidth
            />
          </Box>

          <ActionIcon
            size="md"
            variant="subtle"
            onClick={() => handleSegmentSwap(index)}
            aria-label="Swap origin and destination for this leg"
            style={{ alignSelf: isMobile ? 'center' : 'flex-end', marginBottom: isMobile ? 0 : 4 }}
          >
            <ArrowLeftRight size={18} />
          </ActionIcon>

          <Box style={{ flex: isMobile ? 1 : '1 1 160px', minWidth: 0 }}>
            <Text {...FIELD_LABEL_PROPS}>To</Text>
            <AirportAutocomplete
              value={segment.to}
              onChange={(value, airport) => {
                const serializable: SerializableAirportOption | undefined = airport
                  ? {
                      iata: airport.iata,
                      name: airport.name,
                      city: airport.city,
                      state: airport.state,
                      country: airport.country,
                      isCityOption: airport.isCityOption,
                    }
                  : undefined;
                updateSegmentField(index, { to: value, toAirport: serializable });
              }}
              placeholder="City or airport"
              size="small"
              startAdornment={<ToIcon />}
              fullWidth
            />
          </Box>

          <Box style={{ flex: isMobile ? 1 : '0 0 150px', minWidth: 0 }}>
            <Text {...FIELD_LABEL_PROPS}>Depart</Text>
            <DatePickerInput
              value={segment.date ? new Date(segment.date) : null}
              minDate={
                index === 0
                  ? today()
                  : multiCitySegments[index - 1]?.date
                    ? new Date(multiCitySegments[index - 1]!.date!)
                    : today()
              }
              onChange={(newDate) => {
                const d = newDate ?? null;
                updateSegmentField(index, d ? { date: d.toISOString() } : { date: null });
              }}
              leftSection={<DateIcon />}
              size="sm"
              placeholder="Pick a date"
              w="100%"
              popoverProps={{ withinPortal: true, zIndex: 1400 }}
            />
          </Box>

          <ActionIcon
            size="md"
            variant="subtle"
            color="red"
            onClick={() => handleDeleteLeg(index)}
            disabled={multiCitySegments.length <= 2}
            aria-label="Remove leg"
            style={{ alignSelf: isMobile ? 'center' : 'flex-end', marginBottom: isMobile ? 0 : 4 }}
          >
            <Trash2 size={18} />
          </ActionIcon>
        </Group>
      ))}

      <Button
        variant="default"
        leftSection={<Plus size={16} />}
        onClick={handleAddLeg}
        style={{ alignSelf: 'flex-start' }}
      >
        Add another leg
      </Button>
      <Button variant="filled" onClick={onDone} style={{ alignSelf: 'flex-start' }} mt={4}>
        {doneLabel}
      </Button>
    </Stack>
  );
}

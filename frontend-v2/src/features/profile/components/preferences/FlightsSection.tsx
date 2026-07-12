import { ActionIcon, Autocomplete, Box, Group, RangeSlider, Stack, Text, UnstyledButton } from '@mantine/core';
import { Plus, Search, X } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { LANDING_TOKENS } from '@/features/landing/landingTokens';
import {
  RadioField,
  SectionHeader,
  chipBaseStyle,
} from './PreferenceFieldComponents';
import type { PreferenceOption } from '@/features/profile/types/preferences';
import type { FlightsPreferences } from '@/types/profile';

const SEAT_OPTIONS: PreferenceOption<string>[] = [
  { id: 'window', label: 'Window', value: 'window' },
  { id: 'aisle', label: 'Aisle', value: 'aisle' },
  { id: 'noPreference', label: 'No Preference', value: 'noPreference' },
];

const MAX_STOPS_OPTIONS: PreferenceOption<string>[] = [
  { id: 'nonstop', label: 'Non-stop', value: 'nonstop' },
  { id: '1stop', label: '1 Stop', value: '1stop' },
  { id: '2stops', label: '2+ Stops', value: '2stops' },
  { id: 'any', label: 'Any', value: 'any' },
];

/** Common airline names for autocomplete suggestions */
const AIRLINE_OPTIONS = [
  'Aer Lingus',
  'Aeroflot',
  'Aeromexico',
  'Air Canada',
  'Air France',
  'Air India',
  'Alaska Airlines',
  'American Airlines',
  'Avianca',
  'British Airways',
  'Cathay Pacific',
  'Delta Airlines',
  'Emirates',
  'Etihad Airways',
  'Japan Airlines',
  'JetBlue',
  'KLM',
  'Lufthansa',
  'Qantas',
  'Qatar Airways',
  'Singapore Airlines',
  'Southwest Airlines',
  'Swiss International',
  'Turkish Airlines',
  'United Airlines',
  'Virgin Atlantic',
  'WestJet',
];

function AddAirlineInput({
  value,
  onChange,
  onAdd,
  onCancel,
  selectedAirlines,
  inputRef,
}: {
  value: string;
  onChange: (v: string) => void;
  onAdd: (airline: string) => void;
  onCancel: () => void;
  selectedAirlines: string[];
  inputRef: React.RefObject<HTMLInputElement | null>;
}) {
  const options = AIRLINE_OPTIONS.filter((a) => !selectedAirlines.includes(a));
  // Tracks "the user just picked an option" — `onOptionSubmit` fires before
  // `onBlur` and React state hasn't flushed yet, so a naive `onBlur` would
  // double-add the partially-typed `value` over the selected option.
  const justSelectedRef = useRef(false);

  return (
    <Box
      style={{
        display: 'inline-flex',
        minHeight: 32,
        height: 32,
        borderRadius: 8,
        border: `2px solid ${LANDING_TOKENS.baseColor}`,
        backgroundColor: LANDING_TOKENS.baseColor10,
        overflow: 'visible',
      }}
    >
      <Autocomplete
        ref={inputRef as React.Ref<HTMLInputElement>}
        data={options}
        value={value}
        onChange={(v) => onChange(v)}
        onOptionSubmit={(v) => {
          justSelectedRef.current = true;
          if (v.trim()) onAdd(v.trim());
        }}
        onBlur={() => {
          if (justSelectedRef.current) {
            justSelectedRef.current = false;
            return;
          }
          if (value.trim()) onAdd(value.trim());
          else onCancel();
        }}
        onKeyDown={(e) => {
          if (e.key === 'Escape') {
            e.preventDefault();
            onCancel();
          } else if (e.key === 'Enter' && value.trim()) {
            e.preventDefault();
            onAdd(value.trim());
          }
        }}
        placeholder="Type airline name...."
        leftSection={<Search size={18} color="rgba(0,0,0,0.5)" />}
        variant="unstyled"
        styles={{
          input: {
            paddingLeft: 8,
            paddingRight: 12,
            paddingTop: 6,
            paddingBottom: 6,
            minHeight: 0,
            height: '100%',
            fontFamily: LANDING_TOKENS.fontFamily.display,
            fontSize: 16,
            fontWeight: 400,
            color: LANDING_TOKENS.textColor,
          },
          dropdown: {
            marginTop: 8,
            borderRadius: 8,
            boxShadow: LANDING_TOKENS.shadow,
          },
        }}
        style={{ minWidth: 120, flex: 1 }}
      />
    </Box>
  );
}

export interface FlightsSectionProps {
  preferences: FlightsPreferences;
  documentExists: boolean;
  onChange: (prefs: FlightsPreferences) => void;
}

/**
 * Flights subsection — seat preference, max stops, preferred airlines, departure window.
 * Only populates when documentExists; otherwise shows empty state.
 */
export function FlightsSection({
  preferences,
  documentExists,
  onChange,
}: FlightsSectionProps) {
  const seatChoice = documentExists ? (preferences.seatPreference ?? '') : '';
  const maxStopsChoice = documentExists ? (preferences.maxStops ?? '') : '';
  const airlines = preferences.preferredAirlines ?? [];
  const departureWindow = preferences.departureWindow ?? ['00:00', '23:59'];

  /** Convert "HH:mm" to decimal hours for slider (0-24) */
  const timeToHours = (t: string): number => {
    const parts = t.split(':').map(Number);
    const h = parts[0] ?? 0;
    const m = parts[1] ?? 0;
    return h + m / 60;
  };
  /** Convert decimal hours to "HH:mm" */
  const hoursToTime = (h: number): string => {
    const hi = Math.min(23, Math.floor(h));
    const mi = Math.min(59, Math.round((h % 1) * 60));
    return `${hi.toString().padStart(2, '0')}:${mi.toString().padStart(2, '0')}`;
  };
  const departureRange: [number, number] = [
    timeToHours(departureWindow[0]),
    timeToHours(departureWindow[1]),
  ];

  const [sliderValue, setSliderValue] = useState<[number, number]>(departureRange);
  // Destructure for stable referential identity — react-hooks/exhaustive-deps
  // flags array index access in the deps array.
  const [departureStart, departureEnd] = departureWindow;
  useEffect(() => {
    setSliderValue([timeToHours(departureStart), timeToHours(departureEnd)]);
  }, [departureStart, departureEnd]);

  const [addMode, setAddMode] = useState(false);
  const [newAirlineInput, setNewAirlineInput] = useState('');
  const addInputRef = useRef<HTMLInputElement | null>(null);

  const handleSeatChange = useCallback(
    (v: string) => onChange({ ...preferences, seatPreference: v || null }),
    [onChange, preferences]
  );
  const handleMaxStopsChange = useCallback(
    (v: string) => onChange({ ...preferences, maxStops: v || null }),
    [onChange, preferences]
  );
  const handleRemoveAirline = useCallback(
    (airline: string) =>
      onChange({
        ...preferences,
        preferredAirlines: airlines.filter((a) => a !== airline),
      }),
    [onChange, preferences, airlines]
  );

  const handleOpenAdd = useCallback(() => {
    setAddMode(true);
    setNewAirlineInput('');
  }, []);

  useEffect(() => {
    if (addMode) {
      const t = setTimeout(() => addInputRef.current?.focus(), 0);
      return () => clearTimeout(t);
    }
  }, [addMode]);

  const handleAddAirline = useCallback(
    (airline: string) => {
      const trimmed = airline.trim();
      if (trimmed && !airlines.includes(trimmed)) {
        onChange({ ...preferences, preferredAirlines: [...airlines, trimmed] });
      }
      setNewAirlineInput('');
      setAddMode(false);
    },
    [onChange, preferences, airlines]
  );

  const handleCancelAdd = useCallback(() => {
    setNewAirlineInput('');
    setAddMode(false);
  }, []);

  return (
    <Stack gap={24}>
      <RadioField
        label="Seat Preference"
        options={SEAT_OPTIONS}
        value={seatChoice || null}
        onChange={handleSeatChange}
      />
      <RadioField
        label="Max Stops"
        options={MAX_STOPS_OPTIONS}
        value={maxStopsChoice || null}
        onChange={handleMaxStopsChange}
      />

      <Box style={{ display: 'flex', flexDirection: 'column', gap: 8, width: '100%' }}>
        <Box>
          <SectionHeader label="Preferred Airlines" variant="small" />
        </Box>
        <Box style={{ flex: 1, minWidth: 0 }}>
          <Group gap={12} wrap="wrap">
            {airlines.map((airline) => (
              <Box
                key={airline}
                style={{
                  ...chipBaseStyle,
                  backgroundColor: LANDING_TOKENS.baseColor,
                  color: LANDING_TOKENS.textLight,
                  gap: 6,
                  paddingRight: 4,
                }}
              >
                <span>{airline}</span>
                <ActionIcon
                  size="xs"
                  variant="transparent"
                  c={LANDING_TOKENS.textLight}
                  onClick={() => handleRemoveAirline(airline)}
                  aria-label={`Remove ${airline}`}
                >
                  <X size={14} />
                </ActionIcon>
              </Box>
            ))}
            {addMode ? (
              <AddAirlineInput
                value={newAirlineInput}
                onChange={setNewAirlineInput}
                onAdd={handleAddAirline}
                onCancel={handleCancelAdd}
                selectedAirlines={airlines}
                inputRef={addInputRef}
              />
            ) : (
              <UnstyledButton
                onClick={handleOpenAdd}
                style={{
                  ...chipBaseStyle,
                  backgroundColor: LANDING_TOKENS.baseColor10,
                  color: LANDING_TOKENS.textColor,
                  gap: 4,
                }}
              >
                <Plus size={18} />
                Add
              </UnstyledButton>
            )}
          </Group>
        </Box>
      </Box>

      <Box style={{ display: 'flex', flexDirection: 'column', gap: 8, width: '100%' }}>
        <Box>
          <SectionHeader label="Departure Window" variant="small" />
        </Box>
        <Box style={{ flex: 1, minWidth: 0 }}>
          <Box px={12} py={4}>
            <RangeSlider
              value={sliderValue}
              onChange={setSliderValue}
              onChangeEnd={(v) =>
                onChange({
                  ...preferences,
                  departureWindow: [hoursToTime(v[0]), hoursToTime(v[1])],
                })
              }
              label={(v) => hoursToTime(v)}
              min={0}
              max={24}
              step={0.01}
              marks={[
                { value: 0, label: '' },
                { value: 6, label: '' },
                { value: 12, label: '' },
                { value: 18, label: '' },
                { value: 24, label: '' },
              ]}
              color="brand.6"
              styles={{
                root: { maxWidth: 400 },
                bar: { height: 8 },
                track: { height: 8 },
                thumb: { width: 16, height: 16 },
                mark: { width: 4, height: 4, borderRadius: '50%' },
              }}
            />
            <Group
              justify="space-between"
              px={4}
              mt="xs"
              style={{ fontFamily: LANDING_TOKENS.fontFamily.display }}
            >
              <Text
                component="span"
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  lineHeight: 1.33,
                  letterSpacing: 0.1,
                  color: LANDING_TOKENS.textColor,
                  fontFamily: LANDING_TOKENS.fontFamily.display,
                }}
              >
                {hoursToTime(sliderValue[0])}
              </Text>
              <Text
                component="span"
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  lineHeight: 1.33,
                  letterSpacing: 0.1,
                  color: LANDING_TOKENS.textColor,
                  fontFamily: LANDING_TOKENS.fontFamily.display,
                }}
              >
                {hoursToTime(sliderValue[1])}
              </Text>
            </Group>
          </Box>
        </Box>
      </Box>
    </Stack>
  );
}

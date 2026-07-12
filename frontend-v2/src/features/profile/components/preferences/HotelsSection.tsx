import { Box, Group, Stack, UnstyledButton } from '@mantine/core';
import { LANDING_TOKENS } from '@/features/landing/landingTokens';
import {
  ChipSection,
  RadioField,
  SectionHeader,
  chipBaseStyle,
} from './PreferenceFieldComponents';
import type { PreferenceOption } from '@/features/profile/types/preferences';
import type { HotelsPreferences } from '@/types/profile';


const BED_TYPE_OPTIONS: PreferenceOption<string>[] = [
  { id: 'king', label: 'King', value: 'king' },
  { id: 'twin', label: 'Twin', value: 'twin' },
  { id: 'queen', label: 'Queen', value: 'queen' },
  { id: 'noPreference', label: 'No preference', value: 'noPreference' },
];

const ROOM_TYPE_OPTIONS: PreferenceOption<string>[] = [
  { id: 'hotel', label: 'Hotel', value: 'hotel' },
  { id: 'apartment', label: 'Apartment', value: 'apartment' },
];

const AMENITIES_OPTIONS: PreferenceOption<string>[] = [
  { id: 'breakfast', label: 'Breakfast included', value: 'breakfast' },
  { id: 'gym', label: 'Gym', value: 'gym' },
  { id: 'spa', label: 'Spa', value: 'spa' },
  { id: 'pool', label: 'Pool', value: 'pool' },
  { id: 'workspace', label: 'Workspace desk', value: 'workspace' },
  { id: 'familyFriendly', label: 'Family-friendly', value: 'familyFriendly' },
  { id: 'petFriendly', label: 'Pet-friendly', value: 'petFriendly' },
  { id: 'airportShuttle', label: 'Airport shuttle', value: 'airportShuttle' },
];

const HOTEL_STYLE_OPTIONS: PreferenceOption<string>[] = [
  { id: 'modern', label: 'Modern', value: 'modern' },
  { id: 'classic', label: 'Classic', value: 'classic' },
  { id: 'designForward', label: 'Design-forward', value: 'designForward' },
  { id: 'traditional', label: 'Traditional', value: 'traditional' },
  { id: 'ecoConscious', label: 'Eco-conscious', value: 'ecoConscious' },
  { id: 'minimalist', label: 'Minimalist', value: 'minimalist' },
  { id: 'industrial', label: 'Industrial', value: 'industrial' },
  { id: 'artisanal', label: 'Artisanal', value: 'artisanal' },
];

const LOCATION_OPTIONS: PreferenceOption<string>[] = [
  { id: 'cityCenter', label: 'City center', value: 'cityCenter' },
  { id: 'nearTransport', label: 'Near public transport', value: 'nearTransport' },
  { id: 'quietNeighborhood', label: 'Quiet neighborhood', value: 'quietNeighborhood' },
  { id: 'closeToAttractions', label: 'Close to attractions', value: 'closeToAttractions' },
  { id: 'waterfront', label: 'Waterfront', value: 'waterfront' },
];

const CANCELLATION_OPTIONS: PreferenceOption<string>[] = [
  { id: 'refundable', label: 'Refundable', value: 'refundable' },
  { id: 'nonRefundable', label: 'Non-Refundable', value: 'nonrefundable' },
];

export interface HotelsSectionProps {
  preferences: HotelsPreferences;
  documentExists: boolean;
  onChange: (prefs: HotelsPreferences) => void;
}

/**
 * Hotels subsection — bed type, property type (Hotel/Apartment), amenities,
 * hotel style, location preference, and cancellation flexibility.
 * Only populates when documentExists; otherwise shows empty state.
 */
export function HotelsSection({
  preferences,
  documentExists,
  onChange,
}: HotelsSectionProps) {
  const bedType = documentExists ? (preferences.bedType ?? '') : '';
  const roomType = documentExists ? (preferences.roomType ?? '') : '';
  const amenities = new Set(preferences.amenities ?? []);
  const hotelStyle = new Set(preferences.hotelStyle ?? []);
  const locationPreference = new Set(preferences.locationPreference ?? []);
  const cancellation = new Set(preferences.cancellation ?? []);

  const toggleMulti = (
    field: 'amenities' | 'hotelStyle' | 'locationPreference' | 'cancellation',
    value: string,
    singleSelect?: boolean
  ) => {
    const arr = (preferences[field] ?? []) as string[];
    const next = new Set(arr);
    if (singleSelect) {
      const current = (preferences[field] ?? []) as string[];
      onChange({ ...preferences, [field]: current.includes(value) ? [] : [value] });
      return;
    }
    if (next.has(value)) next.delete(value);
    else next.add(value);
    onChange({ ...preferences, [field]: Array.from(next) });
  };

  const renderChip = (selected: boolean, label: string, onClick: () => void) => (
    <UnstyledButton
      onClick={onClick}
      style={{
        ...chipBaseStyle,
        ...(selected
          ? {
              backgroundColor: LANDING_TOKENS.baseColor,
              color: LANDING_TOKENS.textLight,
            }
          : {
              border: '1px solid var(--mantine-color-default-border)',
              color: LANDING_TOKENS.textHighlight,
              backgroundColor: 'transparent',
            }),
      }}
    >
      {label}
    </UnstyledButton>
  );

  return (
    <Stack gap={24}>
      <RadioField
        label="Bed Type"
        options={BED_TYPE_OPTIONS}
        value={bedType || null}
        onChange={(v) => onChange({ ...preferences, bedType: v || null })}
      />
      <RadioField
        label="Room Type"
        options={ROOM_TYPE_OPTIONS}
        value={roomType || null}
        onChange={(v) => onChange({ ...preferences, roomType: v || null })}
      />

      <Box style={{ display: 'flex', flexDirection: 'column', gap: 8, width: '100%' }}>
        <Box>
          <SectionHeader label="Amenities" variant="small" />
        </Box>
        <Group gap={12} wrap="wrap">
          {AMENITIES_OPTIONS.map((opt) =>
            renderChip(amenities.has(opt.value), opt.label, () => toggleMulti('amenities', opt.value)),
          )}
        </Group>
      </Box>

      <ChipSection
        label="Hotel Style"
        options={HOTEL_STYLE_OPTIONS}
        selectedValues={hotelStyle}
        onToggle={(value) => toggleMulti('hotelStyle', value)}
      />
      <ChipSection
        label="Location preference"
        options={LOCATION_OPTIONS}
        selectedValues={locationPreference}
        onToggle={(value) => toggleMulti('locationPreference', value)}
      />

      <Box style={{ display: 'flex', flexDirection: 'column', gap: 8, width: '100%' }}>
        <Box>
          <SectionHeader label="Cancellation flexibility" variant="small" />
        </Box>
        <Group gap={12} wrap="wrap">
          {CANCELLATION_OPTIONS.map((opt) =>
            renderChip(cancellation.has(opt.value), opt.label, () =>
              toggleMulti('cancellation', opt.value, true),
            ))}
        </Group>
      </Box>
    </Stack>
  );
}

import { useState } from 'react';
import { ActionIcon, Box, Button, Group } from '@mantine/core';
import { Minus, Plus } from 'lucide-react';
import type { TravellersData } from '@/types/flights';

export type { CabinClassUI as CabinClass, TravellersData } from '@/types/flights';

// ── Colours (match FlightNavSearchBar) ───────────────────────────────────────
const NAVY = '#171B63';
const SLATE = '#636e9d';
const LINE = '#E4E6F5';

interface TravellersSelectorProps {
  value: TravellersData;
  onChange: (data: TravellersData) => void;
  onClose?: () => void;
}

interface CounterRowProps {
  label: string;
  caption: string;
  count: number;
  min: number;
  max: number;
  onIncrement: () => void;
  onDecrement: () => void;
}

function CounterRow({ label, caption, count, min, max, onIncrement, onDecrement }: CounterRowProps) {
  return (
    <Box
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 10,
      }}
    >
      <Box>
        <span style={{ display: 'block', fontSize: 13, fontWeight: 600, color: NAVY, fontFamily: 'inherit' }}>
          {label}
        </span>
        <span style={{ display: 'block', fontSize: 11, color: SLATE, fontFamily: 'inherit' }}>
          {caption}
        </span>
      </Box>
      <Group gap={8} align="center">
        <ActionIcon
          size="sm"
          variant="default"
          style={{ borderColor: LINE, color: NAVY }}
          onClick={onDecrement}
          disabled={count <= min}
          aria-label={`Decrease ${label}`}
        >
          <Minus size={12} />
        </ActionIcon>
        <span
          style={{
            minWidth: 20,
            textAlign: 'center',
            fontSize: 13,
            fontWeight: 600,
            color: NAVY,
            fontFamily: 'inherit',
          }}
        >
          {count}
        </span>
        <ActionIcon
          size="sm"
          variant="default"
          style={{ borderColor: LINE, color: NAVY }}
          onClick={onIncrement}
          disabled={count >= max}
          aria-label={`Increase ${label}`}
        >
          <Plus size={12} />
        </ActionIcon>
      </Group>
    </Box>
  );
}

/**
 * Single source of truth for traveller-count limits — used for both the +/-
 * handler clamp and the disabled state on the +/- buttons. Splitting the two
 * caused a silent divergence risk per auto-review on #949.
 */
const TRAVELLER_LIMITS = {
  adults: { min: 1, max: 9 },
  children: { min: 0, max: 8 },
  infants: { min: 0, max: 2 },
} as const;

type TravellerKey = keyof typeof TRAVELLER_LIMITS;

export function TravellersSelector({ value, onChange, onClose }: TravellersSelectorProps) {
  // Seed counts: null means "fresh / unset" — open with sensible minimums so the
  // user sees concrete numbers in the picker.
  const [localValue, setLocalValue] = useState<TravellersData>({
    adults: value.adults ?? 1,
    children: value.children ?? 0,
    infants: value.infants ?? 0,
    cabinClass: value.cabinClass,
  });

  const handleIncrement = (type: TravellerKey) => {
    setLocalValue((prev) => ({
      ...prev,
      [type]: Math.min((prev[type] ?? 0) + 1, TRAVELLER_LIMITS[type].max),
    }));
  };

  const handleDecrement = (type: TravellerKey) => {
    setLocalValue((prev) => ({
      ...prev,
      [type]: Math.max((prev[type] ?? 0) - 1, TRAVELLER_LIMITS[type].min),
    }));
  };

  const handleApply = () => {
    onChange(localValue);
    onClose?.();
  };

  return (
    <Box>
      <CounterRow
        label="Adults"
        caption="12+ years"
        count={localValue.adults ?? 1}
        min={TRAVELLER_LIMITS.adults.min}
        max={TRAVELLER_LIMITS.adults.max}
        onIncrement={() => handleIncrement('adults')}
        onDecrement={() => handleDecrement('adults')}
      />
      <CounterRow
        label="Children"
        caption="2–11 years"
        count={localValue.children ?? 0}
        min={TRAVELLER_LIMITS.children.min}
        max={TRAVELLER_LIMITS.children.max}
        onIncrement={() => handleIncrement('children')}
        onDecrement={() => handleDecrement('children')}
      />
      <CounterRow
        label="Infants"
        caption="Under 2 years"
        count={localValue.infants ?? 0}
        min={TRAVELLER_LIMITS.infants.min}
        max={TRAVELLER_LIMITS.infants.max}
        onIncrement={() => handleIncrement('infants')}
        onDecrement={() => handleDecrement('infants')}
      />

      <span
        style={{
          display: 'block',
          fontSize: 10,
          color: SLATE,
          marginBottom: 12,
          marginTop: 2,
          fontFamily: 'inherit',
          lineHeight: 1.4,
          whiteSpace: 'pre-line',
        }}
      >
        {'Age validity is based on the date of travel.\nSome airlines may have restrictions for minors travelling alone.'}
      </span>

      <Group justify="flex-end" mt={4}>
        <Button
          size="xs"
          radius="xl"
          style={{ backgroundColor: NAVY, color: 'white' }}
          onClick={handleApply}
          fw={600}
          tt="none"
        >
          Apply
        </Button>
      </Group>
    </Box>
  );
}

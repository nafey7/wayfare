import type { TripType } from '@/types/flights';
import { NAV_NAVY, NAV_MIST_CARD } from '@/theme/navTokens';

const TRIP_TYPE_OPTIONS: { value: TripType; label: string }[] = [
  { value: 'round-trip', label: 'Round trip' },
  { value: 'one-way', label: 'One way' },
  { value: 'multi-city', label: 'Multi-city' },
];

export interface TripTypeDialogProps {
  value: TripType | null;
  onUpdate: (tripType: TripType) => void;
}

export function TripTypeDialog({ value, onUpdate }: TripTypeDialogProps) {
  return (
    <>
      {TRIP_TYPE_OPTIONS.map(({ value: optValue, label }) => (
        <button
          key={optValue}
          type="button"
          aria-pressed={value === optValue}
          onClick={() => onUpdate(optValue)}
          style={{
            display: 'block',
            width: '100%',
            textAlign: 'left',
            padding: '8px 12px',
            borderRadius: 8,
            border: 'none',
            background: value === optValue ? NAV_MIST_CARD : 'white',
            color: NAV_NAVY,
            fontSize: 13,
            fontWeight: value === optValue ? 600 : 400,
            cursor: 'pointer',
            fontFamily: 'inherit',
          }}
        >
          {label}
        </button>
      ))}
    </>
  );
}

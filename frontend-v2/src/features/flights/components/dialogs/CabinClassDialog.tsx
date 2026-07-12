import type { CabinClassUI } from '@/types/flights';
import { NAV_NAVY, NAV_MIST_CARD } from '@/theme/navTokens';

const CABIN_OPTIONS: CabinClassUI[] = ['Economy', 'Premium Economy', 'Business', 'First'];

export interface CabinClassDialogProps {
  value: CabinClassUI | null;
  onUpdate: (cabinClass: CabinClassUI) => void;
}

export function CabinClassDialog({ value, onUpdate }: CabinClassDialogProps) {
  return (
    <>
      {CABIN_OPTIONS.map((option) => (
        <button
          key={option}
          type="button"
          aria-pressed={value === option}
          onClick={() => onUpdate(option)}
          style={{
            display: 'block',
            width: '100%',
            textAlign: 'left',
            padding: '8px 12px',
            borderRadius: 8,
            border: 'none',
            background: value === option ? NAV_MIST_CARD : 'white',
            color: NAV_NAVY,
            fontSize: 13,
            fontWeight: value === option ? 600 : 400,
            cursor: 'pointer',
            fontFamily: 'inherit',
          }}
        >
          {option}
        </button>
      ))}
    </>
  );
}

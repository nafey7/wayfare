import { SegmentedControl } from '@mantine/core';
import { Hotel, GitBranch } from 'lucide-react';
import type { HotelTripType } from '@/types/hotels';

interface HotelTripTypeSelectorProps {
  value: HotelTripType;
  onChange: (type: HotelTripType) => void;
}

export function HotelTripTypeSelector({ value, onChange }: HotelTripTypeSelectorProps) {
  return (
    <SegmentedControl
      value={value}
      onChange={(v) => onChange(v as HotelTripType)}
      mb="sm"
      aria-label="Hotel trip type"
      data={[
        {
          value: 'single',
          label: (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontWeight: 600 }}>
              <Hotel size={18} />
              Single stay
            </span>
          ),
        },
        {
          value: 'multi-stay',
          label: (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontWeight: 600 }}>
              <GitBranch size={18} />
              Multi-stay
            </span>
          ),
        },
      ]}
    />
  );
}

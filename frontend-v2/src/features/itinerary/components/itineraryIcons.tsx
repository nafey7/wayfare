// Shared inline SVG icons for itinerary components.
// Kept as inline SVG (no icon library dependency) so the bundle stays light.

import { C_STAR } from '../constants/itineraryColors';

export function ChevronIcon({
  direction, size = 16, color = '#fff', strokeWidth = 2.2,
}: { direction: 'up' | 'down'; size?: number; color?: string; strokeWidth?: number }) {
  const d = direction === 'down' ? 'M6 9l6 6 6-6' : 'M18 15l-6-6-6 6';
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d={d} />
    </svg>
  );
}

export function StarIcon({ size = 9 }: { size?: number }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill={C_STAR} stroke="none">
      <path d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 22 12 18.56 5.82 22 7 14.14 2 9.27l6.91-1.01L12 2z" />
    </svg>
  );
}

export function ArrowRightIcon({ size = 18 }: { size?: number }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="#fff" strokeWidth={3} strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12h14M13 5l7 7-7 7" />
    </svg>
  );
}

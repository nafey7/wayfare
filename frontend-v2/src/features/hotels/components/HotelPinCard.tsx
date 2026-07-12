import { Box, Group, Text, UnstyledButton } from '@mantine/core';
import { HotelImageWithFallback } from './HotelImageWithFallback';
import hotelFallback from '@/assets/images/hotels/hotel-fallback.svg';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface HotelPinCardData {
  id: string;
  name: string;
  area: string;
  stars: number;
  reviewScore: number;
  reviewCount: number;
  reviewLabel: string;
  pricePerNight: string;
  totalPrice: string;
  thumbnail?: string;
}

export interface HotelPinCardProps {
  hotel: HotelPinCardData;
  onClose: () => void;
  onViewDetails: () => void;
  /** Extra bottom offset (px) to clear fixed chrome (BottomNav + ChatSheet). */
  bottomInset?: number;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function HotelPinCard({ hotel, onClose, onViewDetails, bottomInset = 0 }: HotelPinCardProps) {
  return (
    <Box
      style={{
        position: 'absolute', left: 10, right: 10, bottom: 16 + bottomInset,
        background: 'white', borderRadius: 14,
        boxShadow: '0 8px 24px rgba(0,0,0,0.2)',
        overflow: 'hidden', zIndex: 15,
      }}
    >
      {/* Photo */}
      <Box style={{ position: 'relative', height: 140 }}>
        <Box style={{ position: 'absolute', inset: 0, overflow: 'hidden' }}>
          <HotelImageWithFallback
            primaryUrl={hotel.thumbnail}
            hotelName={hotel.name}
            city={hotel.area}
            fallbackSrc={hotelFallback}
            alt={hotel.name}
            sx={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />
        </Box>

        {/* Close button */}
        <UnstyledButton
          onClick={onClose}
          style={{
            position: 'absolute', top: 8, right: 8, zIndex: 2,
            width: 26, height: 26, borderRadius: '50%',
            background: 'rgba(0,0,0,0.6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
          aria-label="Close"
        >
          <svg viewBox="0 0 24 24" width={12} height={12} fill="none" stroke="white" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 6 6 18" /><path d="m6 6 12 12" />
          </svg>
        </UnstyledButton>
      </Box>

      {/* Info body — tap to view details */}
      <Box
        px={12} py={10}
        onClick={onViewDetails}
        style={{ cursor: 'pointer' }}
      >
        <Group justify="space-between" align="center" mb={2}>
          <Text style={{ fontSize: 11, color: '#d4a574' }}>{'★'.repeat(hotel.stars)}</Text>
          <Group gap={4} align="center">
            <Box style={{ background: '#E7FBBC', color: '#2c3ea8', padding: '1px 5px', borderRadius: 3, fontWeight: 700, fontSize: 10 }}>
              {hotel.reviewScore}
            </Box>
            <Text style={{ fontSize: 11, color: '#636e9d' }}>{hotel.reviewCount.toLocaleString()} reviews</Text>
          </Group>
        </Group>

        <Text style={{ fontSize: 15, fontWeight: 600, color: '#2A2F5F', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {hotel.name}
        </Text>
        <Text style={{ fontSize: 12, color: '#636e9d', marginBottom: 6 }}>{hotel.area}</Text>

        <Group justify="space-between" align="baseline">
          <Text style={{ fontSize: 15, fontWeight: 700, color: '#2A2F5F' }}>
            {hotel.pricePerNight}
            <Text span style={{ fontSize: 11, color: '#9aa2c5', fontWeight: 400 }}> /night</Text>
          </Text>
          <Text style={{ fontSize: 11, color: '#9aa2c5' }}>{hotel.totalPrice} total</Text>
        </Group>
      </Box>
    </Box>
  );
}

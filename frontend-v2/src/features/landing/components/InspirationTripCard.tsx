import { useState } from 'react';
import { Box, Stack, Text, ActionIcon } from '@mantine/core';
import { Zap, Star, Heart } from 'lucide-react';
import { formatTripPrice } from '../constants/currency';
import { NAVY, SLATE } from '../landingColors';

export interface InspirationTripData {
  id: string;
  title: string;
  builtInSeconds: number;
  flightRoute: string;
  hotelName: string;
  stops: number;
  priceAmount: number;
  currency?: string;
  duration: string;
  imageUrl?: string;
  theme: 'lisbon' | 'tokyo' | 'bali' | 'bangkok';
  tag?: string;
  rating?: number;
  saved?: boolean;
  savedLabel?: string;
}

const PHOTO_GRADIENTS: Record<InspirationTripData['theme'], string> = {
  lisbon:  'linear-gradient(135deg, #FFCBA0, #FF8B6B 50%, #C44545)',
  tokyo:   'linear-gradient(135deg, #B7CDFF, #4A6FB5 60%, #1D2D5F)',
  bali:    'linear-gradient(135deg, #C0F0CE, #5DAA7B 60%, #2D6B48)',
  bangkok: 'linear-gradient(135deg, #FFE6A0, #E6A94B 50%, #8B5A1A)',
};

export interface InspirationTripCardProps {
  data: InspirationTripData;
  onClick?: (data: InspirationTripData) => void;
  onToggleSave?: (data: InspirationTripData) => void;
  /** Stable marketing id placed on the root element (only wired on `/`). */
  id?: string;
}

export function InspirationTripCard({ data, onClick, onToggleSave, id }: InspirationTripCardProps) {
  const [hovered, setHovered] = useState(false);
  const photoBackground = data.imageUrl ? `url(${data.imageUrl})` : PHOTO_GRADIENTS[data.theme];

  return (
    <Stack
      id={id}
      gap={0}
      onClick={() => onClick?.(data)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{ cursor: 'pointer' }}
    >
      <Box
        style={{
          aspectRatio: '4/3',
          width: '100%',
          borderRadius: 18,
          backgroundImage: photoBackground,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          marginBottom: 12,
          position: 'relative',
          transform: hovered ? 'scale(1.015)' : 'scale(1)',
          transition: 'transform .35s ease',
          overflow: 'hidden',
        }}
      >
        {/* Vignette overlay */}
        <Box
          style={{
            position: 'absolute',
            inset: 0,
            borderRadius: 18,
            boxShadow: 'inset 0 -60px 80px -40px rgba(0,0,0,.35)',
            opacity: hovered ? 1 : 0.55,
            transition: 'opacity .25s ease',
            pointerEvents: 'none',
          }}
        />

        {/* Top-left: badge cluster */}
        <Box style={{ position: 'absolute', top: 12, left: 12, zIndex: 1, display: 'flex', gap: 6 }}>
          {data.saved ? (
            <Box style={{
              backgroundColor: 'rgba(255,255,255,.95)',
              color: NAVY,
              fontSize: 11,
              fontWeight: 700,
              paddingInline: 12,
              paddingBlock: 5,
              borderRadius: 999,
              backdropFilter: 'blur(4px)',
            }}>
              {data.savedLabel ?? 'Saved'}
            </Box>
          ) : (
            <Box style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              backgroundColor: 'rgba(255,255,255,.95)',
              color: NAVY,
              fontSize: 11,
              fontWeight: 700,
              paddingInline: 12,
              paddingBlock: 5,
              borderRadius: 999,
              backdropFilter: 'blur(4px)',
            }}>
              <Zap size={13} />
              <span>Built in {data.builtInSeconds}s</span>
            </Box>
          )}
          {data.tag && (
            <Box style={{
              backgroundColor: 'rgba(23,27,99,.85)',
              color: 'white',
              fontSize: 11,
              fontWeight: 700,
              paddingInline: 12,
              paddingBlock: 5,
              borderRadius: 999,
              backdropFilter: 'blur(4px)',
            }}>
              {data.tag}
            </Box>
          )}
        </Box>

        {/* Top-right: heart button — only rendered when a save handler is wired up */}
        {onToggleSave && (
          <ActionIcon
            onClick={(e) => {
              e.stopPropagation();
              onToggleSave(data);
            }}
            aria-label={data.saved ? 'Unsave trip' : 'Save trip'}
            style={{
              position: 'absolute',
              top: 10,
              right: 10,
              zIndex: 1,
              width: 32,
              height: 32,
              backgroundColor: data.saved ? 'white' : 'rgba(0,0,0,.22)',
              color: data.saved ? '#DD2A4A' : 'white',
              backdropFilter: 'blur(4px)',
              border: 'none',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              transition: 'transform .15s ease',
            }}
          >
            <Heart
              size={16}
              fill={data.saved ? '#DD2A4A' : 'none'}
              stroke={data.saved ? '#DD2A4A' : 'white'}
            />
          </ActionIcon>
        )}
      </Box>

      <Box style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
        <Text style={{
          fontSize: 15,
          fontWeight: 800,
          color: NAVY,
          letterSpacing: '-.005em',
          lineHeight: 1.3,
          flex: 1,
        }}>
          {data.title}
        </Text>
        {data.rating && (
          <Box style={{ display: 'flex', alignItems: 'center', gap: 2, flexShrink: 0, marginTop: 2 }}>
            <Star size={14} fill={NAVY} color={NAVY} />
            <Text style={{ fontSize: 12, fontWeight: 700, color: NAVY }}>
              {data.rating.toFixed(1)}
            </Text>
          </Box>
        )}
      </Box>
      <Text style={{ fontSize: 12, color: SLATE, marginTop: 4, lineHeight: 1.5 }}>
        ✈ {data.flightRoute} · 🏨 {data.hotelName}
      </Text>
      <Text style={{ fontSize: 12, color: SLATE, lineHeight: 1.5 }}>
        🗺 {data.stops} stops · {data.duration}
      </Text>
      <Text style={{ fontSize: 14, color: NAVY, fontWeight: 800, marginTop: 6 }}>
        {formatTripPrice(data.priceAmount, data.currency)}
        <Box component="span" style={{ color: SLATE, fontWeight: 500, marginLeft: 4 }}>
          total
        </Box>
      </Text>
    </Stack>
  );
}

import { useState } from 'react';
import { ActionIcon, Badge, Box, Group, Text } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { Info, Users } from 'lucide-react';
import { FlightDetailsModal } from '@/features/chat/components/flights/FlightDetailsModal';
import { flightCardToMappedFlight } from '../utils/flightUtils';
import { useResolveAirportQuery } from '@/api/flightsApi';
import { airlineLogoFallbackUrl } from '@/utils/apiAssetUrl';
import type { FlightLeg } from '@/types/flight';

export interface FlightCardPassengerCounts {
  adults: number;
  children: number;
  infants: number;
}

export interface FlightCardProps {
  flight: {
    id: string;
    aircraftName: string;
    flightNumber?: string;
    /** `Return` = true round trip; `Circle` = multi-city */
    journeyType?: string;
    tags: string[];
    passengers: number;
    passengerCounts?: FlightCardPassengerCounts;
    legs: FlightLeg[];
    price: number;
    discount?: number;
    /** Original ticket amount before platform fee – for price breakdown in modal. */
    original_total_fare?: number;
    /** Platform fee percentage – for price breakdown in modal. */
    platform_fee_percentage?: number;
  };
  onSelect?: (flightId: string) => void;
  /** When true, disables interaction while a booking request is in-flight. */
  isSelecting?: boolean;
  /** Highlight this card when it is the chosen option for a multicity leg. */
  isSelected?: boolean;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function useStopCity(iataCode: string | null) {
  const { data } = useResolveAirportQuery(iataCode ?? '', { skip: !iataCode });
  return data?.city ?? iataCode ?? '';
}

function getAirlineMeta(leg: FlightLeg): { url: string | null; name: string | null; code: string | null } {
  const first = leg.airlinesInfo?.[0];
  if (!first) return { url: null, name: null, code: null };
  const code = first.code?.trim();
  const safe = code && /^[A-Z0-9]{2,3}$/i.test(code) ? code.toUpperCase() : null;
  return {
    url: first.logoUrl ?? airlineLogoFallbackUrl(safe),
    name: first.name ?? null,
    code: safe,
  };
}

function parseStopCode(stopsText: string): string | null {
  return stopsText.match(/\(([^)]+)\)/)?.[1] ?? null;
}

// ─── Airline logo ──────────────────────────────────────────────────────────────

function AirlineLogo({ leg }: { leg: FlightLeg }) {
  const { url, name, code } = getAirlineMeta(leg);
  const [imgError, setImgError] = useState(false);
  return (
    <Box
      style={{
        width: 40,
        height: 40,
        borderRadius: 10,
        flexShrink: 0,
        overflow: 'hidden',
        background: '#f4f5fb',
        border: '1px solid #eef0f8',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {url && !imgError ? (
        <img
          src={url}
          alt={name ?? 'Airline'}
          onError={() => setImgError(true)}
          style={{ width: '100%', height: '100%', objectFit: 'contain' }}
        />
      ) : (
        <Text style={{ fontSize: '0.625rem' }} c="navy.5" fw={700}>
          {code ?? name?.slice(0, 2).toUpperCase() ?? '—'}
        </Text>
      )}
    </Box>
  );
}

// ─── Single leg row ────────────────────────────────────────────────────────────

function LegRow({ leg }: { leg: FlightLeg }) {
  const stopCode = leg.stops > 0 ? parseStopCode(leg.stopsText) : null;
  const stopCity = useStopCity(stopCode);
  const nextDay = leg.departure.date !== leg.arrival.date;
  const isDirect = leg.stops === 0;
  const stopLabel = isDirect
    ? 'Direct'
    : stopCity
    ? `${leg.stops} stop · ${stopCity}`
    : leg.stopsText || `${leg.stops} stop${leg.stops > 1 ? 's' : ''}`;

  return (
    <Box style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Box style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
        <Text
          fw={700}
          style={{
            fontSize: '0.9375rem',
            color: 'var(--mantine-color-navy-7)',
            whiteSpace: 'nowrap',
            letterSpacing: '-0.01em',
            flexShrink: 0,
          }}
        >
          {leg.departure.time}
          {' – '}
          {leg.arrival.time}
          {nextDay && (
            <Text
              component="span"
              style={{ fontSize: '0.5625rem', color: 'var(--mantine-color-navy-3)', marginLeft: 2 }}
            >
              +1
            </Text>
          )}
        </Text>
        <Text
          style={{
            fontSize: '0.9375rem',
            fontWeight: 500,
            color: 'var(--mantine-color-navy-5)',
            whiteSpace: 'nowrap',
            flexShrink: 0,
          }}
        >
          {leg.totalTimeDisplay ?? leg.duration}
        </Text>
      </Box>

      <Box style={{ display: 'flex', alignItems: 'baseline', gap: 8, overflow: 'hidden' }}>
        <Text
          style={{
            fontSize: '0.6875rem',
            color: 'var(--mantine-color-navy-5)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            flexShrink: 1,
          }}
        >
          {leg.departure.airport} → {leg.arrival.airport}
        </Text>
        <Text
          style={{
            fontSize: '0.6875rem',
            fontWeight: 600,
            whiteSpace: 'nowrap',
            flexShrink: 0,
            color: isDirect ? 'var(--mantine-color-accent-6)' : 'var(--mantine-color-navy-5)',
          }}
        >
          {stopLabel}
        </Text>
      </Box>
    </Box>
  );
}

// ─── Main card ─────────────────────────────────────────────────────────────────

export function FlightCard({
  flight,
  isSelected = false,
  isSelecting = false,
  onSelect,
}: FlightCardProps) {
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [hovered, setHovered] = useState(false);
  const isWideEnough = useMediaQuery('(min-width: 480px)');

  const total = flight.price * flight.passengers;

  const valueTags = flight.tags.filter((t) => t.toLowerCase().includes('best value'));
  const otherTags = flight.tags.filter((t) => !t.toLowerCase().includes('best value'));

  const airlineName = flight.legs[0]?.airlinesInfo?.[0]?.name;
  const airlineCode = flight.legs[0]?.airlinesInfo?.[0]?.code?.toUpperCase();

  const handleClick = () => {
    if (isSelecting) return;
    if (onSelect) onSelect(flight.id);
    else setDetailsOpen(true);
  };

  const handleInfo = (e: React.MouseEvent) => {
    e.stopPropagation();
    setDetailsOpen(true);
  };

  const popOnHover = hovered && !isSelected;
  const borderColor = isSelected
    ? 'var(--mantine-color-brand-6)'
    : popOnHover
    ? 'var(--mantine-color-brand-3)'
    : 'transparent';
  const borderWidth = isSelected ? 2 : 1;
  const drop = isSelected
    ? '0 2px 8px rgba(23,27,99,0.10)'
    : popOnHover
    ? '0 16px 36px rgba(23,27,99,0.20)'
    : '0 1px 3px rgba(23,27,99,0.04)';

  return (
    <Box
      mb="md"
      role={onSelect ? 'button' : undefined}
      tabIndex={onSelect ? 0 : undefined}
      aria-busy={isSelecting || undefined}
      onClick={handleClick}
      onKeyDown={(e) => {
        if (onSelect && !isSelecting && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          handleClick();
        }
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        position: 'relative',
        background: 'white',
        borderRadius: 16,
        border: `${borderWidth}px solid ${borderColor}`,
        boxShadow: drop,
        cursor: isSelecting ? 'progress' : 'pointer',
        transition: 'box-shadow 180ms ease, border-color 180ms ease, transform 180ms ease',
        transform: popOnHover ? 'translateY(-4px)' : 'translateY(0)',
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
        minWidth: isWideEnough ? 420 : 0,
        padding: isSelected ? '13px' : '14px',
        opacity: isSelecting ? 0.6 : 1,
        zIndex: popOnHover ? 1 : 'auto',
      }}
    >
      <Box style={{ display: 'flex', gap: 12, alignItems: 'stretch' }}>

        <Box
          style={{
            width: 44,
            flexShrink: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            paddingTop: 2,
            gap: 4,
          }}
        >
          {flight.legs[0] && <AirlineLogo leg={flight.legs[0]} />}
          {airlineCode && (
            <Text
              style={{
                fontSize: '0.5625rem',
                color: 'var(--mantine-color-navy-3)',
                fontWeight: 600,
                letterSpacing: '0.06em',
              }}
            >
              {airlineCode}
            </Text>
          )}
        </Box>


        <Box style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 6 }}>
          {flight.legs.map((leg, i) => (
            <Box
              key={i}
              style={
                i > 0
                  ? { marginTop: 6, paddingTop: 6, borderTop: '1px dashed var(--mantine-color-gray-3)' }
                  : undefined
              }
            >
              <LegRow leg={leg} />
            </Box>
          ))}

          {(airlineName || valueTags.length > 0 || otherTags.length > 0 || flight.discount != null) && (
            <Box style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 6, marginTop: 2 }}>
              {airlineName && (
                <Text style={{ fontSize: '0.6875rem', color: 'var(--mantine-color-navy-5)', whiteSpace: 'nowrap' }}>
                  {airlineName}
                </Text>
              )}
              {valueTags.map((t) => (
                <Badge
                  key={t}
                  variant="light"
                  color="accent"
                  radius="xl"
                  size="xs"
                  style={{ fontWeight: 600, textTransform: 'none', fontSize: '0.625rem' }}
                >
                  {t}
                </Badge>
              ))}
              {otherTags.map((t) => (
                <Badge
                  key={t}
                  variant="outline"
                  color="gray"
                  radius="xl"
                  size="xs"
                  style={{ fontWeight: 400, textTransform: 'none', fontSize: '0.625rem' }}
                >
                  {t}
                </Badge>
              ))}
              {flight.discount != null && (
                <Text style={{ fontSize: '0.625rem', fontWeight: 600, color: 'var(--mantine-color-accent-6)' }}>
                  -{flight.discount}% off
                </Text>
              )}
            </Box>
          )}
        </Box>

        {/* Price + info icon column */}
        <Box
          style={{
            flexShrink: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'flex-end',
            gap: 6,
            paddingTop: 2,
          }}
        >
          <ActionIcon
            variant="transparent"
            size={20}
            onClick={handleInfo}
            aria-label="Flight details"
          >
            <Info size={14} color="var(--mantine-color-navy-4)" />
          </ActionIcon>

          <Box style={{ textAlign: 'right' }}>
            <Text
              fw={700}
              style={{ fontSize: '0.875rem', color: 'var(--mantine-color-navy-7)', lineHeight: 1.2 }}
            >
              ${total.toLocaleString()} total
            </Text>
            <Group gap={5} align="center" justify="flex-end" mt={2}>
              <Text style={{ fontSize: '0.625rem', color: 'var(--mantine-color-navy-5)' }}>
                ${flight.price.toLocaleString()} / person
              </Text>
              <Group gap={2} align="center">
                <Users size={10} color="var(--mantine-color-navy-3)" />
                <Text style={{ fontSize: '0.625rem', color: 'var(--mantine-color-navy-5)', fontWeight: 600 }}>
                  {flight.passengers}
                </Text>
              </Group>
            </Group>
          </Box>
        </Box>

      </Box>

      <FlightDetailsModal
        open={detailsOpen}
        onOpenChange={setDetailsOpen}
        flight={flightCardToMappedFlight(flight)}
      />
    </Box>
  );
}

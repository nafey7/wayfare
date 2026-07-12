import { useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Text, UnstyledButton } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { format, parseISO, isValid, isSameMonth } from 'date-fns';

import { useAppDispatch, useAppSelector } from '@/store';
import { selectIsAuthenticated } from '@/store/slices/authSlice';
import { selectChatId } from '@/store/slices/chatSlice';
import { setLastItineraryState, openAuthModal } from '@/store/slices/uiSlice';
import { useGetItinerariesQuery } from '@/api/itinerariesApi';
import { AuthenticatedImage } from '@/features/itinerary/components/AuthenticatedImage';
import { getGuestItineraries, type GuestItineraryEntry } from '@/features/chat/utils/guestItineraries';
import {
  getSavedItineraryCardSummary,
  destinationWithoutCountry,
} from '@/features/itinerary/utils/savedItineraryCardSummary';
import { itineraryView } from '@/features/routing';
import { ROUTES } from '@/features/routing/constants';
import { LANDING_TOKENS } from '../landingTokens';
import { NAVY } from '../landingColors';

const MAX_SHOWN = 2;
const CARD_WIDTH = 260;

function buildShortDateLabel(departure?: string, returnDate?: string): string | null {
  if (!departure) return null;
  const dep = parseISO(departure);
  if (!isValid(dep)) return null;
  if (!returnDate) return format(dep, 'd MMM');
  const ret = parseISO(returnDate);
  if (!isValid(ret)) return format(dep, 'd MMM');
  if (isSameMonth(dep, ret)) return `${format(dep, 'd')}–${format(ret, 'd MMM')}`;
  return `${format(dep, 'd MMM')} – ${format(ret, 'd MMM')}`;
}

function buildTravellersLabel(adults?: number, children?: number, infants?: number): string | null {
  const total = (adults ?? 0) + (children ?? 0) + (infants ?? 0);
  if (total === 0) return null;
  return `${total} ${total === 1 ? 'traveller' : 'travellers'}`;
}

function guestFirstImageUrl(entry: GuestItineraryEntry): string | null {
  try {
    const items = (entry.structuredItinerary as { itineraryItems?: unknown[] }).itineraryItems;
    if (!Array.isArray(items) || !items.length) return null;
    const first = items[0] as Record<string, unknown>;
    const url = first.imageUrl;
    return typeof url === 'string' && url.trim() ? url.trim() : null;
  } catch {
    return null;
  }
}

interface ItineraryCardData {
  key: string;
  destination: string;
  dateLabel: string | null;
  nightsLabel: string | null;
  travellersLabel: string | null;
  heroImageUrl: string | null;
  onView: () => void;
}

function StripCard({ card }: { card: ItineraryCardData }) {
  const metaParts = [card.dateLabel, card.nightsLabel, card.travellersLabel].filter(Boolean);

  return (
    <UnstyledButton
      onClick={card.onView}
      style={{
        flex: `0 0 ${CARD_WIDTH}px`,
        width: CARD_WIDTH,
        padding: '12px 14px',
        borderRadius: 10,
        border: `1px solid ${LANDING_TOKENS.border}`,
        backgroundColor: 'white',
        display: 'flex',
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
        cursor: 'pointer',
        textAlign: 'left',
      }}
    >
      <Box style={{ flex: 1, minWidth: 0 }}>
        <Text
          fw={700}
          style={{
            fontFamily: LANDING_TOKENS.fontFamily.display,
            color: NAVY,
            fontSize: 14,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            marginBottom: 3,
          }}
        >
          {card.destination}
        </Text>
        <Text
          style={{
            fontSize: 12,
            color: LANDING_TOKENS.textMuted,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {metaParts.join(' · ')}
          {metaParts.length > 0 && <span aria-hidden="true"> ›</span>}
        </Text>
      </Box>

      {card.heroImageUrl && (
        <Box
          style={{
            flexShrink: 0,
            width: 60,
            height: 60,
            borderRadius: 8,
            overflow: 'hidden',
            backgroundColor: LANDING_TOKENS.border,
          }}
        >
          <AuthenticatedImage
            src={card.heroImageUrl}
            alt={card.destination}
            sx={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
          />
        </Box>
      )}
    </UnstyledButton>
  );
}


function StripContent({
  cards,
  onHeadingClick,
}: {
  cards: ItineraryCardData[];
  onHeadingClick: () => void;
}) {
  const isMdUp = useMediaQuery('(min-width: 48em)');
  const scrollRef = useRef<HTMLDivElement>(null);

  return (
    <Box
      style={{
        paddingBlock: 14,
        paddingInline: isMdUp ? 32 : 16,
        backgroundColor: 'white',
      }}
    >
      <Box style={{ maxWidth: 1200, marginInline: 'auto' }}>
        <UnstyledButton
          onClick={onHeadingClick}
          style={{ display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer', marginBottom: 12 }}
        >
          <Text
            fw={700}
            style={{
              fontFamily: LANDING_TOKENS.fontFamily.display,
              color: NAVY,
              fontSize: 16,
            }}
          >
            Recent trips
          </Text>
          <Text style={{ color: LANDING_TOKENS.textMuted, fontSize: 14, lineHeight: 1 }}>›</Text>
        </UnstyledButton>

        <Box
          ref={scrollRef}
          style={{
            display: 'flex',
            flexDirection: 'row',
            gap: 12,
            overflowX: 'auto',
            paddingBottom: 4,
            scrollbarWidth: 'none',
            msOverflowStyle: 'none',
          }}
        >
          {cards.map((card) => (
            <StripCard key={card.key} card={card} />
          ))}
        </Box>
      </Box>
    </Box>
  );
}

function GuestItinerariesStrip() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const chatId = useAppSelector(selectChatId);
  const entries = getGuestItineraries().slice(0, MAX_SHOWN);

  if (!entries.length) return null;

  const cards: ItineraryCardData[] = entries.map((entry: GuestItineraryEntry, idx) => {
    const meta = entry.tripMeta ?? {};
    return {
      key: entry.savedItineraryId ?? `guest-${idx}`,
      destination: destinationWithoutCountry(meta.destination),
      dateLabel: buildShortDateLabel(meta.departure_date, meta.return_date),
      nightsLabel: null,
      travellersLabel: buildTravellersLabel(meta.adults, meta.children, meta.infants),
      heroImageUrl: guestFirstImageUrl(entry),
      onView: () => {
        const locationState = {
          structuredItinerary: entry.structuredItinerary,
          tripMeta: entry.tripMeta,
          savedItineraryId: entry.savedItineraryId,
        };
        dispatch(setLastItineraryState({ chatId: chatId ?? '__anon__', state: locationState }));
        navigate(ROUTES.PUBLIC_CHAT_ITINERARY, { state: locationState });
      },
    };
  });

  return <StripContent cards={cards} onHeadingClick={() => dispatch(openAuthModal())} />;
}

function AuthItinerariesStrip() {
  const navigate = useNavigate();
  const { data: itineraries } = useGetItinerariesQuery();

  const recent = useMemo(
    () =>
      [...(itineraries ?? [])]
        .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
        .slice(0, MAX_SHOWN),
    [itineraries],
  );

  if (!recent.length) return null;

  const cards: ItineraryCardData[] = recent.map((itinerary) => {
    const summary = getSavedItineraryCardSummary(itinerary);
    const meta = itinerary.tripMeta;
    return {
      key: itinerary.id,
      destination: summary.destinationLabel,
      dateLabel: buildShortDateLabel(meta?.departureDate, meta?.returnDate),
      nightsLabel: summary.nightsLabel !== '—' ? summary.nightsLabel : null,
      travellersLabel: buildTravellersLabel(meta?.adults, meta?.children, meta?.infants),
      heroImageUrl: summary.heroImageUrl,
      onView: () => navigate(itineraryView(itinerary.id)),
    };
  });

  return <StripContent cards={cards} onHeadingClick={() => navigate(ROUTES.ITINERARIES)} />;
}

/**
 * Shows up to 2 recent itineraries below the UnifiedHeader on the landing / home page.
 *
 * - Logged-out users: reads from `voya_guest_itineraries` localStorage (plain <img>).
 * - Logged-in users: reads from GET /api/itineraries (AuthenticatedImage with JWT).
 * - Renders nothing when there are no itineraries to show.
 */
export function RecentItinerariesStrip() {
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  return isAuthenticated ? <AuthItinerariesStrip /> : <GuestItinerariesStrip />;
}

import { useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Text } from '@mantine/core';
import type {
  MulticityChatLegNormalized,
  MulticityChatPayloadNormalized,
} from '@/features/chat/utils/extractMulticityFlightSearchResults';
import {
  legHasCuratedFlights,
  legToExtractedSingleLeg,
  multicityChatPayloadToSearchParamsUI,
} from '@/features/chat/utils/extractMulticityFlightSearchResults';
import { extractChatFilters } from '@/features/chat/utils/chatSearchParamsToUI';
import {
  serializeChatFiltersToUrl,
  serializeSearchParamsToUrl,
} from '@/features/flights/utils/urlParams';
import { trackEvent } from '@/utils/gtm';
import { FlightSearchResultsPanel } from './FlightSearchResultsPanel';
import { MulticityLegPillTabs } from './MulticityLegPillTabs';

export interface MulticityRecommendationsPanelProps {
  payload: MulticityChatPayloadNormalized;
  activeLegIndex: number;
  onActiveLegIndexChange: (index: number) => void;
  /** When false, CTA is inline (e.g. mobile chat bubble with its own scroll container). */
  stickyBottomBar?: boolean;
  /** Analytics + {@link FlightSearchResultsPanel} source; use `chat-inline` for mobile chat bubble. */
  source?: 'chat' | 'recommendations' | 'chat-inline';
}

function mapLegsToTabRows(legs: MulticityChatLegNormalized[]) {
  return legs.map((l) => ({
    legIndex: l.legIndex,
    origin: l.origin,
    destination: l.destination,
    departureDate: l.departureDate,
  }));
}

/**
 * Leg tabs + {@link FlightSearchResultsPanel} for chat multicity (Circle) recommendations.
 */
export function MulticityRecommendationsPanel({
  payload,
  activeLegIndex,
  onActiveLegIndexChange,
  stickyBottomBar = true,
  source = 'recommendations',
}: MulticityRecommendationsPanelProps) {
  const navigate = useNavigate();
  const legs = payload.legs;
  const safeIndex = Math.min(Math.max(0, activeLegIndex), legs.length - 1);
  const activeLeg = legs[safeIndex];

  const extracted = useMemo(
    () => (activeLeg ? legToExtractedSingleLeg(payload.searchParams, activeLeg) : null),
    [payload.searchParams, activeLeg]
  );

  useEffect(() => {
    trackEvent('flight_search_results_shown', {
      source,
      multicity: true,
      leg_count: legs.length,
    });
  }, [legs.length, source]);

  const handleSeeFullResults = () => {
    trackEvent('chat_see_full_results_clicked', {
      result_type: 'flight',
      multicity: true,
      search_session_id: activeLeg?.sessionId || undefined,
    });
    const ui = multicityChatPayloadToSearchParamsUI(payload);
    const encoded = serializeSearchParamsToUrl(ui);
    if (encoded) {
      let url = `/flights/search?q=${encodeURIComponent(encoded)}`;
      const chatFilters = extractChatFilters(payload.searchParams);
      if (chatFilters) {
        const encodedFilters = serializeChatFiltersToUrl(chatFilters);
        if (encodedFilters) {
          url += `&f=${encodeURIComponent(encodedFilters)}`;
        }
      }
      navigate(url, { state: { fromChat: true } });
      return;
    }
    navigate('/flights/search', { state: { fromChat: true } });
  };

  const tabRows = mapLegsToTabRows(legs);
  const showPanel = Boolean(extracted && activeLeg && legHasCuratedFlights(activeLeg));

  const errorLine =
    activeLeg?.errors?.length && activeLeg.errors.some((e) => e.message) ? (
      <Text size="sm" c="dimmed" mb={4}>
        {activeLeg.errors
          .map((e) => e.message)
          .filter(Boolean)
          .join(' ')}
      </Text>
    ) : null;

  return (
    <Box style={{ display: 'flex', flexDirection: 'column', minHeight: 0, flex: 1 }}>
      <MulticityLegPillTabs legs={tabRows} value={safeIndex} onChange={onActiveLegIndexChange} />
      {errorLine}
      {showPanel && extracted ? (
        <FlightSearchResultsPanel
          data={extracted}
          source={source}
          stickyBottomBar={stickyBottomBar}
          onSeeFullResultsOverride={handleSeeFullResults}
          suppressFlightSearchResultsShownAnalytics
        />
      ) : (
        <Text size="sm" c="dimmed" py="sm">
          No flights for this leg
        </Text>
      )}
    </Box>
  );
}

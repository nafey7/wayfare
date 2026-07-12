import { useMemo, type CSSProperties } from 'react';
import { useNavigate } from 'react-router-dom';
import { Avatar, Box, Button, Group, Text, Transition } from '@mantine/core';
import { Plane } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store';
import { selectIsAuthenticated } from '@/store/slices/authSlice';
import { setChatState } from '@/store/slices/uiSlice';
import { chatConfig } from '@/features/chat/styles/chatTheme';
import type { ChatMessage } from '@/types/chat';
import {
  extractFlightSearchResults,
  extractFlightDateRangeResults,
  dateRangeToFlightSearchData,
} from '@/types/api.helpers';
import { extractMulticityFlightSearchResults } from '@/features/chat/utils/extractMulticityFlightSearchResults';
import {
  hydrateFlightSearchResultsFromPayload,
  hydrateMulticityFlightSearchResultsFromPayload,
  hydrateFlightDateRangeFromPayload,
  hydrateFlightSearchParamsForFreshSearch,
  hydrateMulticityFlightSearchParamsForFreshSearch,
} from '@/features/chat/utils/hydrateFlightRecommendationsFromChatResponse';
import { getFlightSearchMessageSummary } from '@/features/chat/utils/messageUtils';
import { ROUTES } from '@/features/routing';
import { trackEvent } from '@/utils/gtm';
import { useIsMdUp } from '@/hooks/useIsMdUp';
import { FeedbackButtons } from './FeedbackButtons';

interface FlightResultMessageProps {
  message: ChatMessage;
}

const RESULT_BUBBLE_STYLE: CSSProperties = {
  flex: 1,
  minWidth: 0,
  backgroundColor: 'white',
  borderRadius: '8px 8px 8px 0px',
  boxShadow:
    '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
  padding: 12,
  border: '1px solid var(--mantine-color-gray-3)',
};

function ErrorFallback() {
  return (
    <Transition mounted transition="fade" duration={300}>
      {(styles) => (
        <Box style={{ ...styles, marginBottom: 16 }}>
          <Text c="red" size="sm">
            Unable to display flight results. Please try searching again.
          </Text>
        </Box>
      )}
    </Transition>
  );
}

function canNavigateFlightMessage(message: ChatMessage): boolean {
  const extra = message.extraData;
  if (!extra) return false;
  if (message.type === 'flight_search_results') {
    return extractFlightSearchResults(extra) !== null;
  }
  if (message.type === 'multicity_flight_search_results') {
    return extractMulticityFlightSearchResults(extra) !== null;
  }
  if (message.type === 'flight_date_range_results') {
    const dr = extractFlightDateRangeResults(extra);
    return dr !== null && dateRangeToFlightSearchData(dr) !== null;
  }
  return false;
}

/**
 * Flight rich-result bubble.
 * - Desktop (md+): intro summary + "View flights" CTA; auto-nav handled by applySuccessfulChatResponse.
 * - Mobile (below md): same summary + CTA; no auto-nav, tap collapses chat sheet then navigates.
 */
export function FlightResultMessage({ message }: FlightResultMessageProps) {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const isMdUp = useIsMdUp();

  const extraData = message.extraData;
  const isHistoryMessage = Boolean(extraData?._isFromHistory);
  const summaryText = getFlightSearchMessageSummary(message.content?.messages?.[0]?.text ?? '');
  const canView = useMemo(() => canNavigateFlightMessage(message), [message]);

  const handleViewFlights = () => {
    if (!extraData || !canView) return;

    trackEvent('chat_view_flights_clicked', {
      result_type: message.type,
      is_history: isHistoryMessage,
    });

    if (!isMdUp) {
      // Collapse chat panel so the flights view isn't obscured on mobile.
      dispatch(setChatState('resting'));
    }

    const target = isAuthenticated
      ? ROUTES.FLIGHTS_SEARCH
      : ROUTES.PUBLIC_CHAT_FLIGHTS_SEARCH;

    if (message.type === 'flight_search_results') {
      if (isHistoryMessage) {
        const ok = hydrateFlightSearchParamsForFreshSearch(dispatch, extraData);
        if (!ok) return;
        navigate(target, { state: { fromChat: true } });
        return;
      }
      const extracted = hydrateFlightSearchResultsFromPayload(dispatch, extraData);
      if (!extracted) return;
      // TODO(#1060): remove this `[FlightChat] 2/3` DEV log once cache-hit behaviour
      // has stabilised in staging/production (paired with 1/3 + 3/3 logs).
      if (import.meta.env.DEV) {
        console.log('[FlightChat] 2/3 Navigating to', target, '(Redux already hydrated, no ?q= param)');
      }
      navigate(target, { state: { fromChat: true } });
      return;
    }

    if (message.type === 'multicity_flight_search_results') {
      if (isHistoryMessage) {
        const ok = hydrateMulticityFlightSearchParamsForFreshSearch(dispatch, extraData);
        if (!ok) return;
        navigate(target, { state: { fromChat: true } });
        return;
      }
      const normalized = hydrateMulticityFlightSearchResultsFromPayload(dispatch, extraData);
      if (!normalized) return;
      navigate(target, { state: { fromChat: true } });
      return;
    }

    if (message.type === 'flight_date_range_results') {
      // date_range results always trigger a fresh search (no useful session data to cache)
      const result = hydrateFlightDateRangeFromPayload(dispatch, extraData);
      if (!result?.extracted) return;
      navigate(target, { state: { fromChat: true } });
    }
  };

  if (!canView) {
    return <ErrorFallback />;
  }

  // Both mobile and desktop: summary text + "View flights" CTA.
  // Auto-nav on desktop is handled by applySuccessfulChatResponse; mobile waits for user tap.
  return (
    <Transition mounted transition="fade" duration={300}>
      {(styles) => (
        <Box style={{ ...styles, marginBottom: 16 }}>
          <Group align="flex-start" gap={8} wrap="nowrap" style={{ maxWidth: '85%' }}>
            <Avatar
              src={chatConfig.avatars.bot}
              alt="Bot"
              size={32}
              radius="xl"
              style={{ flexShrink: 0 }}
            />
            <Box style={RESULT_BUBBLE_STYLE}>
              <Text size="sm" style={{ marginBottom: 12, whiteSpace: 'pre-wrap' }}>
                {summaryText}
              </Text>
              <Group wrap="wrap" align="center" gap={8}>
                <Button
                  size="xs"
                  leftSection={<Plane size={18} />}
                  onClick={handleViewFlights}
                  style={{ fontWeight: 600 }}
                >
                  View flights
                </Button>
                {message.messageId ? <FeedbackButtons messageId={message.messageId} /> : null}
              </Group>
            </Box>
          </Group>
        </Box>
      )}
    </Transition>
  );
}

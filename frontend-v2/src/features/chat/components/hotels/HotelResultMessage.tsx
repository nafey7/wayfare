import { useEffect, useMemo, useRef, type CSSProperties } from 'react';
import { useNavigate } from 'react-router-dom';
import { Avatar, Box, Button, Group, Text, Transition } from '@mantine/core';
import { Hotel as HotelIcon } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store';
import { selectIsAuthenticated } from '@/store/slices/authSlice';
import { setChatState } from '@/store/slices/uiSlice';
import { chatConfig } from '@/features/chat/styles/chatTheme';
import type { ChatMessage } from '@/types/chat';
import { isHotelSearchResults } from '@/types/chat';
import { extractHotelSearchResults } from '@/types/api.helpers';
import { getHotelSearchMessageSummary } from '@/features/chat/utils/messageUtils';
import {
  hydrateHotelSearchResultsFromPayload,
  hydrateHotelSearchParamsForFreshSearch,
} from '@/features/chat/utils/hydrateHotelRecommendationsFromChatResponse';
import { ROUTES } from '@/features/routing';
import { trackEvent } from '@/utils/gtm';
import { useIsMdUp } from '@/hooks/useIsMdUp';
import { FeedbackButtons } from '@/features/chat/components/flights/FeedbackButtons';

interface HotelResultMessageProps {
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
            Unable to display hotel results. Please try searching again.
          </Text>
        </Box>
      )}
    </Transition>
  );
}

function canNavigateHotelMessage(message: ChatMessage): boolean {
  return extractHotelSearchResults(message.extraData) !== null;
}

/**
 * Hotel rich-result bubble.
 * - Desktop (md+): intro summary + "View hotels" CTA; auto-nav handled by applySuccessfulChatResponse.
 * - Mobile (below md): same summary + CTA; no auto-nav, tap collapses chat sheet then navigates.
 */
function HotelResultMessageInner({ message }: HotelResultMessageProps) {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const isMdUp = useIsMdUp();

  const extraData = message.extraData;
  const isHistoryMessage = Boolean(extraData?._isFromHistory);
  const summaryText = getHotelSearchMessageSummary(
    message.content?.messages?.[0]?.text ?? '',
    message.extraData as Record<string, unknown> | undefined
  );
  const canView = useMemo(() => canNavigateHotelMessage(message), [message]);

  const resultsShownFiredRef = useRef(false);
  useEffect(() => {
    if (!canView || resultsShownFiredRef.current) return;
    resultsShownFiredRef.current = true;
    const extracted = extractHotelSearchResults(extraData);
    const sp = extracted?.data?.search_params as Record<string, unknown> | undefined;
    trackEvent('hotel_search_results_shown', {
      source: 'chat',
      search_session_id: extracted?.session_id || undefined,
      destination_city: sp
        ? String(sp.destination_city ?? sp.destination ?? sp.city_name ?? '')
        : undefined,
      country: sp ? (sp.country ?? sp.country_name) : undefined,
      check_in_date: sp ? (sp.check_in_date ?? sp.checkin) : undefined,
      check_out_date: sp ? (sp.check_out_date ?? sp.checkout) : undefined,
      rooms: sp?.rooms as number | undefined,
      adults: sp?.adults as number | undefined,
      children: sp?.children as number | undefined,
    });
  }, [canView, extraData]);

  const handleViewHotels = () => {
    if (!extraData || !canView) return;

    trackEvent('chat_view_hotels_clicked', {
      result_type: message.type,
      is_history: isHistoryMessage,
    });

    if (!isMdUp) {
      // Collapse chat panel so the hotels view isn't obscured on mobile.
      dispatch(setChatState('resting'));
    }

    const target = isAuthenticated
      ? ROUTES.HOTELS_SEARCH
      : ROUTES.PUBLIC_CHAT_HOTELS_SEARCH;

    if (isHistoryMessage) {
      const ok = hydrateHotelSearchParamsForFreshSearch(dispatch, extraData);
      if (!ok) return;
      navigate(target, { state: { fromChat: true } });
      return;
    }

    const extracted = hydrateHotelSearchResultsFromPayload(dispatch, extraData);
    if (!extracted) return;
    navigate(target, {
      state: { fromChat: true },
    });
  };

  if (!canView) {
    return <ErrorFallback />;
  }

  // Both mobile and desktop: summary text + "View hotels" CTA.
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
                  leftSection={<HotelIcon size={18} />}
                  onClick={handleViewHotels}
                  style={{ fontWeight: 600 }}
                >
                  View hotels
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

export function HotelResultMessage({ message }: HotelResultMessageProps) {
  if (!isHotelSearchResults(message)) {
    return null;
  }
  return <HotelResultMessageInner message={message} />;
}

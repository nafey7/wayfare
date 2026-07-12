import { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Avatar, Box, Button, Text, Transition } from '@mantine/core';
import { Map as MapIcon, Bookmark as BookmarkIcon } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store';
import { selectIsAuthenticated } from '@/store/slices/authSlice';
import { selectChatId } from '@/store/slices/chatSlice';
import { setChatState } from '@/store/slices/uiSlice';
import { ROUTES } from '@/features/routing';
import { isPublicChatRoute } from '@/features/routing/constants';
import { usePublicChatConversionGate } from '@/features/chat/hooks/usePublicChatConversionGate';
import { chatConfig } from '@/features/chat/styles/chatTheme';
import type { ChatMessage } from '@/types/chat';
import { isItinerarySearchResults } from '@/types/chat';
import { trackEvent } from '@/utils/gtm';
import { navigateItineraryFromChatExtraData } from '@/features/chat/utils/itineraryNavigateFromChatExtraData';
import { useIsMdUp } from '@/hooks/useIsMdUp';

interface ItineraryResultMessageProps {
  message: ChatMessage;
}

/**
 * Itinerary result card in chat.
 * Mobile and desktop both show message text + "View itinerary" button.
 * Desktop auto-navigates via applySuccessfulChatResponse; mobile waits for the user to tap.
 */
export function ItineraryResultMessage({ message }: ItineraryResultMessageProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useAppDispatch();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const chatId = useAppSelector(selectChatId);
  const isMdUp = useIsMdUp();
  const { ensureAuthenticated } = usePublicChatConversionGate();
  const isPublicRoute = isPublicChatRoute(location.pathname);

  const messageText =
    message.content?.messages?.[0]?.text ??
    "Here's your itinerary! View the full plan below.";
  const extraData = message.extraData as Record<string, unknown> | undefined;
  const sessionId = extraData?.session_id as string | undefined;
  const destination = (extraData?.destination as string | undefined) ?? undefined;

  useEffect(() => {
    if (isItinerarySearchResults(message)) {
      trackEvent('itinerary_results_shown', {
        source: 'chat',
        session_id: sessionId,
        destination,
      });
    }
  }, [message, sessionId, destination]);

  const handleViewItinerary = () => {
    trackEvent('chat_view_itinerary_clicked', {
      session_id: sessionId,
      destination,
    });
    if (!isMdUp) {
      // Collapse chat panel so the itinerary view isn't obscured on mobile.
      dispatch(setChatState('resting'));
    }
    const routePrefix = isAuthenticated ? '' : ROUTES.PUBLIC_CHAT;
    navigateItineraryFromChatExtraData(dispatch, navigate, extraData, routePrefix, chatId);
  };

  return (
    <Transition mounted transition="fade" duration={300}>
      {(styles) => (
        <Box style={{ ...styles, marginBottom: 16 }}>
          <Box
            style={{
              display: 'flex',
              flexDirection: 'row',
              alignItems: 'flex-start',
              gap: 8,
              maxWidth: isMdUp ? '85%' : undefined,
            }}
          >
            <Avatar
              src={chatConfig.avatars.bot}
              alt="Bot"
              size={32}
              radius="xl"
              style={{ flexShrink: 0 }}
            />
            <Box
              style={{
                flex: 1,
                minWidth: 0,
                backgroundColor: 'white',
                borderRadius: '8px 8px 8px 0px',
                boxShadow:
                  '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
                padding: 12,
                border: '1px solid var(--mantine-color-gray-3)',
              }}
            >
              <Text size="sm" style={{ marginBottom: 12, whiteSpace: 'pre-wrap' }}>
                {messageText}
              </Text>

              <Box style={{ display: 'flex', flexDirection: 'row', gap: 8, flexWrap: 'wrap' }}>
                <Button
                  size="xs"
                  leftSection={<MapIcon size={18} />}
                  onClick={handleViewItinerary}
                  styles={{ root: { fontWeight: 600 } }}
                >
                  View itinerary
                </Button>
                {isPublicRoute && !isAuthenticated && (
                  <Button
                    size="xs"
                    variant="outline"
                    leftSection={<BookmarkIcon size={18} />}
                    onClick={() => {
                      trackEvent('chat_save_itinerary_clicked', {
                        source: 'public_chat',
                        session_id: sessionId,
                        destination,
                      });
                      ensureAuthenticated('itinerary_save');
                    }}
                    styles={{ root: { fontWeight: 600 } }}
                  >
                    Save itinerary
                  </Button>
                )}
              </Box>
            </Box>
          </Box>
        </Box>
      )}
    </Transition>
  );
}

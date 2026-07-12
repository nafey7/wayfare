import { useRef, useEffect } from 'react';
import { Box, Avatar, Text, ActionIcon, Textarea, Group, Paper, Stack } from '@mantine/core';
import { SendHorizonal, User as UserIcon } from 'lucide-react';
import { motion } from 'framer-motion';
import { useChatContext } from '../context/useChatContext';
import { renderMarkdown, TypingIndicator } from './chatUtils';
import './chat.css';
import { chatConfig } from '@/features/chat/styles/chatTheme';
import { useAppSelector } from '@/store';
import { selectCurrentUser } from '@/store/slices/authSlice';
import { selectStreamingItinerary } from '@/store/slices/chatSlice';
import { FlightResultMessage } from '@/features/chat/components/flights/FlightResultMessage';
import { ItineraryResultMessage } from '@/features/chat/components/itinerary/ItineraryResultMessage';
import { StreamingItinerarySkeleton } from '@/features/itinerary/components/StreamingItinerarySkeleton';
import { ChatErrorBoundary } from './ErrorBoundary';
import { SuggestedReplies } from './SuggestedReplies';
import { useUrlPromptSend } from '@/features/chat/hooks/useUrlPromptSend';
import { trackEvent } from '@/utils/gtm';
import { useActiveSuggestions } from '../hooks/useActiveSuggestions';
import { HotelResultMessage } from '@/features/chat/components/hotels/HotelResultMessage';

export interface ChatPanelProps {
  inputPlaceholder?: string;
  disclaimerText?: string;
  /**
   * Intent marker for the panel's layout context. Currently unused internally
   * (all variants render identically), but retained so call sites can declare
   * intent and future variant-specific styling has a prop to key off.
   * 'sidebar' = 30% column layout; 'standalone' = full-width chat-only view.
   */
  variant?: 'sidebar' | 'standalone';
}

const VOYA_AVATAR = chatConfig.avatars.bot;

function getUserInitial(
  firstName: string | null,
  lastName: string | null,
  email: string,
): string {
  const f = firstName?.trim();
  if (f && f.length > 0) return f.charAt(0).toUpperCase();
  const l = lastName?.trim();
  if (l && l.length > 0) return l.charAt(0).toUpperCase();
  const local = email?.split('@')[0]?.trim();
  if (local && local.length > 0) return local.charAt(0).toUpperCase();
  return '?';
}


export function ChatPanel({
  inputPlaceholder = 'Type your message...',
  disclaimerText = 'AI responses may contain errors. Please verify important information.',
  variant: _variant = 'sidebar',
}: ChatPanelProps = {}) {
  const {
    messages,
    sendMessage,
    chatInput,
    setChatInput,
    loading,
    messagesLoaded,
    config,
    chatId,
  } = useChatContext();
  const { activeSuggestions, dismiss: dismissSuggestions } = useActiveSuggestions(messages);
  const user = useAppSelector(selectCurrentUser);
  // #1117 piece 4 — when the streaming chat hook is mid-itinerary (stage-1
  // skeleton has emitted day titles or stage-2 is filling activities) we
  // swap the chat's three-dot typing indicator for a day-card skeleton so
  // the user sees concrete progress within ~5-7 s instead of staring at a
  // dot animation for the full ~30 s LLM budget. The slot stays `active:
  // false` for flight / hotel / general agent turns (they don't emit
  // `itinerary_partial` events), so the typing indicator behavior on those
  // paths is unchanged.
  const streamingItinerary = useAppSelector(selectStreamingItinerary);
  const userInitial = user
    ? getUserInitial(user.firstName, user.lastName, user.email)
    : null;
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const shouldRefocusRef = useRef(false);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (!loading && shouldRefocusRef.current) {
      shouldRefocusRef.current = false;
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [loading]);

  useUrlPromptSend({
    messagesLoaded,
    messages,
    publicChatEnabled: config.publicChatEnabled,
    sendMessage,
  });

  const isButtonDisabled = loading || !chatInput.trim();

  const handleSend = () => {
    const text = chatInput.trim();
    if (text && !loading) {
      shouldRefocusRef.current = true;
      sendMessage(text);
    }
  };

  return (
    <Box
        style={{
          height: '100%',
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: 'var(--mantine-color-gray-0)',
        }}
      >
        {/* Messages */}
        <Box
          style={{
            flex: 1,
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            padding: '24px',
            scrollbarWidth: 'none',
          }}
        >
          <Stack gap={0}>
            {messages.map((msg) => {
              if (msg.type === 'itinerary_results') {
                return (
                  <Box key={msg._id} mb={16}>
                    <ChatErrorBoundary fallbackMessage="Unable to display itinerary. Please try again.">
                      <ItineraryResultMessage message={msg} />
                    </ChatErrorBoundary>
                  </Box>
                );
              }

              if (
                msg.type === 'flight_search_results' ||
                msg.type === 'flight_date_range_results' ||
                msg.type === 'multicity_flight_search_results'
              ) {
                return (
                  <Box key={msg._id} mb={16}>
                    <ChatErrorBoundary fallbackMessage="Unable to display flight results. Please try searching again.">
                      <FlightResultMessage message={msg} />
                    </ChatErrorBoundary>
                  </Box>
                );
              }

              if (msg.type === 'hotel_search_results') {
                return (
                  <Box key={msg._id} mb={16}>
                    <ChatErrorBoundary fallbackMessage="Unable to display hotel results. Please try searching again.">
                      <HotelResultMessage message={msg} />
                    </ChatErrorBoundary>
                  </Box>
                );
              }

              const isBot = msg.from === 'bot';
              const isTyping = msg.type === 'typing';
              const text = msg.content?.messages?.[0]?.text ?? '';

              return (
                <Box
                  key={msg._id}
                  mb={12}
                  style={{
                    display: 'flex',
                    justifyContent: isBot ? 'flex-start' : 'flex-end',
                    alignItems: 'flex-end',
                    gap: 8,
                  }}
                >
                  {isBot && (
                    <Avatar src={VOYA_AVATAR} alt="Voya" size={32} style={{ flexShrink: 0 }} />
                  )}

                  <Box
                    style={{
                      // When streaming an itinerary, give the skeleton room
                      // to render full-width day cards. The classic 85% cap
                      // still applies to typing-only and to regular bubbles.
                      maxWidth:
                        isTyping && streamingItinerary.active ? '100%' : '85%',
                      flex:
                        isTyping && streamingItinerary.active ? 1 : undefined,
                    }}
                  >
                    {isTyping ? (
                      streamingItinerary.active ? (
                        <StreamingItinerarySkeleton />
                      ) : (
                        <Box
                          style={{
                            backgroundColor: 'white',
                            borderRadius: '8px 8px 8px 0px',
                            boxShadow: 'var(--mantine-shadow-sm)',
                            padding: '10px 14px',
                          }}
                        >
                          <TypingIndicator />
                        </Box>
                      )
                    ) : (
                      <motion.div
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ type: 'spring', stiffness: 260, damping: 20 }}
                      >
                        <Box
                          style={{
                            backgroundColor: isBot
                              ? 'white'
                              : 'var(--mantine-color-navy-7)',
                            color: isBot
                              ? 'var(--mantine-color-dark-7)'
                              : 'white',
                            borderRadius: isBot ? '8px 8px 8px 0px' : '8px 8px 0px 8px',
                            boxShadow: 'var(--mantine-shadow-sm)',
                            padding: '10px 14px',
                            wordBreak: 'break-word',
                          }}
                        >
                          {isBot ? (
                            <Text
                              component="div"
                              size="sm"
                              style={{ lineHeight: 1.55 }}
                              className="voya-chat-markdown"
                              dangerouslySetInnerHTML={{ __html: renderMarkdown(text) }}
                            />
                          ) : (
                            <Text size="sm" style={{ lineHeight: 1.55, color: 'white' }}>
                              {text}
                            </Text>
                          )}
                        </Box>
                      </motion.div>
                    )}
                  </Box>

                  {!isBot && (
                    <Avatar
                      size={32}
                      style={{
                        flexShrink: 0,
                        backgroundColor: 'var(--mantine-color-gray-4)',
                        color: 'white',
                        fontWeight: 600,
                      }}
                    >
                      {user ? userInitial : <UserIcon size={18} />}
                    </Avatar>
                  )}
                </Box>
              );
            })}
            <div ref={endRef} />
          </Stack>
        </Box>

        {/* Input area */}
        <Box px={24} pt={0} pb={16}>
          <SuggestedReplies
            suggestions={activeSuggestions}
            omitHorizontalPadding
            onSelect={(suggestion) => {
              trackEvent('chat_suggestion_clicked', {
                suggestion_title: suggestion.title,
                chat_id: chatId ?? undefined,
              });
              dismissSuggestions();
              sendMessage(suggestion.command);
            }}
          />

          <Paper
            radius="lg"
            withBorder
            style={{ overflow: 'hidden' }}
          >
            <Group gap={8} align="flex-end" px={16} py={10}>
              <Textarea
                ref={inputRef}
                placeholder={inputPlaceholder}
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey && !isButtonDisabled) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                autosize
                minRows={1}
                maxRows={4}
                autoFocus
                variant="unstyled"
                style={{ flex: 1 }}
                styles={{
                  input: {
                    fontSize: '0.95rem',
                    padding: '2px 0',
                    resize: 'none',
                    lineHeight: 1.5,
                  },
                }}
              />
              <motion.div
                whileHover={isButtonDisabled ? {} : { scale: 1.08 }}
                whileTap={isButtonDisabled ? {} : { scale: 0.92 }}
              >
                <ActionIcon
                  color="navy"
                  size={36}
                  radius="xl"
                  onClick={handleSend}
                  disabled={isButtonDisabled}
                  variant={chatInput.trim() ? 'filled' : 'subtle'}
                  aria-label="Send message"
                  mb={2}
                >
                  <SendHorizonal size={16} />
                </ActionIcon>
              </motion.div>
            </Group>
          </Paper>

          <Text size="xs" c="dimmed" ta="center" mt={8}>
            {disclaimerText}
          </Text>
        </Box>
      </Box>
  );
}

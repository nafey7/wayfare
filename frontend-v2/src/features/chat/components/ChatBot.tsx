import { useEffect } from 'react';
import { zIndex } from '@/theme';
import { ActionIcon, Avatar, Box, Indicator, Paper, Transition } from '@mantine/core';
import { AnimatePresence, motion } from 'framer-motion';
import { useChatContext } from '../context/useChatContext';
import { trackEvent } from '@/utils/gtm';
import { useChatScroll } from '../hooks/useChatScroll';
import { ChatHeader } from './ChatHeader';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { SuggestedReplies } from './SuggestedReplies';
import { chatConfig } from '../styles/chatTheme';
import { useUrlPromptSend } from '@/features/chat/hooks/useUrlPromptSend';
import { useActiveSuggestions } from '../hooks/useActiveSuggestions';
import type { ChatSuggestion } from '@/types/chat';

interface ChatBotProps {
  embedded?: boolean;
}

/**
 * Main ChatBot component
 * Renders as a floating chat widget with animations.
 * Now relies on the app-level MantineProvider — no per-tree theme override
 * (the legacy `chatBotTheme` MUI theme was dropped in M3 migration).
 */
export function ChatBot({ embedded = false }: ChatBotProps) {
  const {
    messages,
    chatId,
    chatInput,
    setChatInput,
    sendMessage,
    clearChat,
    isOpen,
    openChat,
    closeChat,
    soundEnabled,
    toggleSound,
    autoScroll,
    toggleAutoScroll,
    isFullScreen,
    toggleFullScreen,
    loading,
    unreadCount,
    messagesLoaded,
    config,
  } = useChatContext();

  const isChatVisible = embedded || isOpen;

  const { containerRef, messagesEndRef } = useChatScroll({
    messages,
    autoScroll,
    isOpen: isChatVisible,
  });

  // Embedded chat should always be treated as open for chat behavior (auto-scroll, unread count).
  useEffect(() => {
    if (embedded) {
      openChat();
    }
  }, [embedded, openChat]);

  useUrlPromptSend({
    messagesLoaded,
    messages,
    publicChatEnabled: config.publicChatEnabled,
    sendMessage,
    openChat,
  });

  const { activeSuggestions, dismiss: dismissSuggestions } = useActiveSuggestions(messages);

  const handleSuggestionClick = (suggestion: ChatSuggestion) => {
    trackEvent('chat_suggestion_clicked', {
      suggestion_title: suggestion.title,
      chat_id: chatId ?? undefined,
    });
    dismissSuggestions();
    sendMessage(suggestion.command);
  };

  // Render minimized chat button only for floating widget mode
  if (!embedded && !isOpen) {
    return (
      <Box
        style={{
          position: 'fixed',
          bottom: 16,
          right: 16,
          zIndex: zIndex.detailModal,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-end',
          gap: 16,
        }}
      >
        <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} whileHover={{ scale: 1.1 }}>
          <Indicator
            label={unreadCount > 0 ? unreadCount : undefined}
            color="red"
            disabled={!unreadCount}
            size={16}
          >
            <ActionIcon
              variant="filled"
              color="indigo"
              size="xl"
              radius="xl"
              onClick={openChat}
              styles={{
                root: {
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                  padding: 4,
                  '&:hover': { backgroundColor: 'var(--mantine-color-gray-1)' },
                },
              }}
            >
              <Avatar
                src={chatConfig.avatars.bot}
                size={48}
                radius="xl"
                color="indigo"
                style={{ fontSize: 20 }}
              >
                💬
              </Avatar>
            </ActionIcon>
          </Indicator>
        </motion.div>
      </Box>
    );
  }

  const containerStyles = embedded
    ? {
        position: 'relative' as const,
        width: '100%',
        height: '100%',
        borderRadius: 8,
      }
    : {
        position: 'fixed' as const,
        width: isFullScreen ? '100vw' : 400,
        height: isFullScreen ? '100%' : 600,
        bottom: isFullScreen ? 0 : 16,
        right: isFullScreen ? 0 : 16,
        left: isFullScreen ? 0 : 'auto',
        top: isFullScreen ? 0 : 'auto',
        borderRadius: isFullScreen ? 0 : 8,
        boxShadow: isFullScreen ? 'none' : '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
      };

  // Render full chat interface
  return (
    <AnimatePresence>
      <motion.div
        initial={embedded ? false : { width: 400, height: 600, bottom: 16, right: 16, borderRadius: 8 }}
        animate={containerStyles}
        transition={embedded ? { duration: 0 } : chatConfig.animation.spring}
        style={{
          display: 'flex',
          flexDirection: 'column',
          zIndex: embedded ? 'auto' : zIndex.detailModal,
          overflow: 'hidden',
        }}
        id="chat-container"
      >
        <Paper
          shadow="none"
          style={{
            width: '100%',
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            borderRadius: embedded ? 0 : isFullScreen ? 0 : 16,
            overflow: 'hidden',
          }}
        >
          {!embedded && (
            <ChatHeader
              onClose={closeChat}
              onClearChat={clearChat}
              soundEnabled={soundEnabled}
              onToggleSound={toggleSound}
              autoScroll={autoScroll}
              onToggleAutoScroll={toggleAutoScroll}
              isFullScreen={isFullScreen}
              onToggleFullScreen={toggleFullScreen}
              showCloseButton
              showFullScreenButton
            />
          )}

          <Box
            ref={containerRef}
            style={{
              flex: 1,
              minHeight: 0,
              display: 'flex',
              justifyContent: 'center',
              backgroundColor: 'var(--mantine-color-gray-1)',
              overflowY: 'auto',
              overscrollBehavior: 'contain',
              scrollbarWidth: 'none',
            }}
          >
            <Box
              style={{
                paddingBlock: 16,
                paddingInline: embedded ? 64 : 16,
                width: '100%',
                maxWidth: embedded ? '100%' : isFullScreen ? 600 : '100%',
                minHeight: 0,
                position: 'relative',
              }}
            >
              <Transition mounted transition="fade" duration={500}>
                {(styles) => (
                  <Box style={styles}>
                    {messages.map((message) => (
                      <ChatMessage key={message._id} message={message} />
                    ))}
                  </Box>
                )}
              </Transition>
              <div ref={messagesEndRef} />
            </Box>
          </Box>

          <Box
            style={{
              width: '100%',
              backgroundColor: 'var(--mantine-color-gray-1)',
              position: 'sticky',
              bottom: 0,
              left: 0,
              right: 0,
              zIndex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
            }}
          >
            <Box
              style={{
                width: '100%',
                maxWidth: embedded ? '100%' : isFullScreen ? 600 : '100%',
              }}
            >
              <SuggestedReplies
                suggestions={activeSuggestions}
                onSelect={handleSuggestionClick}
              />
              <ChatInput
                value={chatInput}
                onChange={setChatInput}
                onSend={sendMessage}
                loading={loading}
                placeholder="Type your message..."
              />
            </Box>
          </Box>
        </Paper>
      </motion.div>
    </AnimatePresence>
  );
}

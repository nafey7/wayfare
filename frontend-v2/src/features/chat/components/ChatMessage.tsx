import { Box, Avatar, Text } from '@mantine/core';
import { motion } from 'framer-motion';
import type { ChatMessage as ChatMessageType } from '@/types/chat';
import { chatConfig } from '../styles/chatTheme';
import { HotelResultMessage } from '@/features/chat/components/hotels/HotelResultMessage';
import { FlightResultMessage } from '@/features/chat/components/flights/FlightResultMessage';
import { ItineraryResultMessage } from './itinerary';
import { ChatErrorBoundary } from './ErrorBoundary';
import { renderMarkdown, TypingIndicator } from './chatUtils';
import './chat.css';

interface ChatMessageProps {
  message: ChatMessageType;
}

export function ChatMessage({ message }: ChatMessageProps) {
  if (message.type === 'itinerary_results') {
    return (
      <ChatErrorBoundary fallbackMessage="Unable to display itinerary. Please try again.">
        <ItineraryResultMessage message={message} />
      </ChatErrorBoundary>
    );
  }

  if (
    message.type === 'flight_search_results' ||
    message.type === 'flight_date_range_results' ||
    message.type === 'multicity_flight_search_results'
  ) {
    return (
      <ChatErrorBoundary fallbackMessage="Unable to display flight results. Please try searching again.">
        <FlightResultMessage message={message} />
      </ChatErrorBoundary>
    );
  }

  if (message.type === 'hotel_search_results') {
    return (
      <ChatErrorBoundary fallbackMessage="Unable to display hotel results. Please try searching again.">
        <HotelResultMessage message={message} />
      </ChatErrorBoundary>
    );
  }

  const isBot = message.from === 'bot';
  const isTyping = message.type === 'typing';
  const messages = message.content.messages || [];

  return (
    <>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
        style={{ marginBottom: 16 }}
      >
        <Box
          style={{
            display: 'flex',
            justifyContent: isBot ? 'flex-start' : 'flex-end',
            alignItems: 'flex-end',
            gap: 8,
            marginBottom: 8,
          }}
        >
          {isBot && (
            <Avatar src={chatConfig.avatars.bot} alt="Bot" size={32} style={{ flexShrink: 0 }} />
          )}

          <Box style={{ maxWidth: '80%' }}>
            {isTyping ? (
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
            ) : (
              <>
                {messages.map((item, index) => (
                  <motion.div
                    key={`msg-${index}`}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ type: 'spring', stiffness: 260, damping: 20 }}
                    style={{ marginBottom: index > 0 ? 16 : 0 }}
                  >
                    <Box
                      style={{
                        backgroundColor: isBot ? 'white' : 'var(--mantine-color-navy-7)',
                        color: isBot ? 'var(--mantine-color-dark-7)' : 'white',
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
                          dangerouslySetInnerHTML={{ __html: renderMarkdown(item?.text || '') }}
                        />
                      ) : (
                        <Text
                          size="sm"
                          style={{ lineHeight: 1.55, whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: 'white' }}
                        >
                          {item?.text || ''}
                        </Text>
                      )}
                    </Box>
                  </motion.div>
                ))}
              </>
            )}
          </Box>

          {!isBot && <Box style={{ width: 32, height: 32, flexShrink: 0 }} />}
        </Box>
      </motion.div>
    </>
  );
}

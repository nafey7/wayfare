import type { ChatMessage, ChatMessageContent } from '@/types/chat';

/**
 * Create a user message object
 */
export function createUserMessage(text: string): ChatMessage {
  return {
    _id: crypto.randomUUID(),
    content: {
      messages: [{ text }],
    },
    from: 'user',
    type: 'message',
    contentType: 'message',
    timestamp: new Date().toISOString(),
  };
}

/**
 * Create a typing indicator message
 */
export function createTypingMessage(): ChatMessage {
  return {
    _id: crypto.randomUUID(),
    content: {
      messages: [{ text: '' }],
    },
    from: 'bot',
    type: 'typing',
    contentType: 'message',
    timestamp: new Date().toISOString(),
    status: 10,
  };
}

/**
 * Validate and convert API response type to ChatMessageType
 */
export function toMessageType(type: string): ChatMessage['type'] {
  const validTypes: ChatMessage['type'][] = [
    'message',
    'typing',
    'flight_search_results',
    'multicity_flight_search_results',
    'flight_date_range_results',
    'hotel_search_results',
    'itinerary_results',
  ];
  return validTypes.includes(type as ChatMessage['type'])
    ? (type as ChatMessage['type'])
    : 'message';
}

/**
 * Create a bot message from API response
 */
export function createBotMessage(
  text: string,
  messageId?: string,
  type: string = 'message',
  extraData?: Record<string, unknown>,
  content?: Partial<ChatMessageContent>
): ChatMessage {
  const suggestions =
    (extraData?.suggestions as Array<{ title: string; command: string }>) || content?.suggestions;

  return {
    _id: crypto.randomUUID(),
    content: {
      messages: [{ text }],
      ...content,
      ...(suggestions && { suggestions }),
    },
    from: 'bot',
    type: toMessageType(type),
    contentType: content?.form ? 'form' : 'message',
    timestamp: new Date().toISOString(),
    messageId,
    extraData,
  };
}

/**
 * Raw backend chat-history message shape returned by `GET /chat/{chatId}/history`.
 * Frontend ChatMessage shape differs (camelCase keys, `from`/`content`); rebuild
 * via `rebuildHistoryMessages`.
 */
export interface RawHistoryMessage {
  sender?: string;
  message?: string;
  timestamp?: string;
  type?: string;
  extra_data?: Record<string, unknown>;
}

/**
 * Convert backend history payload into frontend ChatMessage[]. Rich-result
 * bot messages get `extraData._isFromHistory = true` so result components
 * know to trigger a fresh search instead of using stale session data.
 */
export function rebuildHistoryMessages(
  rawMessages: RawHistoryMessage[]
): ChatMessage[] {
  return rawMessages.map((msg) => {
    const text = msg.message ?? '';
    const isUser = (msg.sender ?? '').toLowerCase() === 'user';
    const extraData = msg.extra_data
      ? { ...msg.extra_data, _isFromHistory: true }
      : undefined;
    const base = isUser
      ? createUserMessage(text)
      : createBotMessage(text, undefined, msg.type ?? 'message', extraData);
    return {
      ...base,
      timestamp: msg.timestamp ?? base.timestamp,
    };
  });
}

import { vi } from 'vitest';
import type { ChatContextValue } from '@/features/chat/context/ChatContext';
import type { FrontendConfig } from '@/types/chat';

const stubConfig: FrontendConfig = {
  chatFeedbackEnabled: false,
  publicChatEnabled: true,
  langgraphFlightsEnabled: true,
  langgraphHotelsEnabled: true,
  environment: 'test',
};

/**
 * Full ChatContext value for unit tests (avoids ESM/alias issues with vi.mock of useChatContext).
 */
export function getStubChatContextValue(): ChatContextValue {
  return {
    messages: [],
    isTyping: false,
    chatId: null,
    chatInput: '',
    setChatInput: vi.fn(),
    sendMessage: vi.fn().mockResolvedValue(undefined),
    clearChat: vi.fn().mockResolvedValue(undefined),
    isOpen: false,
    openChat: vi.fn(),
    closeChat: vi.fn(),
    toggleChat: vi.fn(),
    soundEnabled: false,
    toggleSound: vi.fn(),
    autoScroll: true,
    toggleAutoScroll: vi.fn(),
    isFullScreen: false,
    toggleFullScreen: vi.fn(),
    isAuthenticated: false,
    loading: false,
    unreadCount: 0,
    messagesLoaded: true,
    config: stubConfig,
  };
}

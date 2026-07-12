import { fn } from 'storybook/test';
import type { ChatContextValue } from '@/features/chat/context/ChatContext';
import type { FrontendConfig } from '@/types/chat';

const stubConfig: FrontendConfig = {
  chatFeedbackEnabled: false,
  publicChatEnabled: true,
  langgraphFlightsEnabled: true,
  langgraphHotelsEnabled: true,
  environment: 'storybook',
};

/** Story-safe ChatContext stub — no API calls, no vi.fn(), no localStorage. */
export function getStubChatContextValue(): ChatContextValue {
  return {
    messages: [],
    isTyping: false,
    chatId: null,
    chatInput: '',
    setChatInput: fn(),
    sendMessage: fn().mockResolvedValue(undefined),
    clearChat: fn().mockResolvedValue(undefined),
    isOpen: false,
    openChat: fn(),
    closeChat: fn(),
    toggleChat: fn(),
    soundEnabled: false,
    toggleSound: fn(),
    autoScroll: true,
    toggleAutoScroll: fn(),
    isFullScreen: false,
    toggleFullScreen: fn(),
    isAuthenticated: false,
    loading: false,
    unreadCount: 0,
    messagesLoaded: true,
    config: stubConfig,
  };
}

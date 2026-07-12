import type { Meta, StoryObj } from '@storybook/react-vite';
import React, { useState } from 'react';
import { within } from 'storybook/test';
import { ChatPanel } from './ChatPanel';
import { ChatContext, type ChatContextValue } from '../context/ChatContext';
import type { ChatMessage, FrontendConfig } from '@/types/chat';
import { PHONE_VIEWPORT } from '@/stories/helpers/viewports';

const defaultConfig: FrontendConfig = {
  chatFeedbackEnabled: false,
  publicChatEnabled: true,
  langgraphFlightsEnabled: true,
  langgraphHotelsEnabled: true,
  environment: 'storybook',
};

const botMsg = (
  id: string,
  text: string,
  suggestions?: { title: string; command: string }[],
): ChatMessage => ({
  _id: id,
  from: 'bot',
  type: 'message',
  contentType: 'message',
  timestamp: new Date().toISOString(),
  content: { messages: [{ text }], suggestions: suggestions ?? [] },
});

const userMsg = (id: string, text: string): ChatMessage => ({
  _id: id,
  from: 'user',
  type: 'message',
  contentType: 'message',
  timestamp: new Date().toISOString(),
  content: { messages: [{ text }] },
});

const typingMsg = (): ChatMessage => ({
  _id: 'typing',
  from: 'bot',
  type: 'typing',
  contentType: 'message',
  timestamp: new Date().toISOString(),
  content: { messages: [] },
});

function MockChatProvider({
  children,
  messages,
}: {
  children: React.ReactNode;
  messages: ChatMessage[];
}) {
  const [input, setInput] = useState('');
  const value: ChatContextValue = {
    messages,
    isTyping: false,
    chatId: 'story-chat',
    chatInput: input,
    setChatInput: setInput,
    sendMessage: async () => {},
    clearChat: async () => {},
    isOpen: true,
    openChat: () => {},
    closeChat: () => {},
    toggleChat: () => {},
    soundEnabled: false,
    toggleSound: () => {},
    autoScroll: true,
    toggleAutoScroll: () => {},
    isFullScreen: false,
    toggleFullScreen: () => {},
    isAuthenticated: true,
    loading: false,
    unreadCount: 0,
    messagesLoaded: true,
    config: defaultConfig,
  };
  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}

const welcomeMessages: ChatMessage[] = [
  botMsg(
    '1',
    "Hi! 👋 I'm Voya, your AI travel assistant. Where would you like to go?",
    [
      { title: 'Search flights', command: 'Find me flights next month' },
      { title: 'Book a hotel', command: 'I need a hotel for my trip' },
      { title: 'Plan an itinerary', command: 'Plan a 5-day trip' },
    ],
  ),
];

const conversationMessages: ChatMessage[] = [
  botMsg('1', "Hi! 👋 I'm Voya, your AI travel assistant. Where would you like to go?"),
  userMsg('2', 'I want to fly from London to Tokyo next month'),
  botMsg(
    '3',
    "Great choice! Tokyo is amazing in **May**. Let me search for flights from London Heathrow (LHR) to Tokyo Narita (NRT).\n\nAny preferences?\n- Economy, Business or First class?\n- Direct flights only, or are stops ok?",
    [
      { title: 'Economy is fine', command: 'Economy class is fine' },
      { title: 'Direct only', command: 'Direct flights only please' },
    ],
  ),
];

const typingMessages: ChatMessage[] = [
  botMsg('1', "Hi! I'm Voya, your AI travel assistant."),
  userMsg('2', 'Find me flights to Tokyo in May'),
  typingMsg(),
];

const Panel = ({
  messages: msgs,
  variant,
}: {
  messages: ChatMessage[];
  variant?: 'sidebar' | 'standalone';
}) => (
  <MockChatProvider messages={msgs}>
    <div
      style={{
        height: 600,
        width: variant === 'standalone' ? 700 : 400,
        border: '1px solid #e4e6f5',
        borderRadius: 12,
        overflow: 'hidden',
      }}
    >
      <ChatPanel variant={variant} />
    </div>
  </MockChatProvider>
);

const meta: Meta = {
  title: 'Chat/ChatPanel',
  parameters: { layout: 'centered', initialEntries: ['/chat'] },
};

export default meta;
type Story = StoryObj;

export const Welcome: Story = {
  render: () => <Panel messages={welcomeMessages} />,
};

export const Conversation: Story = {
  render: () => <Panel messages={conversationMessages} />,
};

export const Typing: Story = {
  render: () => <Panel messages={typingMessages} />,
};

export const Standalone: Story = {
  render: () => <Panel messages={conversationMessages} variant="standalone" />,
};

/**
 * Mobile view (375 px) — verify the panel fills the phone width and the chat
 * input + bot greeting are reachable. Use this story to compare the chat layout
 * before/after the MUI → Mantine migration.
 */
export const Mobile: Story = {
  parameters: { viewport: PHONE_VIEWPORT, layout: 'fullscreen' },
  render: () => (
    <MockChatProvider messages={welcomeMessages}>
      <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
        <ChatPanel variant="sidebar" />
      </div>
    </MockChatProvider>
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    canvas.getByText(/voya/i);
  },
};

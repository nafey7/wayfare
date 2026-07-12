import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { ChatMessage, ConversationMeta, FrontendConfig, FeedbackState } from '@/types/chat';

/**
 * localStorage key for the active conversation id. Persisting it keeps the
 * user on the same conversation across page refreshes — without this, the
 * auto-select logic in ``useConversations`` would always reset them to the
 * most recent thread.
 */
const ACTIVE_CHAT_ID_KEY = 'voya_active_chat_id';

function loadPersistedChatId(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return window.localStorage.getItem(ACTIVE_CHAT_ID_KEY);
  } catch {
    return null;
  }
}

function persistChatId(value: string | null): void {
  if (typeof window === 'undefined') return;
  try {
    if (value) {
      window.localStorage.setItem(ACTIVE_CHAT_ID_KEY, value);
    } else {
      window.localStorage.removeItem(ACTIVE_CHAT_ID_KEY);
    }
  } catch {
    // localStorage unavailable (privacy mode, quota) — silently degrade.
  }
}

/**
 * Latest partial itinerary snapshot emitted by the streaming chat
 * endpoint (#1117). Holds whatever the LLM has parsed so far — day
 * titles arrive first, activities populate later — so the FE can render
 * skeleton day cards within ~6 s instead of after the full ~30 s LLM
 * call. Cleared by the streaming hook when the turn finishes (the
 * final ChatResponse takes over) or when the stream fails / falls back
 * to the non-streaming endpoint.
 */
export interface StreamingItineraryState {
  /** Most recent ``itinerary_partial`` payload — shape matches StructuredItineraryResult. */
  partial: Record<string, unknown> | null;
  /** True between the first ``itinerary_partial`` event and the final ``complete``/``error``. */
  active: boolean;
}

/**
 * Chat state shape
 */
export interface ChatState {
  messages: ChatMessage[];
  chatId: string | null;
  loading: boolean;
  config: FrontendConfig;
  configLoaded: boolean;
  feedbackSubmitted: FeedbackState;
  /** Multi-conversation sidebar list */
  conversations: ConversationMeta[];
  conversationsLoaded: boolean;
  /** Whether the conversation sidebar overlay is open (overlay on both desktop and mobile) */
  conversationSidebarOpen: boolean;
  /** Partial itinerary snapshot for skeleton-streaming render (#1117). */
  streamingItinerary: StreamingItineraryState;
}

const initialState: ChatState = {
  messages: [],
  chatId: loadPersistedChatId(),
  loading: false,
  config: {
    chatFeedbackEnabled: false,
    publicChatEnabled: false,
    langgraphFlightsEnabled: false,
    langgraphHotelsEnabled: false,
    environment: 'development',
  },
  configLoaded: false,
  feedbackSubmitted: {},
  conversations: [],
  conversationsLoaded: false,
  conversationSidebarOpen: false,
  streamingItinerary: { partial: null, active: false },
};

/**
 * Chat slice for managing chat state
 */
const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    /**
     * Set all messages
     */
    setMessages: (state, action: PayloadAction<ChatMessage[]>) => {
      state.messages = action.payload;
    },

    /**
     * Add a single message
     */
    addMessage: (state, action: PayloadAction<ChatMessage>) => {
      state.messages.push(action.payload);
    },

    /**
     * Update a message by ID
     */
    updateMessage: (
      state,
      action: PayloadAction<{ id: string; updates: Partial<ChatMessage> }>
    ) => {
      const index = state.messages.findIndex((m) => m._id === action.payload.id);
      if (index !== -1 && state.messages[index]) {
        state.messages[index] = { ...state.messages[index], ...action.payload.updates };
      }
    },

    /**
     * Remove typing indicator
     */
    removeTypingIndicator: (state) => {
      state.messages = state.messages.filter((m) => m.type !== 'typing');
    },

    /**
     * Clear all messages
     */
    clearMessages: (state) => {
      state.messages = [];
    },

    /**
     * Set chat ID
     */
    setChatId: (state, action: PayloadAction<string | null>) => {
      state.chatId = action.payload;
      persistChatId(action.payload);
    },

    /**
     * Set loading state
     */
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload;
    },

    /**
     * Set frontend config
     */
    setConfig: (state, action: PayloadAction<FrontendConfig>) => {
      state.config = action.payload;
      state.configLoaded = true;
    },

    /**
     * Mark config as loaded after frontend-config fetch completes without data (e.g. error).
     * Keeps default `config` values; avoids indefinite "loading" for consumers that gate on `configLoaded`.
     */
    markChatConfigHydrated: (state) => {
      state.configLoaded = true;
    },

    /**
     * Record feedback submission
     */
    setFeedbackSubmitted: (
      state,
      action: PayloadAction<{ messageId: string; feedbackType: 'thumbs_up' | 'thumbs_down' }>
    ) => {
      state.feedbackSubmitted[action.payload.messageId] = action.payload.feedbackType;
    },

    // --- Multi-conversation reducers ---

    /**
     * Set full conversations list (from API)
     */
    setConversations: (state, action: PayloadAction<ConversationMeta[]>) => {
      state.conversations = action.payload ?? [];
      state.conversationsLoaded = true;
    },

    /**
     * Prepend a newly created conversation
     */
    addConversation: (state, action: PayloadAction<ConversationMeta>) => {
      state.conversations.unshift(action.payload);
    },

    /**
     * Update conversation name in the list.
     * Upserts: if the conversation isn't in state (e.g. backend auto-created it
     * on the first message of a brand-new chat), insert a stub entry so the
     * sidebar reflects it immediately.
     */
    updateConversationName: (
      state,
      action: PayloadAction<{ chatId: string; name: string }>
    ) => {
      const conv = state.conversations.find((c) => c.chat_id === action.payload.chatId);
      if (conv) {
        conv.name = action.payload.name;
      } else {
        const now = new Date().toISOString();
        state.conversations.unshift({
          chat_id: action.payload.chatId,
          name: action.payload.name,
          message_count: 0,
          last_message_at: now,
          last_message_preview: '',
          created_at: now,
        });
      }
    },

    /**
     * Remove a conversation from the list (after deletion)
     */
    removeConversation: (state, action: PayloadAction<string>) => {
      state.conversations = state.conversations.filter(
        (c) => c.chat_id !== action.payload
      );
      // If the deleted conversation was the active one, clear the persisted
      // pointer so a refresh doesn't try to reload a 404 chat.
      if (state.chatId === action.payload) {
        state.chatId = null;
        persistChatId(null);
      }
    },

    /**
     * Update conversation metadata after a message is sent.
     * Upserts: if the conversation isn't in state (e.g. backend auto-created it
     * on the first message of a brand-new chat), insert a stub entry so the
     * sidebar reflects it immediately. The entry is refined by a subsequent
     * `updateConversationName` dispatch when the auto-generated name arrives.
     */
    updateConversationOnMessage: (
      state,
      action: PayloadAction<{ chatId: string; preview: string }>
    ) => {
      const now = new Date().toISOString();
      const preview = action.payload.preview.slice(0, 100);
      let conv = state.conversations.find((c) => c.chat_id === action.payload.chatId);
      if (!conv) {
        conv = {
          chat_id: action.payload.chatId,
          name: 'New conversation',
          message_count: 0,
          last_message_at: now,
          last_message_preview: preview,
          created_at: now,
        };
        state.conversations.unshift(conv);
      }
      conv.message_count += 1;
      conv.last_message_at = now;
      conv.last_message_preview = preview;
      // Move to top of list (most recent first)
      state.conversations.sort((a, b) => {
        const aTime = a.last_message_at ?? a.created_at ?? '';
        const bTime = b.last_message_at ?? b.created_at ?? '';
        return bTime.localeCompare(aTime);
      });
    },

    /**
     * Toggle conversation sidebar
     */
    toggleConversationSidebar: (state) => {
      state.conversationSidebarOpen = !state.conversationSidebarOpen;
    },

    /**
     * Set conversation sidebar state
     */
    setConversationSidebarOpen: (state, action: PayloadAction<boolean>) => {
      state.conversationSidebarOpen = action.payload;
    },

    /**
     * Reset chat state
     */
    resetChat: (state) => {
      state.messages = [];
      state.chatId = null;
      state.loading = false;
      state.feedbackSubmitted = {};
      state.streamingItinerary = { partial: null, active: false };
      state.conversations = [];
      state.conversationsLoaded = false;
      state.conversationSidebarOpen = false;
      // Logout / hard reset path — drop the persisted pointer so the next
      // user (or returning guest) doesn't inherit the previous account's
      // active conversation.
      persistChatId(null);
    },

    /**
     * Replace the partial itinerary snapshot from a streaming turn (#1117).
     * Called by ``useSendChatMessage`` on every ``itinerary_partial`` SSE
     * event so ``ItineraryDetailsComponent`` can re-render skeleton days
     * as titles + activities arrive. ``active`` flips to true on the first
     * call and stays true until ``clearStreamingItinerary`` fires.
     */
    setStreamingItinerary: (
      state,
      action: PayloadAction<Record<string, unknown>>
    ) => {
      state.streamingItinerary = {
        partial: action.payload,
        active: true,
      };
    },

    /**
     * Drop the partial snapshot (#1117). Fired by the streaming hook when
     * the turn completes (the ``complete`` ChatResponse takes over), when
     * the stream errors out, or when the FE falls back to the
     * non-streaming endpoint. Keeps state clean for the next turn.
     */
    clearStreamingItinerary: (state) => {
      state.streamingItinerary = { partial: null, active: false };
    },
  },
});

export const {
  setMessages,
  addMessage,
  updateMessage,
  removeTypingIndicator,
  clearMessages,
  setChatId,
  setLoading,
  setConfig,
  markChatConfigHydrated,
  setFeedbackSubmitted,
  setConversations,
  addConversation,
  updateConversationName,
  removeConversation,
  updateConversationOnMessage,
  toggleConversationSidebar,
  setConversationSidebarOpen,
  resetChat,
  setStreamingItinerary,
  clearStreamingItinerary,
} = chatSlice.actions;

export default chatSlice.reducer;

// Selectors
export const selectMessages = (state: { chat: ChatState }) => state.chat.messages;
export const selectChatId = (state: { chat: ChatState }) => state.chat.chatId;
export const selectChatLoading = (state: { chat: ChatState }) => state.chat.loading;
export const selectChatConfig = (state: { chat: ChatState }) => state.chat.config;
export const selectConfigLoaded = (state: { chat: ChatState }) => state.chat.configLoaded;
export const selectStreamingItinerary = (state: { chat: ChatState }) =>
  state.chat.streamingItinerary;
export const selectFeedbackSubmitted = (state: { chat: ChatState }) => state.chat.feedbackSubmitted;
export const selectConversations = (state: { chat: ChatState }) => state.chat.conversations;
export const selectConversationsLoaded = (state: { chat: ChatState }) =>
  state.chat.conversationsLoaded;
export const selectConversationSidebarOpen = (state: { chat: ChatState }) =>
  state.chat.conversationSidebarOpen;

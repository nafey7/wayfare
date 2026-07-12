import { baseApi } from './baseApi';
import type {
  ChatResponse,
  ChatMessageRequest,
  ChatHistoryResponse,
  ChatFeedbackRequest,
  ClaimChatRequest,
  ClaimChatResponse,
  FrontendConfig,
  FrontendConfigResponse,
  ConversationListResponse,
  ConversationMeta,
} from '@/types/chat';
import type { SuccessResponse } from '@/types/api';

export const chatApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    /**
     * Get frontend config (feature flags)
     */
    getFrontendConfig: builder.query<FrontendConfig, void>({
      query: () => '/config',
      providesTags: ['Config'],
      transformResponse: (response: FrontendConfigResponse): FrontendConfig => ({
        chatFeedbackEnabled: response.chat_feedback_enabled,
        publicChatEnabled: response.public_chat_enabled,
        langgraphFlightsEnabled: response.langgraph_flights_enabled,
        langgraphHotelsEnabled: response.langgraph_hotels_enabled,
        environment: response.environment,
        voucherReservationTtlMinutes: response.voucher_reservation_ttl_minutes,
      }),
    }),

    /**
     * Send a chat message.
     * Intentionally no `transformResponse`: `ChatResponse` matches the wire format (snake_case)
     * per the backend OpenAPI contract; callers use field names as returned.
     */
    sendMessage: builder.mutation<ChatResponse, ChatMessageRequest>({
      query: (body) => ({
        url: '/chat/message',
        method: 'POST',
        body,
      }),
      invalidatesTags: ['Chat'],
    }),

    /**
     * Guest/public landing chat — no JWT; requires X-Public-Chat-Session per request.
     * Same as `sendMessage`: no camelCase transform at the RTK boundary (see FRONTEND_BACKEND_COLLABORATION.md).
     */
    sendPublicMessage: builder.mutation<
      ChatResponse,
      { body: ChatMessageRequest; sessionId: string }
    >({
      query: ({ body, sessionId }) => ({
        url: '/public/chat/message',
        method: 'POST',
        body,
        headers: {
          'X-Public-Chat-Session': sessionId,
        },
      }),
    }),

    /**
     * Mint a new guest Places session JWT (e.g. after photo requests return 401/403).
     */
    refreshPublicPlacesSessionToken: builder.mutation<
      { places_session_token: string },
      { sessionId: string }
    >({
      query: ({ sessionId }) => ({
        url: '/public/places/session-token',
        method: 'POST',
        headers: {
          'X-Public-Chat-Session': sessionId,
        },
      }),
    }),

    /**
     * Get chat history by chat ID
     */
    getChatHistory: builder.query<ChatHistoryResponse, { chatId: string; limit?: number }>({
      query: ({ chatId, limit = 50 }) => `/chat/${chatId}?limit=${limit}`,
      providesTags: ['Chat'],
    }),

    /**
     * Get latest chat history
     */
    getLatestChat: builder.query<ChatHistoryResponse, { limit?: number }>({
      query: ({ limit = 50 }) => `/chat/latest?limit=${limit}`,
      providesTags: ['Chat'],
    }),

    /**
     * Clear chat history by chat ID
     */
    clearChat: builder.mutation<
      { message: string; chat_id: string; deleted_count: number },
      string
    >({
      query: (chatId) => ({
        url: `/chat/${chatId}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['Chat'],
    }),

    /**
     * Clear latest chat history
     */
    clearLatestChat: builder.mutation<
      { message: string; chat_id: string; deleted_count: number },
      void
    >({
      query: () => ({
        url: '/chat/latest',
        method: 'DELETE',
      }),
      invalidatesTags: ['Chat'],
    }),

    /**
     * List conversations for sidebar
     */
    listConversations: builder.query<
      ConversationListResponse,
      { limit?: number; offset?: number } | void
    >({
      query: (params) => {
        const limit = params?.limit ?? 50;
        const offset = params?.offset ?? 0;
        return `/chat/conversations?limit=${limit}&offset=${offset}`;
      },
      providesTags: ['Conversations'],
    }),

    /**
     * Create a new conversation
     */
    createConversation: builder.mutation<ConversationMeta, { name?: string } | void>({
      query: (body) => ({
        url: '/chat/conversations',
        method: 'POST',
        body: body ?? {},
      }),
      invalidatesTags: ['Conversations'],
    }),

    /**
     * Rename a conversation
     */
    renameConversation: builder.mutation<
      { chat_id: string; name: string },
      { chatId: string; name: string }
    >({
      query: ({ chatId, name }) => ({
        url: `/chat/conversations/${chatId}`,
        method: 'PUT',
        body: { name },
      }),
      invalidatesTags: ['Conversations'],
    }),

    /**
     * Soft-delete a conversation
     */
    deleteConversation: builder.mutation<{ chat_id: string; status: string }, string>({
      query: (chatId) => ({
        url: `/chat/conversations/${chatId}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['Conversations'],
    }),

    /**
     * Claim a guest chat thread for the authenticated user.
     * Requires X-Public-Chat-Session header (the guest session UUID).
     */
    claimGuestChat: builder.mutation<
      ClaimChatResponse,
      { body: ClaimChatRequest; sessionId: string }
    >({
      query: ({ body, sessionId }) => ({
        url: '/chat/claim',
        method: 'POST',
        body,
        headers: {
          'X-Public-Chat-Session': sessionId,
        },
      }),
      invalidatesTags: ['Conversations', 'Chat'],
    }),

    /**
     * Submit feedback for a message
     */
    submitFeedback: builder.mutation<SuccessResponse, ChatFeedbackRequest>({
      query: (body) => ({
        url: '/chat/feedback',
        method: 'POST',
        body,
      }),
    }),
  }),
});

export const {
  useGetFrontendConfigQuery,
  useSendMessageMutation,
  useSendPublicMessageMutation,
  useRefreshPublicPlacesSessionTokenMutation,
  useGetChatHistoryQuery,
  useGetLatestChatQuery,
  useClearChatMutation,
  useClearLatestChatMutation,
  useListConversationsQuery,
  useCreateConversationMutation,
  useRenameConversationMutation,
  useDeleteConversationMutation,
  useSubmitFeedbackMutation,
  useClaimGuestChatMutation,
} = chatApi;

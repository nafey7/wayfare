import { useEffect, useRef } from 'react';
import { useStore } from 'react-redux';

import { useAppDispatch, type RootState } from '@/store';
import { setMessages } from '@/store/slices/chatSlice';
import { chatApi } from '@/api/chatApi';
import {
  rebuildHistoryMessages,
  type RawHistoryMessage,
} from '@/features/chat/utils/chatMessages';

interface UseChatHistoryLoaderArgs {
  isAuthenticated: boolean;
  chatId: string | null;
}

/**
 * Fetches chat history when switching to an authenticated conversation.
 *
 * Tracks every chatId transition (including → null) so the sequence
 * A → null → A — which happens when the user clicks "New Chat" then
 * re-opens the same conversation in the sidebar — still triggers a refetch
 * instead of leaving the panel blank.
 */
export function useChatHistoryLoader({
  isAuthenticated,
  chatId,
}: UseChatHistoryLoaderArgs): void {
  const dispatch = useAppDispatch();
  const reduxStore = useStore<RootState>();
  const prevChatIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated) return;
    if (chatId === prevChatIdRef.current) return;
    prevChatIdRef.current = chatId;
    if (!chatId) return;

    // Skip history fetch when Redux already has live messages for this chat
    // (e.g. user just sent the first message in a brand-new conversation —
    // the welcome + user + bot messages are already in state and the DB copy
    // doesn't include the welcome). Switching to another conversation always
    // dispatches `clearMessages()` first, so this guard is safe.
    const liveMessages = reduxStore.getState().chat.messages;
    if (liveMessages.length > 0) return;

    dispatch(chatApi.endpoints.getChatHistory.initiate({ chatId, limit: 50 }))
      .unwrap()
      .then((historyResponse) => {
        const rawMessages = historyResponse.messages as unknown as RawHistoryMessage[];
        if (rawMessages && rawMessages.length > 0) {
          dispatch(setMessages(rebuildHistoryMessages(rawMessages)));
        }
      })
      .catch(() => {
        // History load failed silently
      });
  }, [isAuthenticated, chatId, dispatch, reduxStore]);
}

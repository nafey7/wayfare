import { useCallback, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import {
  useListConversationsQuery,
  useRenameConversationMutation,
  useDeleteConversationMutation,
} from '@/api';
import { ROUTES, isChatRoute } from '@/features/routing';
import { useAppDispatch, useAppSelector } from '@/store';
import {
  selectChatId,
  selectConversations,
  selectConversationsLoaded,
  setConversations,
  updateConversationName,
  removeConversation,
  setChatId,
  clearMessages,
} from '@/store/slices/chatSlice';
import { selectIsAuthenticated } from '@/store/slices/authSlice';
import { useStartNewChat, NEW_CHAT_PENDING_KEY } from './useStartNewChat';

/**
 * Hook for conversation CRUD and lifecycle.
 *
 * - Loads conversation list on mount (authenticated only)
 * - Auto-selects the most recent conversation or creates one
 * - Provides create/rename/delete/switch actions
 */
export function useConversations() {
  const dispatch = useAppDispatch();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const chatId = useAppSelector(selectChatId);
  const conversations = useAppSelector(selectConversations);
  const conversationsLoaded = useAppSelector(selectConversationsLoaded);
  const startNewChat = useStartNewChat();
  const navigate = useNavigate();
  const { pathname } = useLocation();

  // RTK Query
  const { data: listData } = useListConversationsQuery(undefined, {
    skip: !isAuthenticated,
  });

  const [renameConversationMutation] = useRenameConversationMutation();
  const [deleteConversationMutation] = useDeleteConversationMutation();

  // Track if we've already initialized to avoid repeat auto-select
  const initializedRef = useRef(false);

  // Sync API response to Redux
  useEffect(() => {
    if (listData) {
      dispatch(setConversations(listData.conversations));
    }
  }, [listData, dispatch]);

  // Auto-select most recent conversation on first load.
  // If user has no conversations yet, show the welcome message (chatId stays null
  // until they send a message — the backend auto-creates the conversation then).
  useEffect(() => {
    if (!isAuthenticated || !conversationsLoaded || initializedRef.current) return;
    initializedRef.current = true;

    // If startNewChat() was called from a page where this hook wasn't mounted
    // yet (e.g. an itinerary card on /home navigating to /chat), skip
    // auto-selection so the explicit new-chat intent is honoured.
    if (sessionStorage.getItem(NEW_CHAT_PENDING_KEY) === '1') {
      sessionStorage.removeItem(NEW_CHAT_PENDING_KEY);
      return;
    }

    if (conversations.length === 0) {
      startNewChat();
      return;
    }

    // If a chatId was persisted across refresh but it no longer exists in
    // the user's conversations (deleted from another tab, server-side
    // cleanup, etc.), fall back to the most recent rather than letting the
    // history fetch 404.
    if (chatId && !conversations.some((c) => c.chat_id === chatId)) {
      const mostRecent = conversations[0];
      if (mostRecent) {
        dispatch(setChatId(mostRecent.chat_id));
      }
      return;
    }

    if (!chatId) {
      const mostRecent = conversations[0];
      if (mostRecent) {
        dispatch(setChatId(mostRecent.chat_id));
      }
    }
  }, [isAuthenticated, conversationsLoaded, conversations, chatId, dispatch, startNewChat]);

  // Reset initialization when user logs out
  useEffect(() => {
    if (!isAuthenticated) {
      initializedRef.current = false;
    }
  }, [isAuthenticated]);

  /** Switch to a different conversation — loads its history */
  const switchConversation = useCallback(
    async (targetChatId: string) => {
      if (targetChatId === chatId) return;
      dispatch(setChatId(targetChatId));
      dispatch(clearMessages());
    },
    [chatId, dispatch]
  );

  /** Start a new conversation (ChatGPT-style).
   *
   * Does NOT create a DB entry upfront — just resets UI state and clears
   * chatId. The backend auto-creates the conversation when the user sends
   * their first message (see `get_or_create_chat_conversation`). The sidebar
   * then upserts the new conversation from the response in
   * `applySuccessfulChatResponse`.
   */
  const createNewConversation = useCallback(() => {
    startNewChat();
    // If the user clicked "New chat" while viewing a content route (e.g.
    // /itinerary/:id, /flights/search, /hotels/search), the right-side panel
    // is URL-driven and would otherwise keep showing the old itinerary/results.
    // Send them to the standalone chat surface so the new chat starts clean.
    if (!isChatRoute(pathname)) {
      navigate(ROUTES.CHAT);
    }
  }, [startNewChat, navigate, pathname]);

  /** Rename a conversation */
  const renameConv = useCallback(
    async (targetChatId: string, name: string) => {
      try {
        await renameConversationMutation({ chatId: targetChatId, name }).unwrap();
        dispatch(updateConversationName({ chatId: targetChatId, name }));
      } catch (err) {
        console.error('Failed to rename conversation:', err);
      }
    },
    [renameConversationMutation, dispatch]
  );

  /** Delete a conversation — switches to most recent or resets to new-chat state. */
  const deleteConv = useCallback(
    async (targetChatId: string) => {
      try {
        await deleteConversationMutation(targetChatId).unwrap();
        dispatch(removeConversation(targetChatId));

        // If deleting the active conversation, switch to next or reset UI
        if (targetChatId === chatId) {
          const remaining = conversations.filter((c) => c.chat_id !== targetChatId);
          if (remaining.length > 0 && remaining[0]) {
            dispatch(setChatId(remaining[0].chat_id));
            dispatch(clearMessages());
          } else {
            // No conversations left — reset to new-chat state (backend
            // auto-creates on first message).
            startNewChat();
          }
        }
      } catch (err) {
        console.error('Failed to delete conversation:', err);
      }
    },
    [deleteConversationMutation, dispatch, chatId, conversations, startNewChat]
  );

  return {
    conversations,
    conversationsLoaded,
    chatId,
    switchConversation,
    createNewConversation,
    renameConversation: renameConv,
    deleteConversation: deleteConv,
  };
}

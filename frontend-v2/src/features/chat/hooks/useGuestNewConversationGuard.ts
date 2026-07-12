import { useCallback, useRef, useState } from 'react';

import { useAppDispatch, useAppSelector } from '@/store';
import { selectIsAuthenticated } from '@/store/slices/authSlice';
import { openAuthModal } from '@/store/slices/uiSlice';
import { getPublicChatId } from '@/features/chat/utils/publicChatSession';
import { clearGuestItineraries } from '@/features/chat/utils/guestItineraries';

import type { ConfirmNewConversationDialogProps } from '../components/ConfirmNewConversationDialog';

export interface UseGuestNewConversationGuardReturn {
  /**
   * Wraps a "start new conversation" action. When the user is authenticated
   * or has no active guest chat (`voya_public_chat_id` is null), the action
   * runs immediately. Otherwise the confirmation dialog is opened and the
   * action is held until the user chooses "Proceed anyway".
   *
   * Add this guard to every guest entry point that starts a new conversation.
   */
  requestNewConversation: (action: () => void) => void;
  dialogProps: ConfirmNewConversationDialogProps;
}

export function useGuestNewConversationGuard(): UseGuestNewConversationGuardReturn {
  const dispatch = useAppDispatch();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const [open, setOpen] = useState(false);
  const pendingRef = useRef<(() => void) | null>(null);

  const requestNewConversation = useCallback(
    (action: () => void) => {
      if (isAuthenticated || getPublicChatId() === null) {
        action();
        return;
      }
      pendingRef.current = action;
      setOpen(true);
    },
    [isAuthenticated],
  );

  const handleCancel = useCallback(() => {
    setOpen(false);
    pendingRef.current = null;
  }, []);

  const handleSaveChat = useCallback(() => {
    setOpen(false);
    pendingRef.current = null;
    dispatch(openAuthModal());
  }, [dispatch]);

  const handleProceed = useCallback(() => {
    setOpen(false);
    clearGuestItineraries();
    const fn = pendingRef.current;
    pendingRef.current = null;
    fn?.();
  }, []);

  return {
    requestNewConversation,
    dialogProps: {
      open,
      onClose: handleCancel,
      onSaveChat: handleSaveChat,
      onProceed: handleProceed,
    },
  };
}

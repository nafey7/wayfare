import { useCallback, useEffect, useRef } from 'react';
import { Flex } from '@mantine/core';
import { useLocation } from 'react-router-dom';

import { MainLayout } from './MainLayout';
import { ChatPanel, ChatSheet } from '@/features/chat';
import { ContentPanel } from './ContentPanel';
import { LAYOUT } from './layoutConstants';
import { isPublicChatContentRoute } from '@/features/routing';
import { useChatContext } from '@/features/chat/context/useChatContext';

import { AuthModal } from '@/features/auth/components/AuthModal';
import { useAppDispatch, useAppSelector } from '@/store';
import { closeAuthModal, selectAuthModalOpen } from '@/store/slices/uiSlice';

/**
 * Layout route for public chat with rich content.
 * - /public/chat (index): ChatPanel standalone (100% width).
 * - /public/chat/itinerary|flights|hotels: 2-column (30% chat | 70% content).
 * Mounts AuthModal so conversion-gated CTAs work for guests.
 */
export function PublicChatWithContentLayout() {
  const location = useLocation();
  const pathname = location.pathname;
  const onContentRoute = isPublicChatContentRoute(pathname);

  const dispatch = useAppDispatch();
  const authModalOpen = useAppSelector(selectAuthModalOpen);
  const handleCloseAuthModal = useCallback(() => {
    dispatch(closeAuthModal());
  }, [dispatch]);

  const { openChat } = useChatContext();
  const openChatRef = useRef(openChat);
  openChatRef.current = openChat;
  useEffect(() => {
    openChatRef.current();
  }, []);

  return (
    <>
      <MainLayout>
        <Flex style={{ flex: 1, minHeight: 0, width: '100%', overflow: 'hidden', position: 'relative' }}>
          <Flex
            visibleFrom={onContentRoute ? 'md' : undefined}
            style={{
              width: onContentRoute ? LAYOUT.CHAT_COLUMN_WIDTH : '100%',
              minWidth: 0,
              flexShrink: 0,
              borderRight: onContentRoute ? '1px solid var(--mantine-color-default-border)' : 0,
            }}
          >
            <ChatPanel variant={onContentRoute ? 'sidebar' : 'standalone'} />
          </Flex>
          {onContentRoute && <ContentPanel />}
          {/* Mobile: ChatSheet bottom sheet on content routes (renders null on desktop). */}
          {onContentRoute && <ChatSheet />}
        </Flex>
      </MainLayout>
      <AuthModal open={authModalOpen} onClose={handleCloseAuthModal} />
    </>
  );
}

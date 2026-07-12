import { useCallback, useEffect, useRef } from 'react';
import { ActionIcon, Box, Flex, FocusTrap } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { Menu as MenuIcon, SquarePen } from 'lucide-react';
import { useLocation } from 'react-router-dom';
import { MainLayout } from './MainLayout';
import { ChatPanel } from '@/features/chat';
import { ChatSheet } from '@/features/chat/components/ChatSheet';
import { ContentPanel } from './ContentPanel';
import { LAYOUT } from './layoutConstants';
import { isChatRoute } from '@/features/routing';
import { clearPublicChatPendingCompleteRegistration } from '@/features/chat/utils/publicChatSignupIntent';
import { ConversationSidebar } from '@/features/chat/components/ConversationSidebar';
import { useConversations } from '@/features/chat/hooks/useConversations';
import { useAppDispatch, useAppSelector } from '@/store';
import {
  selectConversationSidebarOpen,
  setConversationSidebarOpen,
} from '@/store/slices/chatSlice';
import { setChatState } from '@/store/slices/uiSlice';
import { selectIsAuthenticated } from '@/store/slices/authSlice';
import type { ConversationMeta } from '@/types/chat';

/** Width of the conversation drawer */
const SIDEBAR_WIDTH = 260;

const OVERLAY_CONFIG = {
  desktop: {
    position: 'absolute' as const,
    backdropBg: 'rgba(0, 0, 0, 0.25)',
    backdropZ: 10,
    panelZ: 11,
    panelWidth: `min(${SIDEBAR_WIDTH}px, 100%)`,
    panelShadow: '4px 0 12px rgba(0, 0, 0, 0.15)',
  },
  mobile: {
    position: 'fixed' as const,
    backdropBg: 'rgba(0, 0, 0, 0.4)',
    backdropZ: 1400,
    panelZ: 1401,
    panelWidth: `min(${SIDEBAR_WIDTH}px, 85vw)`,
    panelShadow: '4px 0 16px rgba(0, 0, 0, 0.18)',
  },
} as const;

interface ConversationOverlayProps {
  variant: keyof typeof OVERLAY_CONFIG;
  conversations: ConversationMeta[];
  activeChatId: string | null;
  onClose: () => void;
  onSelect: (chatId: string) => void;
  onNewChat: () => void;
  onRename: (chatId: string, name: string) => void;
  onDelete: (chatId: string) => void;
}

export function ConversationOverlay({
  variant,
  conversations,
  activeChatId,
  onClose,
  onSelect,
  onNewChat,
  onRename,
  onDelete,
}: ConversationOverlayProps) {
  const { position, backdropBg, backdropZ, panelZ, panelWidth, panelShadow } =
    OVERLAY_CONFIG[variant];
  return (
    <>
      <Box
        aria-hidden="true"
        onClick={onClose}
        style={{ position, inset: 0, backgroundColor: backdropBg, zIndex: backdropZ }}
      />
      <FocusTrap active>
        <Box
          role="dialog"
          aria-modal="true"
          aria-label="Conversations"
          style={{ position, top: 0, left: 0, bottom: 0, width: panelWidth, zIndex: panelZ, boxShadow: panelShadow }}
        >
          <ConversationSidebar
            conversations={conversations}
            activeChatId={activeChatId}
            onSelect={onSelect}
            onNewChat={onNewChat}
            onRename={onRename}
            onDelete={onDelete}
            onClose={onClose}
          />
        </Box>
      </FocusTrap>
    </>
  );
}

/**
 * Layout route: route-aware layout for authenticated pages.
 * - /chat (desktop): full-width ChatPanel with header; conversation list in Drawer.
 * - /chat (mobile): ChatSheet at full; no desktop header visible.
 * - itinerary/flights/hotels (desktop): 2-column (ChatPanel sidebar | ContentPanel).
 * - itinerary/flights/hotels (mobile): ContentPanel full-width + ChatSheet bottom sheet.
 * Same ChatPanel instance across navigation (variant switches, panel stays mounted).
 * Hamburger in the chat header opens the conversation Drawer on all routes.
 */
export function LayoutWithChat() {
  const location = useLocation();
  const pathname = location.pathname;
  const onChatRoute = isChatRoute(pathname);
  const dispatch = useAppDispatch();
  // Align with Mantine's default `md` breakpoint (62em = 992px) so the desktop
  // flex column (`visibleFrom="md"`) and the mobile overlay gate stay in sync.
  const isMobile = useMediaQuery('(max-width: 991px)') ?? false;

  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const sidebarOpen = useAppSelector(selectConversationSidebarOpen);

  const {
    conversations,
    chatId,
    switchConversation,
    createNewConversation,
    renameConversation,
    deleteConversation,
  } = useConversations();

  useEffect(() => {
    if (onChatRoute) {
      clearPublicChatPendingCompleteRegistration();
      dispatch(setChatState('full'));
    }
    // No-op on non-chat routes — sheet state is preserved across non-chat navigations.
  }, [onChatRoute, dispatch]);

  // Close drawer on mobile when leaving chat route
  useEffect(() => {
    if (!onChatRoute && isMobile) {
      dispatch(setConversationSidebarOpen(false));
    }
  }, [onChatRoute, isMobile, dispatch]);

  // Ref on the hamburger button so focus returns to it when the drawer closes.
  const hamburgerRef = useRef<HTMLButtonElement>(null);

  const closeDrawer = useCallback(() => {
    dispatch(setConversationSidebarOpen(false));
    hamburgerRef.current?.focus();
  }, [dispatch]);

  // ESC key dismisses the drawer (keyboard accessibility).
  // Guard with defaultPrevented so nested Mantine modals/dialogs that already
  // handled ESC don't also close the drawer. Mantine's `closeOnEscape` option
  // calls `e.preventDefault()` before this document listener fires, so the
  // guard relies on that implicit contract.
  useEffect(() => {
    if (!sidebarOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !e.defaultPrevented) closeDrawer();
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [sidebarOpen, closeDrawer]);

  return (
    <MainLayout>
      {/* Viewport-bound flex container — `position: relative` anchors the ChatSheet.
          Mobile: flex: 1 + overflow: hidden for the bottom-sheet pattern.
          Desktop: natural height so sticky chat column and maps work correctly. */}
      <Box
        style={{
          display: 'flex',
          width: '100%',
          position: 'relative',
          flex: 1,
          minHeight: 0,
          overflow: 'hidden',
        }}
      >
        {/* Desktop-only ChatPanel column — hidden on mobile (ChatSheet handles mobile).
            `position: relative` anchors the conversation overlay within the column. */}
        <Flex
          visibleFrom="md"
          style={{
            flexDirection: 'column',
            flex: onChatRoute ? 1 : undefined,
            width: onChatRoute ? undefined : LAYOUT.CHAT_COLUMN_WIDTH,
            minWidth: 0,
            minHeight: 0,
            flexShrink: 0,
            position: 'relative',
            overflow: 'hidden',
            borderRight: onChatRoute
              ? 0
              : '1px solid var(--mantine-color-default-border)',
          }}
        >
          {/* Chat header: hamburger opens conversation list; new chat resets the panel */}
          {isAuthenticated && (
            <Box
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '8px 12px',
                borderBottom: '1px solid var(--mantine-color-default-border)',
                backgroundColor: 'var(--mantine-color-gray-0)',
                flexShrink: 0,
              }}
            >
              <ActionIcon
                ref={hamburgerRef}
                variant="subtle"
                color="gray"
                size="md"
                radius="md"
                onClick={() => dispatch(setConversationSidebarOpen(true))}
                aria-label="Open conversations"
                aria-expanded={sidebarOpen}
                aria-haspopup="dialog"
              >
                <MenuIcon size={18} />
              </ActionIcon>
              <ActionIcon
                variant="subtle"
                color="gray"
                size="md"
                radius="md"
                onClick={() => createNewConversation()}
                aria-label="New chat"
              >
                <SquarePen size={18} />
              </ActionIcon>
            </Box>
          )}

          <Box style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
            <ChatPanel variant={onChatRoute ? 'standalone' : 'sidebar'} />
          </Box>

          {/* Conversation list overlay — bounded to the chat column, below the header */}
          {isAuthenticated && sidebarOpen && (
            <ConversationOverlay
              variant="desktop"
              conversations={conversations}
              activeChatId={chatId}
              onClose={closeDrawer}
              onSelect={(id) => { void switchConversation(id); closeDrawer(); }}
              onNewChat={() => { createNewConversation(); closeDrawer(); }}
              onRename={renameConversation}
              onDelete={deleteConversation}
            />
          )}
        </Flex>

        {!onChatRoute && <ContentPanel />}

        {/* Mobile: ChatSheet bottom sheet (renders null on desktop). */}
        <ChatSheet
          isAuthenticated={isAuthenticated}
          onOpenSidebar={() => dispatch(setConversationSidebarOpen(true))}
          onNewChat={() => { createNewConversation(); }}
        />

        {/* Mobile conversation sidebar — fixed overlay above ChatSheet's z-index 1300; this overlay sits at 1400 (backdrop) / 1401 (panel). */}
        {isMobile && isAuthenticated && sidebarOpen && (
          <ConversationOverlay
            variant="mobile"
            conversations={conversations}
            activeChatId={chatId}
            onClose={closeDrawer}
            onSelect={(id) => { void switchConversation(id); closeDrawer(); }}
            onNewChat={() => { createNewConversation(); closeDrawer(); }}
            onRename={renameConversation}
            onDelete={deleteConversation}
          />
        )}
      </Box>
    </MainLayout>
  );
}

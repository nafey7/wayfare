import { ActionIcon, Box, Text } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { ChevronDown, ChevronUp, Menu as MenuIcon, SquarePen } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store';
import {
  selectChatState,
  selectBottomNavHidden,
  setChatState,
} from '@/store/slices/uiSlice';
import { selectConversationSidebarOpen } from '@/store/slices/chatSlice';
import { useBottomSheet, type BottomSheetSnap } from '@/components/sheet/useBottomSheet';
import { useScrollDirectionHidden } from '@/hooks';
import { NAV_LINE, NAV_NAVY, NAV_MIST_CARD } from '@/theme/navTokens';
import { zIndex } from '@/theme/zIndex';
import voyaAvatar from '@/assets/images/voya.jpeg';
import { ChatPanel } from './ChatPanel';

// `half` is a transient drag-through stop the underlying sheet emits mid-drag,
// not a resting state — `onSnapChange` collapses it to the nearest extreme.
// Keep it here (and in `tapCycle` below) so drag math still has a midpoint.
const CHAT_SNAPS = { minimized: 44, half: 380, full: 'full' as const };
const SHEET_EXPANDED_RADIUS = '18px 18px 0 0';
const SHEET_RESTING_BORDER = '#ebebeb';
const PILL_TEXT_COLOR = '#8a90b3';
const DRAG_BAR_WIDTH = CHAT_SNAPS.minimized;

// When nav is visible, container's paddingBottom already reserves the nav height,
// so bottom: 0 lands at top-of-nav. Add safe-area so the resting bar clears
// the phone's home-indicator when nav is hidden.
const NAV_VISIBLE_OFFSET = 0;
const NAV_HIDDEN_OFFSET = 'env(safe-area-inset-bottom)';

interface ChatSheetProps {
  isAuthenticated?: boolean;
  onOpenSidebar?: () => void;
  onNewChat?: () => void;
}

/**
 * Mobile chat bottom sheet. Two snap states driven by Redux `chatState`:
 *   - 'resting' (= 'minimized'): 44px "Ask Voya…" pill at bottom
 *   - 'full': fills viewport above BottomNav
 *
 * The underlying sheet still emits a transient 'half' snap during drag; we
 * collapse it to the nearest extreme in `onSnapChange`.
 *
 * Desktop: returns null (ChatPanel sidebar handles desktop).
 */
export function ChatSheet({ isAuthenticated, onOpenSidebar, onNewChat }: ChatSheetProps = {}) {
  const dispatch = useAppDispatch();
  const chatState = useAppSelector(selectChatState);
  const sidebarOpen = useAppSelector(selectConversationSidebarOpen);
  const isMobile = useMediaQuery('(max-width: 768px)');

  const scrollHidden = useScrollDirectionHidden();
  const flagHidden = useAppSelector(selectBottomNavHidden);
  const navHidden = scrollHidden || flagHidden;
  const bottomOffset = navHidden ? NAV_HIDDEN_OFFSET : NAV_VISIBLE_OFFSET;

  const snap: BottomSheetSnap = chatState === 'resting' ? 'minimized' : 'full';
  const onSnapChange = (s: BottomSheetSnap) => {
    // Sheet has no resting 'half' for chat — collapse the transient mid stop
    // toward the nearest extreme based on current snap.
    const target: BottomSheetSnap =
      s === 'half' ? (snap === 'full' ? 'minimized' : 'full') : s;
    dispatch(setChatState(target === 'minimized' ? 'resting' : 'full'));
  };

  const { sheetRef, sheetStyle, handleRef, handleProps, listRef } = useBottomSheet({
    snap,
    snaps: CHAT_SNAPS,
    onSnapChange,
    bottomOffset,
    topReserve: 0,
    zIndex: zIndex.chatSheet,
    tapCycle: { minimized: 'full', half: 'minimized', full: 'minimized' },
  });

  if (!isMobile) return null;

  const isResting = chatState === 'resting';

  return (
    <Box
      ref={sheetRef}
      style={{
        ...sheetStyle,
        display: 'flex',
        flexDirection: 'column',
        background: 'white',
        borderTop: isResting ? `1px solid ${SHEET_RESTING_BORDER}` : 'none',
        borderRadius: isResting ? 0 : SHEET_EXPANDED_RADIUS,
        boxShadow: isResting
          ? '0 -2px 12px rgba(20,23,43,0.04)'
          : '0 -4px 16px rgba(0,0,0,0.12)',
      }}
    >
      {/* Drag handle + header — visible when sheet is expanded. Full top region is draggable. */}
      {!isResting && (
        <Box ref={handleRef} {...handleProps}>
          {/* Pull bar */}
          <Box style={{ display: 'flex', justifyContent: 'center', padding: '12px 0 8px' }}>
            <Box style={{ width: DRAG_BAR_WIDTH, height: 4, borderRadius: 2, background: NAV_LINE }} />
          </Box>

          {/* Header row: [Hamburger] [Avatar · Voya] [spacer] [New chat] [Minimize] */}
          <Box
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '0 12px 12px',
              minHeight: 38,
            }}
          >
            {isAuthenticated && onOpenSidebar && (
              <ActionIcon
                variant="subtle"
                color="gray"
                size="md"
                radius="md"
                onClick={onOpenSidebar}
                aria-label="Open conversations"
                aria-expanded={sidebarOpen}
                aria-haspopup="dialog"
                style={{ flexShrink: 0 }}
              >
                <MenuIcon size={18} />
              </ActionIcon>
            )}

            <Box
              component="img"
              src={voyaAvatar}
              alt="Voya"
              style={{
                width: 32,
                height: 32,
                borderRadius: '50%',
                objectFit: 'cover',
                objectPosition: 'center top',
                flexShrink: 0,
                border: `1px solid ${NAV_LINE}`,
              }}
            />
            <Box style={{ minWidth: 0 }}>
              <Text size="sm" fw={600} style={{ lineHeight: 1.2, color: NAV_NAVY }}>
                Voya
              </Text>
              <Text size="xs" c="dimmed" style={{ display: 'block', lineHeight: 1.2 }}>
                AI travel assistant
              </Text>
            </Box>

            <Box style={{ flex: 1 }} />

            {isAuthenticated && onNewChat && (
              <ActionIcon
                variant="subtle"
                color="gray"
                size="md"
                radius="md"
                onClick={onNewChat}
                aria-label="New chat"
                style={{ flexShrink: 0 }}
              >
                <SquarePen size={18} />
              </ActionIcon>
            )}

            <button
              type="button"
              onClick={() => {
                dispatch(setChatState('resting'));
              }}
              aria-label="Minimise chat"
              style={{
                width: 32,
                height: 32,
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: NAV_NAVY,
                cursor: 'pointer',
                flexShrink: 0,
                background: 'none',
                border: 'none',
                padding: 0,
              }}
            >
              <ChevronDown size={20} strokeWidth={2} />
            </button>
          </Box>
        </Box>
      )}

      {/* ChatPanel — fills remaining space when expanded. listRef enables drag-to-resize at half snap. */}
      {!isResting && (
        <Box
          ref={listRef}
          style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}
        >
          <ChatPanel variant="standalone" />
        </Box>
      )}

      {/* "Ask Voya…" pill — tap to expand from resting state. */}
      {isResting && (
        <button
          type="button"
          onClick={() => dispatch(setChatState('full'))}
          aria-label="Open Voya chat"
          style={{
            padding: '6px 12px',
            height: 44,
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            flexShrink: 0,
            background: 'white',
            border: 'none',
            cursor: 'pointer',
          }}
        >
          <Box
            component="img"
            src={voyaAvatar}
            alt="Voya"
            style={{
              width: 26,
              height: 26,
              borderRadius: '50%',
              objectFit: 'cover',
              objectPosition: 'center top',
              flexShrink: 0,
            }}
          />
          <Box
            style={{
              flex: 1,
              background: NAV_MIST_CARD,
              borderRadius: '16px',
              padding: '6px 12px',
              fontSize: 12,
              color: PILL_TEXT_COLOR,
              height: 30,
              display: 'flex',
              alignItems: 'center',
            }}
          >
            Ask Voya…
          </Box>
          <Box
            style={{
              width: 30,
              height: 30,
              borderRadius: '50%',
              background: NAV_MIST_CARD,
              color: NAV_NAVY,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <ChevronUp size={18} strokeWidth={2.5} />
          </Box>
        </button>
      )}
    </Box>
  );
}

import { useCallback, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Text } from '@mantine/core';
import { SendHorizonal } from 'lucide-react';

import { useAppDispatch, useAppSelector } from '@/store';
import { selectIsAuthenticated } from '@/store/slices/authSlice';
import { selectChatConfig, selectConfigLoaded } from '@/store/slices/chatSlice';
import { openAuthModal } from '@/store/slices/uiSlice';
import { ROUTES } from '@/features/routing';
import { useStartNewChat } from '@/features/chat/hooks/useStartNewChat';
import { useGuestNewConversationGuard } from '@/features/chat/hooks/useGuestNewConversationGuard';
import { ConfirmNewConversationDialog } from '@/features/chat/components/ConfirmNewConversationDialog';

import {
  NAV_NAVY as NAVY,
  NAV_NAVY_DEEP as NAVY_DEEP,
  NAV_NAVY_MID as SLATE,
  NAV_INACTIVE as LAVENDER,
  NAV_MIST_CARD as MIST,
} from '@/theme/navTokens';

import { LAVENDER_SOFT } from '../landingColors';

export interface NavbarChatSearchProps {
  maxWidth?: number | string;
}

/**
 * Landing / home page search pill. Typing and pressing Enter (or clicking the
 * search button) navigates to AI chat with the typed text pre-sent via `?prompt=`.
 * Shows on `/` and `/home` in place of the flight/hotel chips.
 */
export function NavbarChatSearch({ maxWidth = '100%' }: NavbarChatSearchProps) {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const { publicChatEnabled } = useAppSelector(selectChatConfig);
  const configLoaded = useAppSelector(selectConfigLoaded);

  const startNewChat = useStartNewChat();
  const { requestNewConversation, dialogProps } = useGuestNewConversationGuard();
  const [value, setValue] = useState('');
  const [focused, setFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const buildRoute = useCallback((text: string) => {
    const query = text.trim() ? `?prompt=${encodeURIComponent(text.trim())}` : '';
    if (isAuthenticated) return `${ROUTES.CHAT}${query}`;
    if (publicChatEnabled) return `${ROUTES.PUBLIC_CHAT}${query}`;
    return null;
  }, [isAuthenticated, publicChatEnabled]);

  const handleSubmit = useCallback(() => {
    if (!configLoaded) return;
    const route = buildRoute(value);
    if (route) {
      requestNewConversation(() => {
        startNewChat();
        navigate(route);
      });
    } else {
      dispatch(openAuthModal());
    }
  }, [buildRoute, configLoaded, dispatch, navigate, requestNewConversation, startNewChat, value]);

  const borderColor = focused ? LAVENDER : LAVENDER_SOFT;
  const bgColor = focused ? MIST : 'white';
  const shadow = focused
    ? '0 4px 16px rgba(23,27,99,.10)'
    : '0 2px 10px rgba(23,27,99,.06)';

  return (
    <Box style={{ width: '100%', maxWidth, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
      <Box
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          backgroundColor: bgColor,
          border: `1.5px solid ${borderColor}`,
          borderRadius: 9999,
          paddingLeft: 20,
          paddingRight: 5,
          paddingTop: 5,
          paddingBottom: 5,
          boxShadow: shadow,
          transition: 'border-color 150ms, background 150ms, box-shadow 150ms',
        }}
        onClick={() => inputRef.current?.focus()}
      >
        <input
          ref={inputRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              handleSubmit();
            }
          }}
          placeholder="Ask Voya AI to plan your trip…"
          aria-label="Chat with Voya AI"
          style={{
            flex: 1,
            minWidth: 0,
            border: 'none',
            outline: 'none',
            background: 'transparent',
            color: NAVY,
            fontSize: 14,
            fontWeight: 500,
            lineHeight: 1.4,
            paddingBlock: 4,
            fontFamily: 'inherit',
          }}
        />
        <Box
          component="button"
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            handleSubmit();
          }}
          aria-label="Send to Voya AI"
          style={{
            width: 38,
            height: 38,
            borderRadius: '50%',
            backgroundColor: NAVY,
            color: 'white',
            flexShrink: 0,
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: 'none',
            cursor: 'pointer',
            transition: 'background 150ms',
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLElement).style.backgroundColor = NAVY_DEEP;
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLElement).style.backgroundColor = NAVY;
          }}
        >
          <SendHorizonal size={18} />
        </Box>
      </Box>
      <Text
        component="p"
        style={{
          fontSize: 12,
          color: SLATE,
          textAlign: 'center',
          lineHeight: 1.4,
          margin: 0,
        }}
      >
        Describe your trip — Voya AI handles the planning
      </Text>
      <ConfirmNewConversationDialog {...dialogProps} />
    </Box>
  );
}

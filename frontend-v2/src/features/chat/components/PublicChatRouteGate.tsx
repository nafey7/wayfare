import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { Box, Loader } from '@mantine/core';

import { useAppSelector } from '@/store';
import { selectChatConfig, selectConfigLoaded } from '@/store/slices/chatSlice';

interface PublicChatRouteGateProps {
  children: ReactNode;
}

/**
 * Renders `/public/chat` only when frontend config has `public_chat_enabled`.
 */
export function PublicChatRouteGate({ children }: PublicChatRouteGateProps) {
  const configLoaded = useAppSelector(selectConfigLoaded);
  const { publicChatEnabled } = useAppSelector(selectChatConfig);

  if (!configLoaded) {
    return (
      <Box
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100svh',
        }}
      >
        <Loader aria-label="Loading chat" />
      </Box>
    );
  }

  if (!publicChatEnabled) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}

import { Box, Text } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { User, ChevronRight } from 'lucide-react';

import { useAppDispatch, useAppSelector } from '@/store';
import { openAuthModal } from '@/store/slices/uiSlice';
import { selectIsAuthenticated } from '@/store/slices/authSlice';

import { NAVY, NAVY_4, MIST } from '../landingColors';

interface HomeSignInCardProps {
  /** When true, renders on all screen sizes instead of mobile-only. Default: false. */
  showOnDesktop?: boolean;
  /** Stable marketing id placed on the root element (only wired on `/`). */
  id?: string;
}

/** Mobile-only card shown to logged-out users. Disappears once signed in. */
export function HomeSignInCard({ showOnDesktop = false, id }: HomeSignInCardProps = {}) {
  const dispatch = useAppDispatch();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const isMobile = !useMediaQuery('(min-width: 48em)');

  if (isAuthenticated) return null;
  if (!isMobile && !showOnDesktop) return null;

  return (
    <Box
      id={id}
      onClick={() => dispatch(openAuthModal())}
      style={{
        backgroundColor: 'white',
        border: '1px solid #E4E6F5',
        borderRadius: 14,
        padding: 12,
        boxShadow: '0 1px 3px rgba(23,27,99,.03)',
        marginInline: 16,
        marginBottom: 4,
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        transition: 'box-shadow 160ms, border-color 120ms',
      }}
    >
      {/* Text */}
      <Box style={{ flex: 1, minWidth: 0 }}>
        <Text style={{
          fontSize: 14,
          fontWeight: 700,
          color: NAVY,
          letterSpacing: '-0.01em',
          lineHeight: 1.25,
          marginBottom: 2,
        }}>
          Log in or sign up
        </Text>
        <Text style={{ fontSize: 12, color: NAVY_4, fontWeight: 500 }}>
          Save trips, preferences and wishlist
        </Text>
      </Box>

      {/* Icon tile */}
      <Box style={{
        width: 56,
        height: 56,
        flexShrink: 0,
        borderRadius: 10,
        backgroundColor: MIST,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        <User size={30} color={NAVY} />
      </Box>

      <ChevronRight size={22} color={NAVY_4} style={{ flexShrink: 0, marginLeft: -4 }} />
    </Box>
  );
}

import { Box, Text } from '@mantine/core';
import { useNavigate, useLocation } from 'react-router-dom';
import { useMediaQuery } from '@mantine/hooks';
import { Compass, Heart, User, LogOut, MessageCircle } from 'lucide-react';

import { useAppDispatch, useAppSelector } from '@/store';
import { selectIsAuthenticated } from '@/store/slices/authSlice';
import { openAuthModal } from '@/store/slices/uiSlice';
import { useSignOut } from '@/hooks';
import { ROUTES } from '@/features/routing';
import { NAV_NAVY, NAV_INACTIVE } from '@/theme/navTokens';

type TabId = 'explore' | 'trips' | 'chat' | 'account' | 'signout';

interface BottomNavProps {
  /** Controlled hidden state from the parent layout (eliminates duplicate scroll listener). */
  hidden?: boolean;
}

export function resolveActiveTab(pathname: string): TabId {
  if (pathname.startsWith(ROUTES.PROFILE)) return 'account';
  // '/itinerary' and '/itineraries' diverge at index 9 ('y' vs 'i') so both need explicit checks
  if (
    pathname.startsWith(ROUTES.ITINERARY) ||
    pathname.startsWith(ROUTES.ITINERARIES)
  ) return 'trips';
  return 'explore';
}

/**
 * Returns true on the screens where a Chat tab is shown in the bottom nav instead
 * of the ChatSheet bottom sheet (which those layouts don't have).
 * Matches: public landing `/`, `/home`, `/profile/*`, `/itineraries/*`.
 */
export function shouldShowChatTab(pathname: string): boolean {
  return (
    pathname === '/' || // public landing page (no ROUTES constant)
    pathname === ROUTES.HOME ||
    pathname.startsWith(`${ROUTES.HOME}/`) ||
    pathname.startsWith(ROUTES.PROFILE) ||
    pathname.startsWith(ROUTES.ITINERARIES)
  );
}

/**
 * Mobile-only fixed bottom navigation bar.
 * Mirrors the RossMyvoya BottomNav design: 4 tabs with icon + label.
 * Slides off-screen when `hidden` is `true`; scroll-direction detection and Redux flag
 * are owned by the parent (MainLayout, HomePage, PublicLandingPage) via useBottomNavHidden.
 */
export function BottomNav({ hidden = false }: BottomNavProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useAppDispatch();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const signOut = useSignOut();
  const isMobile = useMediaQuery('(max-width: 768px)');

  const active = resolveActiveTab(location.pathname);
  const showChatTab = shouldShowChatTab(location.pathname);

  // BottomNav is mobile-only; don't render at desktop breakpoint
  if (!isMobile) return null;

  const exploreTab = {
    id: 'explore' as TabId,
    label: 'Explore',
    Icon: Compass,
    onClick: () => navigate(isAuthenticated ? ROUTES.HOME : '/'),
  };
  const tripsTab = {
    id: 'trips' as TabId,
    label: 'Trips',
    Icon: Heart,
    onClick: () =>
      isAuthenticated ? navigate(ROUTES.ITINERARIES) : dispatch(openAuthModal()),
  };
  const accountTab = {
    id: 'account' as TabId,
    label: isAuthenticated ? 'Profile' : 'Sign in',
    Icon: User,
    onClick: () =>
      isAuthenticated ? navigate(ROUTES.PROFILE) : dispatch(openAuthModal()),
  };

  const signOutTab = isAuthenticated
    ? [{
        id: 'signout' as TabId,
        label: 'Sign out',
        Icon: LogOut,
        onClick: signOut,
      }]
    : [];

  const tabs: { id: TabId; label: string; Icon: typeof Compass; onClick: () => void }[] =
    showChatTab
      ? [
          exploreTab,
          tripsTab,
          {
            id: 'chat',
            label: 'Chat',
            Icon: MessageCircle,
            onClick: () => navigate(isAuthenticated ? ROUTES.CHAT : ROUTES.PUBLIC_CHAT),
          },
          accountTab,
          ...signOutTab,
        ]
      : [exploreTab, tripsTab, accountTab, ...signOutTab];

  return (
    <Box
      component="nav"
      aria-label="Primary navigation"
      style={{
        display: 'flex',
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        height: 'calc(48px + env(safe-area-inset-bottom))',
        backgroundColor: 'white',
        borderTop: '1px solid #ebebeb',
        zIndex: 1300,
        alignItems: 'flex-start',
        paddingTop: 4,
        paddingBottom: 'env(safe-area-inset-bottom)',
        transform: hidden ? 'translateY(100%)' : 'translateY(0)',
        transition: 'transform 240ms cubic-bezier(0.32, 0.72, 0, 1)',
      }}
    >
      {tabs.map(({ id, label, Icon, onClick }) => {
        const isActive = active === id;
        return (
          <button
            key={id}
            type="button"
            onClick={onClick}
            aria-current={isActive ? 'page' : undefined}
            style={{
              flex: 1,
              minWidth: 0,
              alignSelf: 'stretch',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 2,
              paddingInline: 2,
              cursor: 'pointer',
              color: isActive ? NAV_NAVY : NAV_INACTIVE,
              background: 'none',
              border: 'none',
              padding: 0,
              paddingTop: 4,
              userSelect: 'none',
              WebkitTapHighlightColor: 'transparent',
              transition: 'color 180ms ease',
            }}
          >
            <Icon size={20} strokeWidth={isActive ? 2 : 1.75} style={{ flexShrink: 0 }} />
            <Text
              style={{
                fontSize: 9.5,
                fontWeight: isActive ? 700 : 500,
                lineHeight: 1,
                letterSpacing: '-0.01em',
                width: '100%',
                textAlign: 'center',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                transition: 'font-weight 180ms ease',
              }}
            >
              {label}
            </Text>
          </button>
        );
      })}
    </Box>
  );
}

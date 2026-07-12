import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate, Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Stack,
  Text,
  Button,
  ActionIcon,
  Avatar,
  Drawer,
  Divider,
  UnstyledButton,
} from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import {
  X as CloseIcon,
  Compass,
  Heart,
  Luggage,
  LogOut,
  Tag,
  CalendarDays,
  MessageCircle,
} from 'lucide-react';

import navbarLogo from '@/assets/logos/navbarLogo.png';
import { useAppDispatch, useAppSelector } from '@/store';
import { selectCurrentUser, selectIsAuthenticated } from '@/store/slices/authSlice';
import { openAuthModal } from '@/store/slices/uiSlice';
import { ROUTES, getTripNavPaths } from '@/features/routing';
import { useIsAdmin, useScrollCollapsed, useSignOut } from '@/hooks';
import { FlightNavSearchBar } from '@/features/flights/components/FlightNavSearchBar';
import { HotelNavSearchBar } from '@/features/hotels/components/HotelNavSearchBar';
import { NavbarChatSearch } from '@/features/landing/components/NavbarChatSearch';
import {
  NAV_NAVY,
  NAV_NAVY_MID,
  NAV_LINE,
  NAV_MIST,
} from '@/theme/navTokens';

// ── Subtab config ─────────────────────────────────────────────────────────────
type Section = 'flights' | 'hotels' | 'itinerary';

const SUBTAB_DEFS: { id: Section; label: string; icon: string }[] = [
  { id: 'flights',   label: 'Flights',  icon: '✈️' },
  { id: 'hotels',    label: 'Stays',    icon: '🏨' },
  { id: 'itinerary', label: 'Day plan', icon: '🗺️' },
];

export function resolveSection(pathname: string): Section | null {
  const bare = pathname.startsWith('/public/chat')
    ? pathname.slice('/public/chat'.length)
    : pathname;
  if (bare.startsWith('/flights')) return 'flights';
  if (bare.startsWith('/hotels')) return 'hotels';
  // '/itinerary' and '/itineraries' diverge at index 9 ('y' vs 'i') so both need explicit checks
  if (bare.startsWith('/itinerary') || bare.startsWith('/itineraries')) return 'itinerary';
  return null;
}

/** Which center-content to render based on current route. */
export type CenterVariant = 'chat' | 'flights' | 'hotels' | 'none';

export function resolveCenterVariant(pathname: string): CenterVariant {
  const bare = pathname.startsWith('/public/chat')
    ? pathname.slice('/public/chat'.length)
    : pathname;
  if (bare.startsWith('/flights')) return 'flights';
  if (bare.startsWith('/hotels')) return 'hotels';
  return 'chat';
}

// ── Optional DOM ids (public landing E2E) ─────────────────────────────────────
export interface UnifiedHeaderDomIds {
  logo?: string;
  signIn?: string;
}

export interface UnifiedHeaderProps {
  /** Stable DOM ids for public marketing analytics / E2E (only on `/`). */
  domIds?: UnifiedHeaderDomIds;
  /** Called when the sign-in button is clicked (unauthenticated). */
  onSignInClick?: () => void;
}

// ── Helper: drawer menu item ──────────────────────────────────────────────────
function MenuItem({
  icon,
  label,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        display: 'flex',
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
        padding: '10px 12px',
        borderRadius: 10,
        cursor: 'pointer',
        color: NAV_NAVY,
        background: 'none',
        border: 'none',
        width: '100%',
        textAlign: 'left',
        transition: 'background 120ms',
        fontFamily: 'inherit',
      }}
      onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.backgroundColor = NAV_MIST; }}
      onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent'; }}
    >
      <Box style={{ display: 'flex', alignItems: 'center', color: NAV_NAVY_MID }}>{icon}</Box>
      <Text style={{ fontSize: 14, fontWeight: 600, color: NAV_NAVY }}>{label}</Text>
    </button>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function UnifiedHeader({ domIds, onSignInClick }: UnifiedHeaderProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useAppDispatch();
  const user = useAppSelector(selectCurrentUser);
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const isAdmin = useIsAdmin();

  const collapsed = useScrollCollapsed(80, 40);
  const [drawerOpen, setDrawerOpen] = useState(false);

  // `(max-width: 768px)` to match RossMyvoya breakpoint
  const isMobile = useMediaQuery('(max-width: 768px)');

  const activeSection = resolveSection(location.pathname);
  const centerVariant = resolveCenterVariant(location.pathname);

  // Hotels and flights tabs always route to /search — chat results are stored in the
  // in-memory results cache, which HotelSearchPage / FlightSearchPage read directly.
  const tripPaths = getTripNavPaths(!isAuthenticated);
  const SUBTABS = [
    {
      ...SUBTAB_DEFS[0],
      route: tripPaths.flights,
    },
    {
      ...SUBTAB_DEFS[1],
      route: tripPaths.hotels,
    },
    { ...SUBTAB_DEFS[2], route: tripPaths.itinerary },
  ];

  const subtabsMinimal = collapsed || isMobile;

  const handleSignIn = () => {
    setDrawerOpen(false);
    if (onSignInClick) {
      onSignInClick();
    } else {
      dispatch(openAuthModal());
    }
  };

  const signOut = useSignOut();
  const handleSignOut = () => {
    setDrawerOpen(false);
    signOut();
  };

  const handleMenuNav = (route: string) => {
    setDrawerOpen(false);
    navigate(route);
  };

  // Expose measured header height as CSS variable so sticky sub-headers can use it
  const headerRef = useRef<HTMLElement>(null);
  useEffect(() => {
    const el = headerRef.current;
    if (!el) return;
    let rafId: number | null = null;
    const obs = new ResizeObserver(() => {
      if (rafId !== null) return;
      rafId = requestAnimationFrame(() => {
        rafId = null;
        document.documentElement.style.setProperty(
          '--unified-header-h',
          `${el.offsetHeight}px`,
        );
      });
    });
    obs.observe(el);
    return () => {
      obs.disconnect();
      if (rafId !== null) cancelAnimationFrame(rafId);
    };
  }, []);

  // ── Right cluster ─────────────────────────────────────────────────────────
  // Desktop: avatar (auth) / Log in button (unauth). Mobile: nothing (all nav lives in BottomNav).
  const rightCluster = (
    <Box
      style={{
        display: 'flex',
        flexDirection: 'row',
        alignItems: 'center',
        gap: 10,
        flexShrink: 0,
      }}
    >
      {/* Avatar opens drawer (auth) / Log in button (unauth); desktop-only — mobile uses BottomNav */}
      {!isMobile && (
        isAuthenticated ? (
          <UnstyledButton
            onClick={() => setDrawerOpen(true)}
            aria-label="Open menu"
            style={{ borderRadius: '50%', flexShrink: 0 }}
          >
            <Avatar
              src={user?.photoUrls?.sm ?? undefined}
              size={collapsed ? 34 : 38}
              radius="xl"
              style={{
                border: '2px solid white',
                boxShadow: '0 2px 6px rgba(23,27,99,.18)',
                background: 'linear-gradient(135deg, #9AA2C5 0%, #8088c8 100%)',
                color: NAV_NAVY,
                fontSize: collapsed ? 13 : 14,
                fontWeight: 800,
              }}
            >
              {user?.firstName?.[0] ?? user?.email?.[0]?.toUpperCase() ?? 'V'}
            </Avatar>
          </UnstyledButton>
        ) : (
          <Button
            onClick={handleSignIn}
            id={domIds?.signIn}
            radius="xl"
            size="sm"
            style={{
              backgroundColor: NAV_NAVY,
              color: 'white',
              fontSize: collapsed ? 12 : 13,
              fontWeight: 700,
              whiteSpace: 'nowrap',
              boxShadow: 'none',
              transition: 'background 200ms',
            }}
            styles={{
              root: { '&:hover': { backgroundColor: '#0F1340' } },
            }}
          >
            Log in
          </Button>
        )
      )}
    </Box>
  );

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <Box
      ref={headerRef}
      component="header"
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 1100,
        backgroundColor: NAV_MIST,
        borderBottom: `1px solid ${NAV_LINE}`,
        contain: 'layout style',
      }}
    >
      {/* ── Bar row: logo · center (search/chips) · right cluster ─────────── */}
      <Box
        style={{
          width: '100%',
          display: 'flex',
          flexDirection: 'row',
          alignItems: 'flex-start',
          gap: isMobile ? 10 : collapsed ? 12 : 20,
          paddingInline: isMobile ? 12 : collapsed ? 24 : 32,
          paddingBlock: isMobile ? 8 : collapsed ? 6 : 12,
          transition: 'padding 250ms ease, gap 250ms ease',
        }}
      >
        {/* Logo — desktop only */}
        <Box
          id={domIds?.logo}
          component={RouterLink}
          to={isAuthenticated ? ROUTES.HOME : '/'}
          aria-label="Voya home"
          style={{
            display: isMobile ? 'none' : 'inline-flex',
            alignItems: 'center',
            flexShrink: 0,
            outline: 'none',
            textDecoration: 'none',
          }}
        >
          <Box
            aria-hidden
            style={{
              width: collapsed ? 96 : 135,
              height: collapsed ? 36 : 48,
              flexShrink: 0,
              backgroundColor: NAV_NAVY,
              WebkitMaskImage: `url(${navbarLogo})`,
              maskImage: `url(${navbarLogo})`,
              WebkitMaskSize: 'contain',
              maskSize: 'contain',
              WebkitMaskRepeat: 'no-repeat',
              maskRepeat: 'no-repeat',
              WebkitMaskPosition: 'center left',
              maskPosition: 'center left',
              filter: 'drop-shadow(0px 0px 0.6px #171B63)',
              transition: 'width 250ms ease, height 250ms ease',
            }}
          />
        </Box>

        {/* Center column — context-aware search */}
        <Box
          style={{
            flex: 1,
            minWidth: 0,
            display: 'flex',
            justifyContent: 'center',
          }}
        >
          <Box
            style={{
              flex: 1,
              minWidth: 0,
              maxWidth: collapsed ? 720 : 880,
              transition: 'max-width 250ms ease',
            }}
          >
            {centerVariant === 'chat' && <NavbarChatSearch />}
            {centerVariant === 'flights' && (
              <Box style={{ paddingBlock: 4 }}>
                <FlightNavSearchBar />
              </Box>
            )}
            {centerVariant === 'hotels' && (
              <Box style={{ paddingBlock: 4 }}>
                <HotelNavSearchBar />
              </Box>
            )}
          </Box>
        </Box>

        {/* Right cluster */}
        {rightCluster}
      </Box>

      {/* ── Subtabs row: Flights · Stays · Day plan ───────────────────────── */}
      <Box
        style={{
          width: '100%',
          display: 'flex',
          flexDirection: 'row',
          alignItems: 'center',
          gap: isMobile ? 10 : collapsed ? 12 : 20,
          paddingInline: isMobile ? 12 : collapsed ? 24 : 32,
          paddingBlock: subtabsMinimal ? 4 : isMobile ? 10 : 16,
          backgroundColor: NAV_MIST,
          transition: 'padding 200ms ease, gap 200ms ease',
        }}
      >
        {/* Logo-width spacer (desktop) — mirrors bar-row logo column */}
        <Box
          aria-hidden
          style={{
            display: isMobile ? 'none' : 'block',
            width: collapsed ? 96 : 135,
            flexShrink: 0,
            transition: 'width 250ms ease',
          }}
        />

        {/* Subtabs centered */}
        <Box
          component="nav"
          aria-label="Section navigation"
          data-testid={subtabsMinimal ? 'subtabs-minimal' : 'subtabs-expanded'}
          style={{ flex: 1, minWidth: 0, display: 'flex', justifyContent: 'center' }}
        >
          <Box
            style={{
              display: 'flex',
              flexDirection: 'row',
              justifyContent: 'center',
              gap: subtabsMinimal
                ? isMobile ? 16 : 24
                : isMobile ? 32 : 48,
            }}
          >
            {SUBTABS.map((tab) => {
              const isActive = activeSection === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => navigate(tab.route)}
                  aria-current={isActive ? 'page' : undefined}
                  style={{
                    display: 'flex',
                    flexDirection: subtabsMinimal ? 'row' : 'column',
                    alignItems: 'center',
                    gap: subtabsMinimal ? 6 : 5,
                    cursor: 'pointer',
                    paddingInline: subtabsMinimal ? 10 : 16,
                    paddingTop: subtabsMinimal ? 4 : 5,
                    paddingBottom: subtabsMinimal ? 4 : 8,
                    borderBottom: '2px solid',
                    borderLeft: 'none',
                    borderRight: 'none',
                    borderTop: 'none',
                    borderColor: isActive ? NAV_NAVY : 'transparent',
                    color: NAV_NAVY,
                    background: 'none',
                    fontFamily: 'inherit',
                    transition: 'border-color 200ms ease, padding 200ms ease',
                  }}
                >
                  <Text
                    component="span"
                    style={{
                      fontSize: subtabsMinimal ? 14 : isMobile ? 22 : 26,
                      lineHeight: 1,
                      display: subtabsMinimal
                        ? isMobile ? 'none' : 'inline-block'
                        : 'inline-block',
                      transition: 'font-size 250ms ease',
                    }}
                  >
                    {tab.icon}
                  </Text>
                  <Text
                    style={{
                      fontSize: subtabsMinimal ? 12 : 13,
                      fontWeight: isActive ? 700 : 600,
                      color: isActive ? NAV_NAVY : NAV_NAVY_MID,
                      transition: 'font-size 250ms ease, color 200ms ease',
                    }}
                  >
                    {tab.label}
                  </Text>
                </button>
              );
            })}
          </Box>
        </Box>

        {/* Right-cluster ghost spacer (desktop) — keeps subtabs centered */}
        <Box
          aria-hidden
          style={{
            display: isMobile ? 'none' : 'block',
            opacity: 0,
            pointerEvents: 'none',
            flexShrink: 0,
          }}
        >
          {rightCluster}
        </Box>
      </Box>

      {/* ── Hamburger drawer ─────────────────────────────────────────────── */}
      <Drawer
        opened={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        position="right"
        size={280}
        withCloseButton={false}
        padding={0}
        zIndex={1200}
        styles={{
          body: { padding: 0 },
        }}
      >
        <Stack gap={0} style={{ padding: 20, height: '100%' }}>
          <Box
            style={{
              display: 'flex',
              flexDirection: 'row',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: 16,
            }}
          >
            <Text style={{ fontSize: 14, fontWeight: 800, color: NAV_NAVY }}>Menu</Text>
            <ActionIcon
              onClick={() => setDrawerOpen(false)}
              variant="subtle"
              aria-label="Close menu"
            >
              <CloseIcon size={20} />
            </ActionIcon>
          </Box>

          <MenuItem icon={<Compass size={20} />} label="Explore" onClick={() => handleMenuNav('/')} />
          <MenuItem
            icon={<MessageCircle size={20} />}
            label="Chat"
            onClick={() => handleMenuNav(isAuthenticated ? ROUTES.CHAT : ROUTES.PUBLIC_CHAT)}
          />
          <MenuItem icon={<Heart size={20} />} label="Trips" onClick={() => handleMenuNav(ROUTES.ITINERARIES)} />
          {isAuthenticated && (
            <MenuItem icon={<Luggage size={20} />} label="Profile" onClick={() => handleMenuNav(ROUTES.PROFILE)} />
          )}

          {isAuthenticated && isAdmin && (
            <>
              <Divider my="xs" color={NAV_LINE} />
              <Text style={{ fontSize: 10, fontWeight: 700, color: NAV_NAVY_MID, letterSpacing: '0.06em', textTransform: 'uppercase', padding: '4px 12px 2px' }}>
                Administration
              </Text>
              <MenuItem icon={<Tag size={20} />} label="Discounts" onClick={() => handleMenuNav(ROUTES.ADMIN_DISCOUNTS)} />
              <MenuItem icon={<CalendarDays size={20} />} label="Booking Management" onClick={() => handleMenuNav(ROUTES.ADMIN_BOOKINGS)} />
            </>
          )}

          {isAuthenticated && (
            <>
              <Divider my="md" color={NAV_LINE} />
              <MenuItem icon={<LogOut size={20} />} label="Sign out" onClick={handleSignOut} />
            </>
          )}

          {!isAuthenticated && (
            <>
              <Divider my="md" color={NAV_LINE} />
              <Box style={{ paddingTop: 4 }}>
                <Button
                  onClick={handleSignIn}
                  fullWidth
                  radius="xl"
                  style={{ backgroundColor: NAV_NAVY, color: 'white', fontWeight: 700 }}
                >
                  Log in
                </Button>
              </Box>
            </>
          )}
        </Stack>
      </Drawer>
    </Box>
  );
}

import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Avatar,
  Box,
  Group,
  Loader,
  Stack,
  Text,
  UnstyledButton,
} from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import {
  User,
  Users,
  Luggage,
  Lock,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Pencil,
  Plane,
  Building2,
  Map,
} from 'lucide-react';
import { useIsAdmin } from '@/hooks';
import { useGetProfileQuery } from '@/api/usersApi';
import { useGetMyBookingsQuery } from '@/api/flightsApi';
import { useGetMyHotelBookingsQuery } from '@/api/hotelsApi';
import { useGetItinerariesQuery } from '@/api/itinerariesApi';
import { getSavedItineraryCardSummary } from '@/features/itinerary/utils/savedItineraryCardSummary';
import { AccountSection } from './AccountSection';
import { PreferencesSection } from './preferences';
import { TravelDetailsSection } from './travelDetails';
import { FlightBookingsSection } from './FlightBookingsSection';
import { HotelBookingsSection } from './HotelBookingsSection';
import { UpcomingTripsSection } from './_wip/UpcomingTripsSection';
import { SecuritySection } from './SecuritySection';
import { NAVY, NAVY4, MUTED, LINE, MIST } from '../profileTokens';

type ActiveSection =
  | 'about'
  | 'companions'
  | 'trips'
  | 'bookings-flights'
  | 'bookings-hotels'
  | 'security';

// ── Sidebar nav item ─────────────────────────────────────────────────────────

function SidebarNavItem({
  icon,
  label,
  active,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  const [hovered, setHovered] = useState(false);
  const bg = active || hovered ? MIST : 'transparent';
  const color = active || hovered ? NAVY : NAVY4;
  const fw: React.CSSProperties['fontWeight'] = active ? 700 : 500;

  return (
    <Box
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '12px 20px',
        cursor: 'pointer',
        background: bg,
        borderLeft: active ? `3px solid ${NAVY}` : '3px solid transparent',
        color,
        fontWeight: fw,
        fontSize: 14,
        transition: 'all 120ms',
        userSelect: 'none',
      }}
    >
      {icon}
      <Text style={{ fontSize: 14, fontWeight: fw, color }}>{label}</Text>
    </Box>
  );
}

// ── Sidebar bookings sub-item ────────────────────────────────────────────────

function BookingsSubItem({
  icon,
  label,
  active,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  const [hovered, setHovered] = useState(false);
  const bg = active ? '#ECEEFE' : hovered ? MIST : 'transparent';
  const color = active || hovered ? NAVY : NAVY4;
  const fw: React.CSSProperties['fontWeight'] = active ? 600 : 500;

  return (
    <Box
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        padding: '10px 20px 10px 48px',
        cursor: 'pointer',
        background: bg,
        borderLeft: active ? `3px solid ${NAVY}` : '3px solid transparent',
        color,
        fontWeight: fw,
        fontSize: 13,
        transition: 'all 120ms',
        userSelect: 'none',
      }}
    >
      {icon}
      <Text style={{ fontSize: 13, fontWeight: fw, color }}>{label}</Text>
    </Box>
  );
}

// ── Mobile tab bar config (static — no component state dependency) ───────────

const MOBILE_TABS: Array<{
  id: 'about' | 'companions' | 'trips' | 'bookings' | 'security';
  label: string;
  icon: React.ReactNode;
}> = [
  { id: 'about', label: 'About', icon: <User size={18} /> },
  { id: 'companions', label: 'Companions', icon: <Users size={18} /> },
  { id: 'trips', label: 'Trips', icon: <Map size={18} /> },
  { id: 'bookings', label: 'Bookings', icon: <Luggage size={18} /> },
  { id: 'security', label: 'Security', icon: <Lock size={18} /> },
];

// ── About sub-view ───────────────────────────────────────────────────────────

type AboutSubView = 'personal' | 'travel' | 'flight' | 'hotel';

const ABOUT_PREF_ROWS: Array<{
  key: AboutSubView;
  icon: React.ReactNode;
  title: string;
  subtitle: string;
}> = [
  { key: 'personal', icon: <User size={18} color={MUTED} />, title: 'Personal information', subtitle: 'Name, email, phone' },
  { key: 'travel', icon: <Map size={18} color={MUTED} />, title: 'Travel preferences', subtitle: 'Budget, travel style, interests' },
  { key: 'flight', icon: <Plane size={18} color={MUTED} />, title: 'Flight preferences', subtitle: 'Seat, timings, airlines' },
  { key: 'hotel', icon: <Building2 size={18} color={MUTED} />, title: 'Hotel preferences', subtitle: 'Accommodation, amenities, location' },
];

function AboutBackButton({ onClick }: { onClick: () => void }) {
  return (
    <UnstyledButton
      onClick={onClick}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        fontSize: 14,
        fontWeight: 600,
        color: NAVY4,
        cursor: 'pointer',
        background: 'transparent',
        transition: 'color 120ms',
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLElement).style.color = NAVY;
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLElement).style.color = NAVY4;
      }}
    >
      <ChevronLeft size={16} />
      Back to profile
    </UnstyledButton>
  );
}

// ── Main profile page v2 ─────────────────────────────────────────────────────

/**
 * Profile page v2 — sidebar navigation design ported from RossMyvoya.
 * Reuses all existing Voya profile section components with no new API calls or features.
 * Bookings sidebar item expands to reveal Flights and Hotels sub-sections.
 */
export function ProfilePage() {
  const isMobile = useMediaQuery('(max-width: 768px)');
  const [activeSection, setActiveSection] = useState<ActiveSection>('about');
  const [bookingsOpen, setBookingsOpen] = useState(true);
  const [aboutSubView, setAboutSubView] = useState<AboutSubView | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();

  // Deep-link support: `/profile?section=flight|hotel|travel|personal` opens the
  // matching preferences sub-view (e.g. flight/hotel search pages link here).
  useEffect(() => {
    const section = searchParams.get('section');
    if (section === 'flight' || section === 'hotel' || section === 'travel' || section === 'personal') {
      if (activeSection !== 'about' || aboutSubView !== section) {
        setActiveSection('about');
        setAboutSubView(section);
      }
      const next = new URLSearchParams(searchParams);
      next.delete('section');
      setSearchParams(next, { replace: true });
    }
  }, [searchParams, setSearchParams, activeSection, aboutSubView]);

  const { data: profile, isLoading } = useGetProfileQuery();
  const { data: flightBookings } = useGetMyBookingsQuery({ limit: 20 });
  const { data: hotelBookings } = useGetMyHotelBookingsQuery({ limit: 20 });
  const {
    data: itineraries,
    isLoading: isItinerariesLoading,
    isError: isItinerariesError,
    refetch: refetchItineraries,
  } = useGetItinerariesQuery();
  const upcomingTripCards = useMemo(
    () => (itineraries ?? []).map(getSavedItineraryCardSummary),
    [itineraries],
  );

  const user = profile?.user;
  const isAdmin = useIsAdmin();
  const flightCount = flightBookings?.length ?? 0;
  const hotelCount = hotelBookings?.length ?? 0;
  const tripsCount = itineraries?.length ?? 0;
  const displayName =
    [user?.firstName, user?.lastName].filter(Boolean).join(' ') ||
    user?.email ||
    'Traveller';
  const initials =
    [user?.firstName?.[0], user?.lastName?.[0]].filter(Boolean).join('').toUpperCase() ||
    '?';

  const isBookingsActive =
    activeSection === 'bookings-flights' || activeSection === 'bookings-hotels';

  function handleNavClick(s: ActiveSection) {
    setAboutSubView(null);
    setActiveSection(s);
  }

  // Mobile collapses flights/hotels into a single "bookings" tab
  const mobileActiveTab: 'about' | 'companions' | 'trips' | 'bookings' | 'security' =
    isBookingsActive
      ? 'bookings'
      : (activeSection as 'about' | 'companions' | 'trips' | 'security');

  function handleMobileTabClick(tab: 'about' | 'companions' | 'trips' | 'bookings' | 'security') {
    setAboutSubView(null);
    if (tab === 'bookings') {
      // Stay on current booking sub-section if already in bookings, else default to flights
      setActiveSection(isBookingsActive ? activeSection : 'bookings-flights');
    } else {
      setActiveSection(tab as ActiveSection);
    }
  }

  // ── Bookings content (shared between mobile sub-tabs and desktop sections) ──

  function renderBookingsContent() {
    return (
      <Stack gap="lg">
        {/* Mobile sub-tab strip */}
        {isMobile && (
          <Group gap={8} px={16} pt={16}>
            {(
              [
                { id: 'bookings-flights' as ActiveSection, icon: <Plane size={14} />, label: 'Flights' },
                { id: 'bookings-hotels' as ActiveSection, icon: <Building2 size={14} />, label: 'Hotels' },
              ] as const
            ).map((sub) => {
              const sel = activeSection === sub.id;
              return (
                <UnstyledButton
                  key={sub.id}
                  onClick={() => setActiveSection(sub.id)}
                  style={{
                    height: 32,
                    borderRadius: 8,
                    padding: '6px 14px',
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 6,
                    ...(sel
                      ? { background: NAVY, color: 'white' }
                      : {
                          border: `1px solid ${LINE}`,
                          color: NAVY4,
                          background: 'transparent',
                        }),
                  }}
                >
                  {sub.icon}
                  {sub.label}
                </UnstyledButton>
              );
            })}
          </Group>
        )}

        {activeSection === 'bookings-flights' ? (
          <FlightBookingsSection />
        ) : (
          <HotelBookingsSection />
        )}
      </Stack>
    );
  }

  // ── Content renderer ─────────────────────────────────────────────────────

  function renderContent() {
    if (isLoading) {
      return (
        <Group justify="center" py="xl">
          <Loader size={32} color={NAVY} />
        </Group>
      );
    }

    if (activeSection === 'about') {
      const prefs = profile?.preferences;

      const completionMap: Record<AboutSubView, boolean> = {
        personal: !!(user?.firstName && user?.mobile),
        travel: !!(
          prefs?.travelStyle?.budgetMindset ||
          prefs?.travelStyle?.travelPace ||
          (prefs?.travelStyle?.primaryGoals?.length ?? 0) > 0
        ),
        flight: !!prefs?.flights?.seatPreference,
        hotel:
          (prefs?.hotels?.hotelStyle?.length ?? 0) > 0 ||
          (prefs?.hotels?.amenities?.length ?? 0) > 0,
      };

      // Sub-view: personal information
      if (aboutSubView === 'personal') {
        return (
          <Stack gap="lg">
            <AboutBackButton onClick={() => setAboutSubView(null)} />
            <AccountSection user={user} />
          </Stack>
        );
      }

      // Sub-view: preferences (travel / flight / hotel)
      if (aboutSubView === 'travel' || aboutSubView === 'flight' || aboutSubView === 'hotel') {
        const sectionMap = { travel: 'travelStyle', flight: 'flights', hotel: 'hotels' } as const;
        return (
          <Stack gap="lg">
            <AboutBackButton onClick={() => setAboutSubView(null)} />
            <PreferencesSection
              preferences={prefs}
              documentExists={prefs?.documentExists ?? false}
              section={sectionMap[aboutSubView]}
            />
          </Stack>
        );
      }

      // Default: hero card + preferences list
      return (
        <Stack gap="lg">
          {/* Profile hero card */}
          <Box
            style={{
              background: 'white',
              borderRadius: 14,
              border: `1px solid ${LINE}`,
              padding: 24,
            }}
          >
            <Box
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: 20,
                flexWrap: isMobile ? 'wrap' : 'nowrap',
              }}
            >
              {/* Avatar with verified badge */}
              <Box style={{ position: 'relative', flexShrink: 0 }}>
                <Avatar
                  src={user?.photoUrls?.lg ?? user?.profileImage ?? undefined}
                  size={isMobile ? 80 : 100}
                  radius={100}
                  style={{
                    border: '3px solid white',
                    boxShadow: '0 2px 12px rgba(23,27,99,0.12)',
                    background: MIST,
                  }}
                >
                  <Text
                    style={{
                      fontSize: isMobile ? 26 : 32,
                      fontWeight: 900,
                      color: NAVY,
                    }}
                  >
                    {initials}
                  </Text>
                </Avatar>
                <Box
                  style={{
                    position: 'absolute',
                    bottom: 2,
                    right: 2,
                    width: 22,
                    height: 22,
                    borderRadius: '50%',
                    background: NAVY,
                    border: '2px solid white',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <svg width="10" height="10" viewBox="0 0 12 12" fill="none">
                    <path
                      d="M2 6l3 3 5-5"
                      stroke="white"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </Box>
              </Box>

              {/* Name, email, edit button */}
              <Box style={{ flex: 1, minWidth: 0, paddingTop: 4 }}>
                <Text
                  style={{
                    fontSize: isMobile ? 18 : 22,
                    fontWeight: 900,
                    color: NAVY,
                    lineHeight: 1.15,
                  }}
                >
                  {user?.firstName || displayName.split(' ')[0]}
                </Text>
                <Text
                  style={{ fontSize: 13, color: MUTED, marginTop: 2, marginBottom: 14 }}
                >
                  {user?.email ?? ''}
                </Text>
                <UnstyledButton
                  onClick={() => setAboutSubView('personal')}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 6,
                    border: `1px solid ${LINE}`,
                    borderRadius: 999,
                    padding: '4px 12px',
                    fontSize: 12,
                    fontWeight: 600,
                    color: NAVY,
                    cursor: 'pointer',
                    background: 'transparent',
                    transition: 'background 120ms',
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLElement).style.background = MIST;
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLElement).style.background = 'transparent';
                  }}
                >
                  <Pencil size={13} />
                  Edit profile
                </UnstyledButton>
              </Box>

              {/* Stats */}
              <Box
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  alignSelf: isMobile ? 'auto' : 'center',
                  borderLeft: isMobile ? 'none' : `1px solid ${LINE}`,
                  paddingLeft: isMobile ? 0 : 24,
                  paddingTop: isMobile ? 16 : 0,
                  flexShrink: 0,
                  width: isMobile ? '100%' : 'auto',
                  borderTop: isMobile ? `1px solid ${LINE}` : 'none',
                  gap: 0,
                }}
              >
                {[
                  { value: tripsCount, label: 'Trips' },
                  { value: flightCount, label: 'Flights' },
                  { value: hotelCount, label: 'Stays' },
                ].map(({ value, label }, i, arr) => (
                  <Box
                    key={label}
                    style={{
                      textAlign: 'center',
                      padding: isMobile ? '12px 0' : '0 20px',
                      flex: isMobile ? 1 : undefined,
                      borderRight:
                        i < arr.length - 1 ? `1px solid ${LINE}` : undefined,
                    }}
                  >
                    <Text
                      style={{
                        fontSize: 20,
                        fontWeight: 900,
                        color: NAVY,
                        lineHeight: 1,
                      }}
                    >
                      {value}
                    </Text>
                    <Text style={{ fontSize: 12, color: MUTED, marginTop: 2 }}>
                      {label}
                    </Text>
                  </Box>
                ))}
              </Box>
            </Box>
          </Box>

          {/* Preferences list */}
          <Box
            style={{
              background: 'white',
              borderRadius: 14,
              border: `1px solid ${LINE}`,
              overflow: 'hidden',
            }}
          >
            <Box style={{ padding: '20px 20px 12px' }}>
              <Text style={{ fontSize: 15, fontWeight: 800, color: NAVY }}>
                Your preferences
              </Text>
              <Text style={{ fontSize: 13, color: MUTED, marginTop: 4 }}>
                Complete your profile so Voya can plan trips that match your style.
              </Text>
            </Box>

            {ABOUT_PREF_ROWS.map((row, i) => {
              const done = completionMap[row.key];
              return (
                <Box key={row.key}>
                  {i > 0 && (
                    <Box style={{ height: 1, background: LINE, margin: '0 20px' }} />
                  )}
                  <Box
                    onClick={() => setAboutSubView(row.key)}
                    onMouseEnter={(e) => {
                      (e.currentTarget as HTMLElement).style.background = MIST;
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLElement).style.background = 'transparent';
                    }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 12,
                      padding: '16px 20px',
                      cursor: 'pointer',
                      transition: 'background 120ms',
                    }}
                  >
                    <Box
                      style={{
                        width: 36,
                        height: 36,
                        borderRadius: 10,
                        background: MIST,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                      }}
                    >
                      {row.icon}
                    </Box>
                    <Box style={{ flex: 1, minWidth: 0 }}>
                      <Text
                        style={{
                          fontSize: 14,
                          fontWeight: 600,
                          color: NAVY,
                          lineHeight: 1.3,
                        }}
                      >
                        {row.title}
                      </Text>
                      <Text style={{ fontSize: 12, color: MUTED, marginTop: 2 }}>
                        {row.subtitle}
                      </Text>
                    </Box>
                    <Box
                      style={{
                        height: 24,
                        borderRadius: 999,
                        padding: '0 10px',
                        display: 'inline-flex',
                        alignItems: 'center',
                        fontSize: 11,
                        fontWeight: 700,
                        flexShrink: 0,
                        ...(done
                          ? { background: '#E8EAFC', color: NAVY }
                          : { border: `1px solid ${LINE}`, color: MUTED }),
                      }}
                    >
                      {done ? 'Complete' : 'Not set'}
                    </Box>
                    <ChevronRight size={18} color={MUTED} style={{ flexShrink: 0 }} />
                  </Box>
                </Box>
              );
            })}
          </Box>
        </Stack>
      );
    }

    if (activeSection === 'companions') {
      return <TravelDetailsSection profile={profile} />;
    }

    if (activeSection === 'trips') {
      return (
        <UpcomingTripsSection
          trips={upcomingTripCards}
          isLoading={isItinerariesLoading}
          isError={isItinerariesError}
          onRetry={refetchItineraries}
        />
      );
    }

    if (isBookingsActive) {
      return renderBookingsContent();
    }

    if (activeSection === 'security') {
      return <SecuritySection isAdmin={isAdmin} />;
    }

    return null;
  }

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <Box style={{ width: '100%', height: '100%', backgroundColor: '#F7F8FC', display: 'flex', flexDirection: 'column' }}>
      {/* Mobile top tab bar */}
      {isMobile && (
        <Box
          component="nav"
          style={{
            position: 'sticky',
            top: 0,
            zIndex: 10,
            background: 'white',
            borderBottom: `1px solid ${LINE}`,
          }}
        >
          <Box style={{ display: 'flex', width: '100%' }}>
            {MOBILE_TABS.map((tab) => {
              const active = mobileActiveTab === tab.id;
              return (
                <UnstyledButton
                  key={tab.id}
                  onClick={() => handleMobileTabClick(tab.id)}
                  style={{
                    flex: 1,
                    minWidth: 0,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: 3,
                    padding: '10px 2px',
                    color: active ? NAVY : NAVY4,
                    borderBottom: active
                      ? `2px solid ${NAVY}`
                      : '2px solid transparent',
                    marginBottom: -1,
                    transition: 'color 120ms',
                    background: 'transparent',
                  }}
                >
                  {tab.icon}
                  <Text
                    style={{
                      fontSize: 10,
                      fontWeight: active ? 700 : 500,
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      maxWidth: '100%',
                      color: 'inherit',
                    }}
                  >
                    {tab.label}
                  </Text>
                </UnstyledButton>
              );
            })}
          </Box>
        </Box>
      )}

      <Box
        style={{
          flex: 1,
          minHeight: 0,
          maxWidth: 1060,
          margin: '0 auto',
          width: '100%',
          padding: isMobile ? '0' : '32px 24px',
          display: 'flex',
          flexDirection: 'column',
          boxSizing: 'border-box',
        }}
      >
        <Box style={{ flex: 1, minHeight: 0, display: 'flex', gap: 24 }}>
          {/* Desktop sidebar */}
          {!isMobile && (
            <Box
              component="nav"
              style={{
                width: 240,
                flexShrink: 0,
                background: 'white',
                borderRadius: 14,
                border: `1px solid ${LINE}`,
                overflow: 'hidden',
                alignSelf: 'flex-start',
              }}
            >
              {/* Sidebar header */}
              <Box
                style={{
                  padding: '16px 20px',
                  borderBottom: `1px solid ${LINE}`,
                }}
              >
                <Text style={{ fontSize: 13, fontWeight: 700, color: NAVY }}>
                  Profile
                </Text>
              </Box>

              {/* About me */}
              <SidebarNavItem
                icon={<User size={18} />}
                label="About me"
                active={activeSection === 'about'}
                onClick={() => handleNavClick('about')}
              />

              {/* Travel companions */}
              <SidebarNavItem
                icon={<Users size={18} />}
                label="Travel companions"
                active={activeSection === 'companions'}
                onClick={() => handleNavClick('companions')}
              />

              {/* Trips */}
              <SidebarNavItem
                icon={<Map size={18} />}
                label="Trips"
                active={activeSection === 'trips'}
                onClick={() => handleNavClick('trips')}
              />

              {/* Bookings — expandable dropdown */}
              <BookingsDropdownItem
                active={isBookingsActive}
                open={bookingsOpen}
                flightsActive={activeSection === 'bookings-flights'}
                hotelsActive={activeSection === 'bookings-hotels'}
                onHeaderClick={() => {
                  if (!isBookingsActive) {
                    setBookingsOpen(true);
                    setActiveSection('bookings-flights');
                  } else {
                    setBookingsOpen((prev) => !prev);
                  }
                }}
                onFlightsClick={() => setActiveSection('bookings-flights')}
                onHotelsClick={() => setActiveSection('bookings-hotels')}
              />

              {/* Login & security */}
              <SidebarNavItem
                icon={<Lock size={18} />}
                label="Login & security"
                active={activeSection === 'security'}
                onClick={() => handleNavClick('security')}
              />
            </Box>
          )}

          {/* Content area */}
          <Box
            style={{
              flex: 1,
              minWidth: 0,
              minHeight: 0,
              overflowY: 'auto',
              padding: isMobile ? '24px 16px 32px' : '0',
            }}
          >
            {renderContent()}
          </Box>
        </Box>
      </Box>
    </Box>
  );
}

// ── Bookings dropdown item (extracted to keep ProfilePage readable) ─────────

function BookingsDropdownItem({
  active,
  open,
  flightsActive,
  hotelsActive,
  onHeaderClick,
  onFlightsClick,
  onHotelsClick,
}: {
  active: boolean;
  open: boolean;
  flightsActive: boolean;
  hotelsActive: boolean;
  onHeaderClick: () => void;
  onFlightsClick: () => void;
  onHotelsClick: () => void;
}) {
  const [hovered, setHovered] = useState(false);
  const bg = active || hovered ? MIST : 'transparent';
  const color = active || hovered ? NAVY : NAVY4;
  const fw: React.CSSProperties['fontWeight'] = active ? 700 : 500;

  return (
    <Box>
      {/* Bookings header row */}
      <Box
        onClick={onHeaderClick}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 20px',
          cursor: 'pointer',
          background: bg,
          borderLeft: active ? `3px solid ${NAVY}` : '3px solid transparent',
          color,
          fontWeight: fw,
          fontSize: 14,
          transition: 'all 120ms',
          userSelect: 'none',
        }}
      >
        <Box style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Luggage size={18} />
          <Text style={{ fontSize: 14, fontWeight: fw, color }}>Bookings</Text>
        </Box>
        {open ? (
          <ChevronDown size={16} color={color} />
        ) : (
          <ChevronRight size={16} color={color} />
        )}
      </Box>

      {/* Sub-items */}
      {open && (
        <>
          <BookingsSubItem
            icon={<Plane size={15} />}
            label="Flights"
            active={flightsActive}
            onClick={onFlightsClick}
          />
          <BookingsSubItem
            icon={<Building2 size={15} />}
            label="Hotels"
            active={hotelsActive}
            onClick={onHotelsClick}
          />
        </>
      )}
    </Box>
  );
}

import { Box } from '@mantine/core';

import { AuthModal } from '@/features/auth/components/AuthModal';

import { UnifiedHeader } from '@/components/layout/UnifiedHeader';
import { BottomNav } from '@/components/layout/BottomNav';
import { useBottomNavHidden } from '@/hooks';
import { ConfirmNewConversationDialog } from '@/features/chat/components/ConfirmNewConversationDialog';
import { LandingPageSections } from './LandingPageSections';
import { useLandingPageController } from './useLandingPageController';
import { RecentItinerariesStrip } from './components/RecentItinerariesStrip';

/**
 * Authenticated home (`/home`) — UnifiedHeader shell + V2 landing sections.
 * No marketing DOM ids on this route; see `docs/LANDING_DOM_IDS.md`.
 */
export function HomePage() {
  const bottomNavHidden = useBottomNavHidden();
  const {
    authModalOpen,
    handleSearchSubmit,
    handleCtaClick,
    confirmDialogProps,
    closeAuthModal,
  } = useLandingPageController();

  return (
    <Box
      style={{
        height: '100dvh',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <UnifiedHeader />
      <Box
        id="main-scroll-root"
        style={{
          flex: 1,
          minHeight: 0,
          overflowY: 'auto',
          overflowX: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <RecentItinerariesStrip />
        <LandingPageSections
          onSearchSubmit={handleSearchSubmit}
          onCtaClick={handleCtaClick}
        />
      </Box>
      <BottomNav hidden={bottomNavHidden} />
      <AuthModal open={authModalOpen} onClose={closeAuthModal} />
      <ConfirmNewConversationDialog {...confirmDialogProps} />
    </Box>
  );
}

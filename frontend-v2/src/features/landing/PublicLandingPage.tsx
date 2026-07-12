import { useEffect, useRef } from 'react';
import { Navigate, useLocation, useParams } from 'react-router-dom';
import { Box } from '@mantine/core';

import { useGetLandingPageBySlugQuery } from '@/api/strapiApi';
import { AuthModal } from '@/features/auth/components/AuthModal';
import { UnifiedHeader } from '@/components/layout/UnifiedHeader';
import { BottomNav } from '@/components/layout/BottomNav';
import { useBottomNavHidden } from '@/hooks';
import { ConfirmNewConversationDialog } from '@/features/chat/components/ConfirmNewConversationDialog';
import { LANDING_PAGE_IDS } from './landingPageIds';
import { LandingPageSections } from './LandingPageSections';
import { useLandingPageController } from './useLandingPageController';
import { RecentItinerariesStrip } from './components/RecentItinerariesStrip';

/**
 * Public marketing route (`/`) and campaign slug route (`/l/:slug`).
 *
 * When a slug is present the page fetches the matching Strapi landing page and
 * passes it to `LandingPageSections`; sections fall back to hardcoded data when
 * Strapi is unreachable. When the slug has no matching Strapi entry the component
 * redirects to `/` to prevent duplicate-content indexing.
 *
 * Guidelines for DOM ids: `docs/LANDING_DOM_IDS.md`.
 */
export function PublicLandingPage() {
  const location = useLocation();
  const { slug } = useParams<{ slug?: string }>();
  const rootRef = useRef<HTMLDivElement>(null);
  const {
    authModalOpen,
    handleSearchSubmit,
    handleCtaClick,
    confirmDialogProps,
    openAuthModal,
    closeAuthModal,
  } = useLandingPageController();

  const bottomNavHidden = useBottomNavHidden();
  const isDefaultPage = !slug;

  const { data: slugRails, isSuccess: slugQueryDone, isLoading: isSlugLoading } = useGetLandingPageBySlugQuery(slug ?? '', { skip: !slug });

  // Resolve `#anchor` inside this subtree only.
  useEffect(() => {
    const raw = location.hash.replace(/^#/, '');
    if (!raw) return;
    const root = rootRef.current;
    if (!root) return;
    const el = root.querySelector(`#${CSS.escape(raw)}`);
    if (!el) return;
    const frame = window.requestAnimationFrame(() => {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [location.pathname, location.hash]);

  // Slug was queried but not found in Strapi — redirect to avoid a 200 duplicate-content page.
  if (slug && slugQueryDone && slugRails === null) {
    return <Navigate to="/" replace />;
  }

  return (
    <Box
      style={{
        height: '100dvh',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <UnifiedHeader
        domIds={isDefaultPage ? LANDING_PAGE_IDS.nav : undefined}
        onSignInClick={openAuthModal}
      />
      <Box
        ref={rootRef}
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
          ids={isDefaultPage ? LANDING_PAGE_IDS : undefined}
          strapiData={slug && !isSlugLoading && slugRails !== null ? slugRails : undefined}
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

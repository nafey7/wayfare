import { Box } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';

import { useBottomNavHidden } from '@/hooks';
import { UnifiedHeader } from './UnifiedHeader';
import { BottomNav } from './BottomNav';

interface MainLayoutProps {
  children: React.ReactNode;
}

/**
 * Main layout wrapper for authenticated pages.
 * Uses the unified sticky header (matching RossMyvoya design) and mobile BottomNav.
 */
export function MainLayout({ children }: MainLayoutProps) {
  const isMobile = useMediaQuery('(max-width: 768px)');
  const bottomNavHidden = useBottomNavHidden();

  return (
    <Box
      style={{
        height: '100svh',
        overflow: 'hidden',
        background: 'var(--mantine-color-body)',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <UnifiedHeader />
      <Box
        id="main-scroll-root"
        component="main"
        style={{
          flex: 1,
          minHeight: 0,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'auto',
          // Reserve space for the fixed BottomNav only while it's visible; transition
          // syncs with BottomNav's translateY(100%) so content doesn't jump on re-appear.
          paddingBottom: isMobile && !bottomNavHidden
            ? 'calc(48px + env(safe-area-inset-bottom))'
            : undefined,
          transition: 'padding-bottom 240ms cubic-bezier(0.32, 0.72, 0, 1)',
        }}
      >
        {children}
      </Box>
      <BottomNav hidden={bottomNavHidden} />
    </Box>
  );
}

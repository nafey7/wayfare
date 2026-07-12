import { useCallback, type ReactNode } from 'react';
import { Box, Container } from '@mantine/core';
import { zIndex } from '@/theme';
import { UnifiedHeader } from '@/components/layout/UnifiedHeader';
import { OnboardingHeader } from './OnboardingHeader';
import { AuthModal } from '@/features/auth/components/AuthModal';
import { useAppDispatch, useAppSelector } from '@/store';
import { closeAuthModal, selectAuthModalOpen } from '@/store/slices/uiSlice';

interface OnboardingLayoutProps {
  step: 1 | 2 | 3;
  title: string;
  subtitle?: string;
  /** Set false on Screen 1 where the title is rendered inside the hero. */
  showTitle?: boolean;
  children: ReactNode;
}

/**
 * Wraps each onboarding screen with:
 *  1. UnifiedHeader at the top
 *  2. Sticky sub-header with step navigation arrows + screen title
 *  3. Centered content container
 */
export function OnboardingLayout({
  step,
  title,
  subtitle,
  showTitle = true,
  children,
}: OnboardingLayoutProps) {
  const dispatch = useAppDispatch();
  const authModalOpen = useAppSelector(selectAuthModalOpen);
  const handleCloseAuthModal = useCallback(() => {
    dispatch(closeAuthModal());
  }, [dispatch]);

  return (
    <Box style={{ minHeight: '100svh', backgroundColor: 'var(--mantine-color-body)' }}>
      <UnifiedHeader />

      <Box
        style={{
          position: 'sticky',
          top: 'var(--unified-header-h, 120px)',
          zIndex: zIndex.subHeader,
          backgroundColor: 'var(--mantine-color-body)',
          borderBottom: '1px solid var(--mantine-color-default-border)',
          backdropFilter: 'saturate(150%) blur(6px)',
        }}
      >
        <Container size="xs" py="md">
          <OnboardingHeader
            step={step}
            title={showTitle ? title : ''}
            subtitle={showTitle ? subtitle : undefined}
          />
        </Container>
      </Box>

      <Container size="xs" py="lg">
        {children}
      </Container>
      <AuthModal open={authModalOpen} onClose={handleCloseAuthModal} />
    </Box>
  );
}

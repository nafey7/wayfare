import { useNavigate } from 'react-router-dom';
import { Avatar, Box, Button, Stack, Text, Title } from '@mantine/core';
import { useAppDispatch, useAppSelector } from '@/store';
import { selectIsAuthenticated } from '@/store/slices/authSlice';
import { openAuthModal } from '@/store/slices/uiSlice';
import { ROUTES } from '@/features/routing/constants';
import { OnboardingLayout } from '@/features/onboarding/components/OnboardingLayout';
import { stashPostAuthOnboardingPath } from '@/features/onboarding/utils/postAuthOnboardingPath';
import voyaAvatar from '@/assets/images/voya.jpeg';

interface OnboardingScreen1Props {
  variant?: 'new' | 'returning';
}

export function OnboardingScreen1({ variant = 'new' }: OnboardingScreen1Props) {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);

  const headline =
    variant === 'returning'
      ? 'Welcome back'
      : 'Plan your perfect trip with Voya AI';

  const pitch =
    variant === 'returning'
      ? 'Your chat is still here — pick up where you left off.'
      : 'Tell Voya about your trip — get flights, hotels, and a day-by-day plan, all personalised to how you travel.';

  const signInLabel =
    variant === 'returning'
      ? 'Sign in for the best experience'
      : 'Sign in to save your trip and preferences';

  const skipSubtext =
    variant === 'returning'
      ? 'Your previous chat is still saved on this device'
      : 'Your chat will be saved for 7 days on this device';

  function handleSignIn() {
    stashPostAuthOnboardingPath(ROUTES.ONBOARDING_TRIP);
    dispatch(openAuthModal());
  }

  function handleSkip() {
    navigate(ROUTES.ONBOARDING_LOCATION);
  }

  return (
    <OnboardingLayout step={1} title={headline} showTitle={false}>
      <Stack gap="lg">
        <Stack gap="md" align="center">
          <Avatar
            src={voyaAvatar}
            size={96}
            radius="50%"
            style={{
              boxShadow: 'var(--mantine-shadow-md)',
              border: '3px solid var(--mantine-color-body)',
            }}
            alt="Voya AI"
          />
          <Title order={2} ta="center" fw={700}>
            {headline}
          </Title>
          <Text size="md" ta="center" c="dimmed" style={{ maxWidth: 420 }}>
            {pitch}
          </Text>
          <Text size="sm" ta="center" fw={500}>
            ✈ Flights &nbsp;·&nbsp; 🏨 Hotels &nbsp;·&nbsp; 🗺 Day plans
          </Text>
        </Stack>

        {isAuthenticated ? (
          <Button size="md" fullWidth tt="none" onClick={() => navigate(ROUTES.ONBOARDING_TRIP)}>
            Continue to your trip
          </Button>
        ) : (
          <Stack gap="xs">
            <Text size="sm" c="dimmed" ta="center">
              {signInLabel}
            </Text>
            <Button size="md" fullWidth tt="none" onClick={handleSignIn}>
              Sign in with Google
            </Button>
            <Button size="md" variant="outline" fullWidth tt="none" onClick={handleSignIn}>
              Sign in with email
            </Button>
            <Button
              size="md"
              variant="subtle"
              fullWidth
              tt="none"
              c="dimmed"
              onClick={handleSkip}
            >
              Continue without signing in
            </Button>
            <Box ta="center">
              <Text size="xs" c="dimmed">
                {skipSubtext}
              </Text>
            </Box>
          </Stack>
        )}
      </Stack>
    </OnboardingLayout>
  );
}

import { useNavigate } from 'react-router-dom';
import { ActionIcon, Group, Stack, Text, Title } from '@mantine/core';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { ROUTES } from '@/features/routing/constants';

type Step = 1 | 2 | 3;

const STEP_TO_ROUTE: Record<Step, string> = {
  1: ROUTES.ONBOARDING_WELCOME,
  2: ROUTES.ONBOARDING_LOCATION,
  3: ROUTES.ONBOARDING_TRIP,
};

interface OnboardingHeaderProps {
  step: Step;
  title: string;
  subtitle?: string;
  onBack?: () => void;
  onForward?: () => void;
}

export function OnboardingHeader({
  step,
  title,
  subtitle,
  onBack,
  onForward,
}: OnboardingHeaderProps) {
  const navigate = useNavigate();

  const defaultBack = () => {
    if (step > 1) navigate(STEP_TO_ROUTE[(step - 1) as Step]);
  };
  const defaultForward = () => {
    if (step < 3) navigate(STEP_TO_ROUTE[(step + 1) as Step]);
  };

  const backDisabled = step === 1;
  const forwardDisabled = step === 3;

  return (
    <Stack gap="md">
      <Group justify="space-between" align="center">
        <ActionIcon
          size="lg"
          variant="subtle"
          color="gray"
          aria-label="Back"
          onClick={onBack ?? defaultBack}
          disabled={backDisabled}
          style={{ visibility: backDisabled ? 'hidden' : 'visible' }}
        >
          <ChevronLeft size={20} />
        </ActionIcon>

        <Text
          size="xs"
          c="dimmed"
          fw={600}
          style={{ textTransform: 'uppercase', letterSpacing: 1 }}
        >
          Step {step} of 3
        </Text>

        <ActionIcon
          size="lg"
          variant="subtle"
          color="gray"
          aria-label="Forward"
          onClick={onForward ?? defaultForward}
          disabled={forwardDisabled}
          style={{ visibility: forwardDisabled ? 'hidden' : 'visible' }}
        >
          <ChevronRight size={20} />
        </ActionIcon>
      </Group>

      {title && (
        <Stack gap={4} align="center">
          <Title order={3} ta="center" fw={700}>
            {title}
          </Title>
          {subtitle && (
            <Text size="sm" c="dimmed" ta="center">
              {subtitle}
            </Text>
          )}
        </Stack>
      )}
    </Stack>
  );
}

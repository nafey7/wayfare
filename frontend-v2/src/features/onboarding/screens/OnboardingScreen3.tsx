import { useMemo } from 'react';
import {
  Box,
  Button,
  Group,
  Loader,
  NumberInput,
  Paper,
  SegmentedControl,
  Stack,
  Text,
  UnstyledButton,
} from '@mantine/core';
import { DatePickerInput } from '@mantine/dates';
import dayjs from 'dayjs';
import { useAppDispatch, useAppSelector } from '@/store';
import { selectCurrentUser } from '@/store/slices/authSlice';
import {
  selectOnboardingTripDetails,
  setTripDetails,
  togglePrimaryGoal,
} from '@/store/slices/onboardingSlice';
import {
  BUDGET_MINDSET_PREFERENCE_OPTIONS,
  PRIMARY_GOAL_PREFERENCE_OPTIONS,
  TRAVEL_PACE_PREFERENCE_OPTIONS,
} from '@/features/onboarding/constants/travelStylePreferenceOptions';
import type { OnboardingTripDetails, PrimaryGoal, TravelPace } from '@/types/onboarding';
import type { BudgetMindset } from '@/types/trip';
import {
  CitySearchAutocomplete,
  type CitySearchOption,
} from '@/features/onboarding/components/CitySearchAutocomplete';
import { tripCityOptionFromStored } from '@/features/onboarding/openMeteoGeocoding';
import { useStartPlanning } from '@/features/onboarding/useStartPlanning';
import { OnboardingLayout } from '@/features/onboarding/components/OnboardingLayout';

function parseOnboardingDate(value: string): Date | null {
  const local = dayjs(value, 'YYYY-MM-DD', true);
  if (local.isValid()) return local.toDate();
  const parsed = dayjs(value);
  return parsed.isValid() ? parsed.toDate() : null;
}

const MAX_PAX = 10;

const PILL_BASE: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  height: 28,
  paddingLeft: 12,
  paddingRight: 12,
  borderRadius: 14,
  fontSize: 13,
  fontWeight: 500,
  cursor: 'pointer',
  border: '1px solid var(--mantine-color-default-border)',
  backgroundColor: 'transparent',
  color: 'var(--mantine-color-dark-8)',
};

const PILL_SELECTED: React.CSSProperties = {
  ...PILL_BASE,
  border: '1px solid var(--mantine-color-brand-6)',
  backgroundColor: 'var(--mantine-color-brand-6)',
  color: 'var(--mantine-color-white)',
};

export function OnboardingScreen3() {
  const dispatch = useAppDispatch();
  const { startPlanning, continueToChat, isGuestAwaitingChatConfig } = useStartPlanning();

  const user = useAppSelector(selectCurrentUser);
  const trip = useAppSelector(selectOnboardingTripDetails);

  const update = (patch: Partial<OnboardingTripDetails>) =>
    dispatch(setTripDetails(patch));

  const headline = user?.firstName
    ? `Welcome back, ${user.firstName}`
    : 'Tell us about your trip';
  const subtext = user?.firstName
    ? 'Where are you heading next?'
    : 'A few details so Voya can find what matters to you.';

  const totalPax =
    trip.passengers.adults + trip.passengers.children + trip.passengers.infants;

  const canSubmit = !!trip.destination && !!trip.departureDate;

  const originValue = useMemo(
    (): CitySearchOption | null => tripCityOptionFromStored(trip.origin),
    [trip.origin]
  );
  const destinationValue = useMemo(
    (): CitySearchOption | null => tripCityOptionFromStored(trip.destination),
    [trip.destination]
  );

  function onOriginChange(value: CitySearchOption | null) {
    update({ origin: value?.displayLine ?? '' });
  }
  function onDestinationChange(value: CitySearchOption | null) {
    update({ destination: value?.displayLine ?? '' });
  }

  const departureDate = trip.departureDate ? parseOnboardingDate(trip.departureDate) : null;
  const returnDate = trip.returnDate ? parseOnboardingDate(trip.returnDate) : null;
  const today = new Date();

  return (
    <OnboardingLayout step={3} title={headline} subtitle={subtext}>
      <Stack gap="md">
        <Paper withBorder p="md">
          <Stack gap="md">
            <CitySearchAutocomplete
              label="Flying from (optional)"
              value={originValue}
              onChange={onOriginChange}
            />
            <CitySearchAutocomplete
              label="Going to"
              value={destinationValue}
              onChange={onDestinationChange}
            />

            <SegmentedControl
              value={trip.tripType}
              onChange={(value) => {
                update({
                  tripType: value as 'oneWay' | 'roundTrip',
                  returnDate: value === 'oneWay' ? null : trip.returnDate,
                });
              }}
              data={[
                { value: 'roundTrip', label: 'Round trip' },
                { value: 'oneWay', label: 'One way' },
              ]}
              size="sm"
              fullWidth
            />

            <Group gap="xs" wrap="nowrap">
              <DatePickerInput
                label="Depart"
                value={departureDate}
                minDate={today}
                onChange={(d) =>
                  update({
                    departureDate: d ? dayjs(d).format('YYYY-MM-DD') : null,
                  })
                }
                placeholder="Add date"
                style={{ flex: 1 }}
              />
              {trip.tripType === 'roundTrip' && (
                <DatePickerInput
                  label="Return"
                  value={returnDate}
                  minDate={departureDate ?? today}
                  onChange={(d) =>
                    update({
                      returnDate: d ? dayjs(d).format('YYYY-MM-DD') : null,
                    })
                  }
                  placeholder="Add date"
                  style={{ flex: 1 }}
                />
              )}
            </Group>

            <Group gap="xs" wrap="nowrap">
              <NumberInput
                label="Adults"
                value={trip.passengers.adults}
                onChange={(v) =>
                  update({
                    passengers: {
                      ...trip.passengers,
                      adults: Math.max(1, Math.min(MAX_PAX, Number(v) || 1)),
                    },
                  })
                }
                min={1}
                max={MAX_PAX}
                style={{ flex: 1 }}
              />
              <NumberInput
                label="Children"
                value={trip.passengers.children}
                onChange={(v) =>
                  update({
                    passengers: {
                      ...trip.passengers,
                      children: Math.max(0, Math.min(MAX_PAX, Number(v) || 0)),
                    },
                  })
                }
                min={0}
                max={MAX_PAX}
                style={{ flex: 1 }}
              />
              <NumberInput
                label="Infants"
                value={trip.passengers.infants}
                onChange={(v) =>
                  update({
                    passengers: {
                      ...trip.passengers,
                      infants: Math.max(0, Math.min(MAX_PAX, Number(v) || 0)),
                    },
                  })
                }
                min={0}
                max={MAX_PAX}
                style={{ flex: 1 }}
              />
            </Group>
            {totalPax > MAX_PAX && (
              <Text size="xs" c="red">
                Max {MAX_PAX} passengers combined
              </Text>
            )}
          </Stack>
        </Paper>

        <Paper withBorder p="md">
          <Stack gap="md">
            <Text size="sm" fw={600}>
              Preferences{' '}
              <Text component="span" size="sm" c="dimmed">
                (optional)
              </Text>
            </Text>

            <Stack gap={4}>
              <Text size="xs" c="dimmed">
                Travel Pace
              </Text>
              <Box style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {TRAVEL_PACE_PREFERENCE_OPTIONS.map((p) => (
                  <UnstyledButton
                    key={p.id}
                    onClick={() =>
                      update({
                        travelPace:
                          trip.travelPace === p.value ? null : (p.value as TravelPace),
                      })
                    }
                    style={trip.travelPace === p.value ? PILL_SELECTED : PILL_BASE}
                  >
                    {p.label}
                  </UnstyledButton>
                ))}
              </Box>
            </Stack>

            <Stack gap={4}>
              <Text size="xs" c="dimmed">
                Budget Mindset
              </Text>
              <Box style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {BUDGET_MINDSET_PREFERENCE_OPTIONS.map((b) => (
                  <UnstyledButton
                    key={b.id}
                    onClick={() =>
                      update({
                        budgetMindset:
                          trip.budgetMindset === b.value ? null : (b.value as BudgetMindset),
                      })
                    }
                    style={trip.budgetMindset === b.value ? PILL_SELECTED : PILL_BASE}
                  >
                    {b.label}
                  </UnstyledButton>
                ))}
              </Box>
            </Stack>

            <Stack gap={4}>
              <Text size="xs" c="dimmed">
                Primary travel goal
              </Text>
              <Box style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {PRIMARY_GOAL_PREFERENCE_OPTIONS.map((i) => (
                  <UnstyledButton
                    key={i.id}
                    onClick={() => dispatch(togglePrimaryGoal(i.value as PrimaryGoal))}
                    style={
                      trip.primaryGoals.includes(i.value as PrimaryGoal)
                        ? PILL_SELECTED
                        : PILL_BASE
                    }
                  >
                    {i.label}
                  </UnstyledButton>
                ))}
              </Box>
            </Stack>
          </Stack>
        </Paper>

        <Stack gap="xs">
          <Button
            size="md"
            fullWidth
            tt="none"
            disabled={!canSubmit || totalPax > MAX_PAX || isGuestAwaitingChatConfig}
            onClick={startPlanning}
            leftSection={isGuestAwaitingChatConfig ? <Loader size={16} color="white" /> : undefined}
          >
            Start planning
          </Button>
          <Button
            size="md"
            variant="subtle"
            fullWidth
            tt="none"
            c="dimmed"
            disabled={isGuestAwaitingChatConfig}
            onClick={continueToChat}
            leftSection={isGuestAwaitingChatConfig ? <Loader size={16} /> : undefined}
          >
            Continue straight to chat
          </Button>
        </Stack>
      </Stack>
    </OnboardingLayout>
  );
}

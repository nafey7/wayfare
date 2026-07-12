import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Anchor, Box, Button, Group, Loader, Paper, Stack, Text } from '@mantine/core';
import { useDetectLocationQuery } from '@/api/locationApi';
import { useAppDispatch } from '@/store';
import {
  confirmLocation,
  skipLocation,
} from '@/store/slices/onboardingSlice';
import type { DetectedLocation } from '@/types/onboarding';
import { ROUTES } from '@/features/routing/constants';
import { findCountryByCode } from '@/features/onboarding/locationData';
import { OnboardingLayout } from '@/features/onboarding/components/OnboardingLayout';
import {
  CitySearchAutocomplete,
  type CitySearchOption,
} from '@/features/onboarding/components/CitySearchAutocomplete';
import { draftLocationToCityOption } from '@/features/onboarding/openMeteoGeocoding';

function flagEmoji(countryCode: string): string {
  if (!countryCode || countryCode.length !== 2) return '';
  return countryCode
    .toUpperCase()
    .split('')
    .map((c) => String.fromCodePoint(0x1f1a5 + c.charCodeAt(0)))
    .join('');
}

type Mode = 'detecting' | 'detected' | 'editing' | 'failed';

const EMPTY_LOCATION: DetectedLocation = {
  country: '',
  countryCode: '',
  city: '',
  iata: '',
  currency: '',
  currencySymbol: '',
};

function currencyFromCountryCode(code: string): Pick<DetectedLocation, 'currency' | 'currencySymbol'> {
  const c = findCountryByCode(code);
  if (!c) return { currency: '', currencySymbol: '' };
  return { currency: c.currency, currencySymbol: c.currencySymbol };
}

/** Fill currency from our catalog when we have a country code (no user-facing currency field). */
function withDerivedCurrency(d: DetectedLocation): DetectedLocation {
  return { ...d, ...currencyFromCountryCode(d.countryCode) };
}

export function OnboardingScreen2() {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();

  const { data, isLoading, isError } = useDetectLocationQuery();

  const [mode, setMode] = useState<Mode>('detecting');
  const [draft, setDraft] = useState<DetectedLocation>(EMPTY_LOCATION);

  useEffect(() => {
    if (isLoading) {
      setMode('detecting');
      return;
    }
    if (isError || !data) {
      setMode('failed');
      return;
    }
    setMode('detected');
    setDraft(data);
  }, [isLoading, isError, data]);

  const locationOption = useMemo(
    () => draftLocationToCityOption(draft),
    [draft]
  );

  function onLocationChange(next: CitySearchOption | null) {
    if (!next) {
      setDraft(EMPTY_LOCATION);
      return;
    }
    if (next.cityName && next.countryName && next.countryCode) {
      setDraft({
        country: next.countryName,
        countryCode: next.countryCode,
        city: next.cityName,
        iata: '',
        ...currencyFromCountryCode(next.countryCode),
      });
    }
  }

  function handleSkip() {
    dispatch(skipLocation());
    navigate(ROUTES.ONBOARDING_TRIP);
  }

  function confirmLocationAndProceed() {
    if (!draft.country || !draft.city || !draft.countryCode) return;
    dispatch(confirmLocation(withDerivedCurrency(draft)));
    navigate(ROUTES.ONBOARDING_TRIP);
  }

  const manualFormValid = !!draft.country && !!draft.city && !!draft.countryCode;

  return (
    <OnboardingLayout
      step={2}
      title="Where are you based?"
      subtitle="We use this to suggest flights from a nearby airport and personalize your trip"
    >
      <Stack gap="md">
        {mode === 'detecting' && (
          <Paper withBorder p="lg">
            <Group justify="center" align="center" gap="md">
              <Loader size={18} />
              <Text c="dimmed">Detecting your location…</Text>
            </Group>
          </Paper>
        )}

        {mode === 'detected' && (
          <Paper withBorder p="md">
            <Stack gap={4}>
              <Text size="sm" c="dimmed" fw={500}>
                We detected:
              </Text>
              <Text size="lg" fw={600}>
                {flagEmoji(draft.countryCode)} {draft.city} · {draft.country}
              </Text>
              <Box>
                <Anchor
                  component="button"
                  type="button"
                  size="sm"
                  onClick={() => setMode('editing')}
                >
                  Change
                </Anchor>
              </Box>
            </Stack>
          </Paper>
        )}

        {(mode === 'editing' || mode === 'failed') && (
          <Paper withBorder p="md">
            <Stack gap="md">
              {mode === 'failed' && (
                <Text size="sm" c="dimmed">
                  We couldn't detect your location. Search for your home city below.
                </Text>
              )}
              <CitySearchAutocomplete
                label="Home city"
                placeholder="Start typing a city"
                value={locationOption}
                onChange={onLocationChange}
              />
            </Stack>
          </Paper>
        )}

        <Stack gap="xs">
          {mode === 'detected' && (
            <Button size="md" fullWidth tt="none" onClick={confirmLocationAndProceed}>
              That's right
            </Button>
          )}
          {(mode === 'editing' || mode === 'failed') && (
            <Button
              size="md"
              fullWidth
              tt="none"
              onClick={confirmLocationAndProceed}
              disabled={!manualFormValid}
            >
              Confirm
            </Button>
          )}
          <Button
            size="md"
            variant="subtle"
            fullWidth
            tt="none"
            c="dimmed"
            onClick={handleSkip}
            disabled={mode === 'detecting'}
          >
            Skip
          </Button>
        </Stack>
      </Stack>
    </OnboardingLayout>
  );
}

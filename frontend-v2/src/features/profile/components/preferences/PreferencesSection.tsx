import { Box, Stack, Text } from '@mantine/core';
import { useCallback, useEffect, useRef, useState } from 'react';
import { LANDING_TOKENS } from '@/features/landing/landingTokens';
import { TravelStylesSection } from './TravelStylesSection';
import { FlightsSection } from './FlightsSection';
import { HotelsSection } from './HotelsSection';
import { useUpdatePreferencesMutation } from '@/api/usersApi';
import { showErrorToastFromError } from '@/utils/toast';
import type {
  UserPreferences,
  FlightsPreferences,
  TravelStylePreferences,
  HotelsPreferences,
} from '@/types/profile';

/** Empty state when no document exists */
function emptyFlights(): FlightsPreferences {
  return {
    seatPreference: null,
    maxStops: null,
    preferredAirlines: [],
    departureWindow: ['00:00', '23:59'],
  };
}

function emptyTravelStyle(): TravelStylePreferences {
  return {
    travelPace: null,
    budgetMindset: null,
    accommodation: null,
    activityDensity: null,
    primaryGoals: [],
    gettingAround: [],
  };
}

function emptyHotels(): HotelsPreferences {
  return {
    bedType: null,
    roomType: null,
    amenities: [],
    hotelStyle: [],
    locationPreference: [],
    cancellation: [],
  };
}

export type PreferencesSection = 'travelStyle' | 'flights' | 'hotels';

export interface PreferencesSectionProps {
  preferences?: UserPreferences | null;
  documentExists: boolean;
  section: PreferencesSection;
}

const SECTION_TITLES: Record<PreferencesSection, string> = {
  travelStyle: 'Travel Preferences',
  flights: 'Flight Preferences',
  hotels: 'Hotel Preferences',
};

/**
 * Preferences section — renders only the sub-section matching `section`.
 * Only populates fields when documentExists and backend has data.
 */
export function PreferencesSection({
  preferences,
  documentExists,
  section,
}: PreferencesSectionProps) {
  const [updatePreferences] = useUpdatePreferencesMutation();

  const [flights, setFlights] = useState<FlightsPreferences>(() =>
    documentExists && preferences?.flights
      ? { ...emptyFlights(), ...preferences.flights }
      : emptyFlights()
  );
  const [travelStyle, setTravelStyle] = useState<TravelStylePreferences>(() =>
    documentExists && preferences?.travelStyle
      ? { ...emptyTravelStyle(), ...preferences.travelStyle }
      : emptyTravelStyle()
  );
  const [hotels, setHotels] = useState<HotelsPreferences>(() =>
    documentExists && preferences?.hotels
      ? { ...emptyHotels(), ...preferences.hotels }
      : emptyHotels()
  );

  useEffect(() => {
    if (documentExists && preferences) {
      setFlights((prev) =>
        preferences.flights
          ? { ...emptyFlights(), ...prev, ...preferences.flights }
          : prev
      );
      setTravelStyle((prev) =>
        preferences.travelStyle
          ? { ...emptyTravelStyle(), ...prev, ...preferences.travelStyle }
          : prev
      );
      setHotels((prev) =>
        preferences.hotels
          ? { ...emptyHotels(), ...prev, ...preferences.hotels }
          : prev
      );
    }
  }, [documentExists, preferences]);

  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const prefsRef = useRef({ flights, travelStyle, hotels });
  prefsRef.current = { flights, travelStyle, hotels };

  const performSave = useCallback(async () => {
    const { flights: f, travelStyle: t, hotels: h } = prefsRef.current;
    try {
      await updatePreferences({
        flights: {
          seatPreference: f.seatPreference,
          maxStops: f.maxStops,
          preferredAirlines: f.preferredAirlines,
          departureWindow: f.departureWindow,
        },
        travelStyle: {
          travelPace: t.travelPace,
          budgetMindset: t.budgetMindset,
          accommodation: t.accommodation,
          activityDensity: t.activityDensity,
          primaryGoals: t.primaryGoals,
          gettingAround: t.gettingAround,
        },
        hotels: {
          bedType: h.bedType,
          roomType: h.roomType,
          amenities: h.amenities,
          hotelStyle: h.hotelStyle,
          locationPreference: h.locationPreference,
          cancellation: h.cancellation,
        },
      }).unwrap();
    } catch (err) {
      showErrorToastFromError(err, 'Failed to save preferences. Please try again.');
    }
  }, [updatePreferences]);

  const scheduleSave = useCallback(() => {
    if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);
    saveTimeoutRef.current = setTimeout(() => {
      saveTimeoutRef.current = null;
      performSave();
    }, 300);
  }, [performSave]);

  useEffect(
    () => () => {
      if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);
    },
    []
  );

  const handleFlightsChange = useCallback(
    (newFlights: FlightsPreferences) => {
      setFlights(newFlights);
      scheduleSave();
    },
    [scheduleSave]
  );

  const handleTravelStyleChange = useCallback(
    (newTravelStyle: TravelStylePreferences) => {
      setTravelStyle(newTravelStyle);
      scheduleSave();
    },
    [scheduleSave]
  );

  const handleHotelsChange = useCallback(
    (newHotels: HotelsPreferences) => {
      setHotels(newHotels);
      scheduleSave();
    },
    [scheduleSave]
  );

  return (
    <Stack gap={0}>
      <Text
        style={{
          flex: 1,
          fontSize: 28,
          fontWeight: 700,
          lineHeight: 1.29,
          color: LANDING_TOKENS.textColor,
          margin: 0,
          display: 'block',
          fontFamily: LANDING_TOKENS.fontFamily.display,
          padding: '10px 16px',
        }}
      >
        {SECTION_TITLES[section]}
      </Text>

      <Box
        mt={16}
        style={{
          border: `1px solid ${LANDING_TOKENS.baseLighter}`,
          borderRadius: 25,
          padding: 16,
          display: 'flex',
          flexDirection: 'column',
          gap: 31,
          backgroundColor: 'white',
        }}
      >
        <Stack gap={31}>
          {section === 'travelStyle' && (
            <TravelStylesSection
              preferences={travelStyle}
              documentExists={documentExists}
              onChange={handleTravelStyleChange}
            />
          )}
          {section === 'flights' && (
            <FlightsSection
              preferences={flights}
              documentExists={documentExists}
              onChange={handleFlightsChange}
            />
          )}
          {section === 'hotels' && (
            <HotelsSection
              preferences={hotels}
              documentExists={documentExists}
              onChange={handleHotelsChange}
            />
          )}
        </Stack>
      </Box>
    </Stack>
  );
}

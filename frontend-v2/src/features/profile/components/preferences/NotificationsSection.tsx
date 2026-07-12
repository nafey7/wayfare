import { Alert, Box, Group, Stack, Switch, Text } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { useState } from 'react';
import { LANDING_TOKENS } from '@/features/landing/landingTokens';
import { SectionHeader } from '../shared';

function NotificationToggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <Group
      justify="space-between"
      align="center"
      style={{
        minHeight: 48,
        width: '100%',
        paddingTop: 10,
        paddingBottom: 10,
        paddingLeft: 16,
        paddingRight: 16,
        backgroundColor: 'white',
        borderRadius: 4,
      }}
    >
      <Text
        component="span"
        style={{
          fontSize: 16,
          fontWeight: 600,
          lineHeight: 1.25,
          letterSpacing: 0.1,
          color: LANDING_TOKENS.textColor,
          margin: 0,
          fontFamily: LANDING_TOKENS.fontFamily.display,
          flex: 1,
        }}
      >
        {label}
      </Text>
      <Switch
        checked={checked}
        onChange={(e) => onChange(e.currentTarget.checked)}
        size="md"
        color="brand.6"
      />
    </Group>
  );
}

interface NotificationGroup {
  id: string;
  title: string;
  items: { id: string; label: string }[];
}

const NOTIFICATION_GROUPS: NotificationGroup[] = [
  {
    id: 'priceAlerts',
    title: 'Price Alerts',
    items: [
      { id: 'flightPrice', label: 'Notify when flight price drops' },
      { id: 'hotelPrice', label: 'Notify when hotel price drops' },
      { id: 'flexibleDates', label: 'Notify when flexible dates show better deals' },
    ],
  },
  {
    id: 'tripUpdates',
    title: 'Trip Updates',
    items: [
      { id: 'gateChanges', label: 'Gate changes' },
      { id: 'flightDelays', label: 'Flight delays' },
      { id: 'checkInReminders', label: 'Check-in reminders' },
      { id: 'passportExpiry', label: 'Passport expiry reminders' },
    ],
  },
  {
    id: 'inspirationAlerts',
    title: 'Inspiration Alerts',
    items: [
      { id: 'trendingDestinations', label: 'New trending destinations' },
      { id: 'seasonalDeals', label: 'Seasonal deals' },
      { id: 'weekendGetaway', label: 'Weekend getaway ideas' },
      { id: 'personalizedRecs', label: 'Personalized recommendations' },
    ],
  },
  {
    id: 'communication',
    title: 'Communication Preferences',
    items: [
      { id: 'email', label: 'Email' },
      { id: 'sms', label: 'SMS' },
      { id: 'inAppOnly', label: 'In-app only' },
    ],
  },
];

const DEFAULT_ENABLED = new Set([
  'flightPrice',
  'hotelPrice',
  'flexibleDates',
  'gateChanges',
  'flightDelays',
  'checkInReminders',
  'seasonalDeals',
  'weekendGetaway',
  'email',
]);

/**
 * Notifications subsection — price alerts, trip updates, inspiration, communication.
 * NOTE: State is not persisted; backend integration coming soon.
 */
export function NotificationsSection() {
  const [enabled, setEnabled] = useState<Set<string>>(DEFAULT_ENABLED);
  const isMdUp = useMediaQuery('(min-width: 900px)') ?? false;

  return (
    <Stack gap="md">
      <Alert color="blue">
        Coming soon — notification preferences are not saved yet. Toggle changes are for preview only.
      </Alert>
      <Box
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          columnGap: 32,
          rowGap: 31,
          justifyContent: 'space-between',
        }}
      >
        {NOTIFICATION_GROUPS.map((group) => (
          <Box
            key={group.id}
            style={{
              minWidth: 0,
              flex: isMdUp ? '1 1 calc(50% - 32px)' : '1 1 100%',
            }}
          >
            <Stack gap="sm">
              <SectionHeader label={group.title} variant="main" px={2} />
              {group.items.map((item) => (
                <NotificationToggle
                  key={item.id}
                  label={item.label}
                  checked={enabled.has(item.id)}
                  onChange={(checked) =>
                    setEnabled((prev) => {
                      const next = new Set(prev);
                      if (checked) next.add(item.id);
                      else next.delete(item.id);
                      return next;
                    })
                  }
                />
              ))}
            </Stack>
          </Box>
        ))}
      </Box>
    </Stack>
  );
}

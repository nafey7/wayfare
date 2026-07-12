import type { Meta, StoryObj } from '@storybook/react-vite';
import { Avatar, Badge, Divider, Group, Indicator, Stack, Text, Title } from '@mantine/core';
import { Plane, BedDouble, Bell, Mail } from 'lucide-react';

/**
 * Chips and badges rendered with the Mantine theme. Mantine's Chip
 * primitive is for *toggle* state (filter chips); the static-label "chip"
 * pattern from MUI maps to Mantine `Badge`. The icon-overlay "badge" pattern
 * from MUI maps to Mantine `Indicator`.
 *
 * Interactive chip patterns (clickable / deletable / pill tabs) live in
 * application code: see `ChatChip` (#916) and `ContentPanelTabs` (M1 batch 2)
 * for `UnstyledButton` + manual styling references.
 */
function ChipsAndBadgesShowcase() {
  return (
    <Stack gap="lg" maw={600}>
      <Title order={4}>Chips & Badges</Title>

      <Stack gap="sm">
        <Text size="xs" c="dimmed" tt="uppercase">
          Badge — filled (≈ MUI chip filled)
        </Text>
        <Group gap="xs" wrap="wrap">
          <Badge color="gray">Default</Badge>
          <Badge>Primary</Badge>
          <Badge color="navy">Secondary</Badge>
          <Badge color="green">Success</Badge>
          <Badge color="red">Error</Badge>
          <Badge color="yellow">Warning</Badge>
          <Badge color="cyan">Info</Badge>
        </Group>
      </Stack>

      <Divider />

      <Stack gap="sm">
        <Text size="xs" c="dimmed" tt="uppercase">
          Badge — outline (≈ MUI chip outlined)
        </Text>
        <Group gap="xs" wrap="wrap">
          <Badge variant="outline" color="gray">
            Default
          </Badge>
          <Badge variant="outline">Primary</Badge>
          <Badge variant="outline" color="navy">
            Secondary
          </Badge>
          <Badge variant="outline" color="green">
            Success
          </Badge>
          <Badge variant="outline" color="red">
            Error
          </Badge>
        </Group>
      </Stack>

      <Divider />

      <Stack gap="sm">
        <Text size="xs" c="dimmed" tt="uppercase">
          Badge — light (subtle background, full saturation text)
        </Text>
        <Group gap="xs" wrap="wrap">
          <Badge variant="light">Primary</Badge>
          <Badge variant="light" color="navy">
            Secondary
          </Badge>
          <Badge variant="light" color="green">
            Success
          </Badge>
          <Badge variant="light" color="red">
            Error
          </Badge>
          <Badge variant="light" leftSection={<Plane size={12} />}>
            With Icon
          </Badge>
        </Group>
      </Stack>

      <Divider />

      <Stack gap="sm">
        <Text size="xs" c="dimmed" tt="uppercase">
          Badge — sizes
        </Text>
        <Group gap="xs" align="center">
          <Badge size="xs">XS</Badge>
          <Badge size="sm">SM</Badge>
          <Badge size="md">MD</Badge>
          <Badge size="lg">LG</Badge>
          <Badge size="xl">XL</Badge>
        </Group>
      </Stack>

      <Divider />

      <Stack gap="sm">
        <Text size="xs" c="dimmed" tt="uppercase">
          Use cases (flight & hotel curated chips)
        </Text>
        <Group gap="xs" wrap="wrap">
          <Badge size="sm" color="green">
            Cheapest
          </Badge>
          <Badge size="sm" color="cyan">
            Fastest
          </Badge>
          <Badge size="sm">Best Value</Badge>
          <Badge size="sm" variant="outline" color="gray">
            1 Stop
          </Badge>
          <Badge size="sm" variant="outline" color="gray">
            Direct
          </Badge>
          <Badge size="sm" leftSection={<Plane size={12} />}>
            Flight
          </Badge>
          <Badge size="sm" leftSection={<BedDouble size={12} />}>
            Hotel
          </Badge>
        </Group>
      </Stack>

      <Divider />

      <Stack gap="sm">
        <Text size="xs" c="dimmed" tt="uppercase">
          Indicator (≈ MUI Badge overlay on icons)
        </Text>
        <Group gap="lg" align="center">
          <Indicator inline label="4" size={18}>
            <Mail size={28} />
          </Indicator>
          <Indicator inline label="12" size={18} color="red">
            <Bell size={28} />
          </Indicator>
          <Indicator inline color="green" size={10} processing>
            <Mail size={28} />
          </Indicator>
          <Indicator inline label="99+" size={18} color="red">
            <Bell size={28} />
          </Indicator>
          <Indicator inline color="green" size={10} offset={4}>
            <Avatar size="md" color="brand">
              V
            </Avatar>
          </Indicator>
        </Group>
      </Stack>
    </Stack>
  );
}

const meta: Meta<typeof ChipsAndBadgesShowcase> = {
  title: 'Foundation/Chips & Badges',
  component: ChipsAndBadgesShowcase,
};

export default meta;
type Story = StoryObj<typeof ChipsAndBadgesShowcase>;

export const Default: Story = {};

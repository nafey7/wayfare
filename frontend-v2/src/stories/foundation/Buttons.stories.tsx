import type { Meta, StoryObj } from '@storybook/react-vite';
import { ActionIcon, Button, Divider, Group, Stack, Text, Title } from '@mantine/core';
import { Plane, Search } from 'lucide-react';

/**
 * Buttons rendered with the Mantine theme (src/theme/mantineTheme.ts).
 * Variants, colors, sizes are Mantine-native: filled / outline / subtle /
 * transparent / light, with brand color tokens (brand, navy, accent) plus
 * the standard semantic colors (red, green, etc.).
 *
 * For the legacy MUI button reference, see Foundation/MuiTheme (kept until
 * M6 #913 cleanup).
 */
function ButtonShowcase() {
  return (
    <Stack gap="lg" maw={600}>
      <Title order={4}>Buttons</Title>

      <Stack gap="sm">
        <Text size="xs" c="dimmed" tt="uppercase">
          Filled (≈ MUI contained)
        </Text>
        <Group gap="sm" wrap="wrap">
          <Button>Primary</Button>
          <Button color="navy">Secondary</Button>
          <Button color="green">Success</Button>
          <Button color="red">Error</Button>
          <Button disabled>Disabled</Button>
        </Group>
      </Stack>

      <Divider />

      <Stack gap="sm">
        <Text size="xs" c="dimmed" tt="uppercase">
          Outline (≈ MUI outlined)
        </Text>
        <Group gap="sm" wrap="wrap">
          <Button variant="outline">Primary</Button>
          <Button variant="outline" color="navy">
            Secondary
          </Button>
          <Button variant="outline" color="green">
            Success
          </Button>
          <Button variant="outline" color="red">
            Error
          </Button>
          <Button variant="outline" disabled>
            Disabled
          </Button>
        </Group>
      </Stack>

      <Divider />

      <Stack gap="sm">
        <Text size="xs" c="dimmed" tt="uppercase">
          Subtle (≈ MUI text)
        </Text>
        <Group gap="sm" wrap="wrap">
          <Button variant="subtle">Primary</Button>
          <Button variant="subtle" color="navy">
            Secondary
          </Button>
          <Button variant="subtle" disabled>
            Disabled
          </Button>
        </Group>
      </Stack>

      <Divider />

      <Stack gap="sm">
        <Text size="xs" c="dimmed" tt="uppercase">
          Sizes
        </Text>
        <Group gap="sm" align="center">
          <Button size="xs">XS</Button>
          <Button size="sm">SM (≈ MUI small)</Button>
          <Button size="md">MD (≈ MUI medium)</Button>
          <Button size="lg">LG (≈ MUI large)</Button>
          <Button size="xl">XL</Button>
        </Group>
      </Stack>

      <Divider />

      <Stack gap="sm">
        <Text size="xs" c="dimmed" tt="uppercase">
          With Icons
        </Text>
        <Group gap="sm" align="center">
          <Button leftSection={<Plane size={16} />}>Search Flights</Button>
          <Button variant="outline" rightSection={<Search size={16} />}>
            Search
          </Button>
          <ActionIcon variant="subtle" aria-label="Search flights" size="lg">
            <Plane size={18} />
          </ActionIcon>
        </Group>
      </Stack>
    </Stack>
  );
}

const meta: Meta<typeof ButtonShowcase> = {
  title: 'Foundation/Buttons',
  component: ButtonShowcase,
};

export default meta;
type Story = StoryObj<typeof ButtonShowcase>;

export const Default: Story = {};

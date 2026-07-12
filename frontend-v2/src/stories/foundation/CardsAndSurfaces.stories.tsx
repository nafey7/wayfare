import type { Meta, StoryObj } from '@storybook/react-vite';
import { Button, Card, Divider, Group, Paper, Stack, Text, Title } from '@mantine/core';

/**
 * Cards and surfaces rendered with the Mantine theme. Mantine's `Card` and
 * `Paper` are the closest equivalents to MUI's `Card`/`Paper`; the
 * `elevation` integer (0-24) maps to Mantine's `shadow` prop ("xs" through
 * "xl"). Both components share `radius`, `padding`, and `withBorder` props.
 */
function CardsAndSurfacesShowcase() {
  return (
    <Stack gap="lg" maw={700}>
      <Title order={4}>Cards & Surfaces</Title>

      <Stack gap="sm">
        <Text size="xs" c="dimmed" tt="uppercase">
          Cards
        </Text>
        <Group gap="sm" wrap="wrap" align="stretch">
          <Card w={300}>
            <Title order={6}>Basic Card</Title>
            <Text size="sm" c="dimmed" mt={4}>
              Cards rendered with Mantine theme defaults (radius=lg, shadow=sm,
              padding=lg).
            </Text>
          </Card>

          <Card w={300}>
            <Title order={6}>Card with Actions</Title>
            <Text size="sm" c="dimmed" mt={4}>
              Example of a card with action buttons.
            </Text>
            <Group gap="xs" mt="md">
              <Button size="xs" variant="subtle">
                View Details
              </Button>
              <Button size="xs" color="navy">
                Book Now
              </Button>
            </Group>
          </Card>
        </Group>
      </Stack>

      <Divider />

      <Stack gap="sm">
        <Text size="xs" c="dimmed" tt="uppercase">
          Paper — shadow scale (≈ MUI elevation)
        </Text>
        <Group gap="sm" wrap="wrap">
          {(['xs', 'sm', 'md', 'lg', 'xl'] as const).map((shadow) => (
            <Paper key={shadow} shadow={shadow} p="md" w={120} ta="center">
              <Text size="sm">shadow={shadow}</Text>
            </Paper>
          ))}
        </Group>
      </Stack>

      <Divider />

      <Stack gap="sm">
        <Text size="xs" c="dimmed" tt="uppercase">
          Paper variants
        </Text>
        <Group gap="sm">
          <Paper p="md" w={200}>
            <Text size="sm">Default (shadow=sm)</Text>
          </Paper>
          <Paper p="md" w={200} withBorder shadow="none">
            <Text size="sm">withBorder (≈ MUI outlined)</Text>
          </Paper>
          <Paper p="md" w={200} bg="gray.1">
            <Text size="sm">Tinted background</Text>
          </Paper>
        </Group>
      </Stack>
    </Stack>
  );
}

const meta: Meta<typeof CardsAndSurfacesShowcase> = {
  title: 'Foundation/Cards & Surfaces',
  component: CardsAndSurfacesShowcase,
};

export default meta;
type Story = StoryObj<typeof CardsAndSurfacesShowcase>;

export const Default: Story = {};

import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, within } from 'storybook/test';
import {
  Box,
  Button,
  Group,
  Stack,
  Text,
  Title,
  Badge,
  Card,
  Divider,
  Paper,
  TextInput,
  Chip,
  useMantineTheme,
} from '@mantine/core';
import { mantineTheme } from '@/theme/mantineTheme';

const brandColors  = mantineTheme.colors?.['brand']  ?? [];
const accentColors = mantineTheme.colors?.['accent'] ?? [];
const navyColors   = mantineTheme.colors?.['navy']   ?? [];

function ColorSwatch({ color, label }: { color: string; label: string }) {
  return (
    <Stack align="center" gap={4} w={80}>
      <Box w={64} h={64} style={{ borderRadius: 8, backgroundColor: color, border: '1px solid rgba(0,0,0,0.07)' }} />
      <Text size="xs" ta="center" lh={1.2}>{label}</Text>
      <Text size="xs" c="dimmed" ta="center" ff="monospace">{color}</Text>
    </Stack>
  );
}

function SurfaceSwatch({ color, label, desc }: { color: string; label: string; desc: string }) {
  return (
    <Stack gap={4} w={160}>
      <Box h={56} style={{ borderRadius: 8, backgroundColor: color, border: '1px solid rgba(0,0,0,0.07)' }} />
      <Text size="sm" fw={500}>{label}</Text>
      <Text size="xs" ff="monospace" c="dimmed">{color}</Text>
      <Text size="xs" c="dimmed">{desc}</Text>
    </Stack>
  );
}

function MantineThemeShowcase() {
  const theme = useMantineTheme();
  const other = theme.other as typeof mantineTheme.other;

  return (
    <Stack gap="xl" p="xl" maw={900}>
      <Title order={2}>Mantine Theme — Voya</Title>

      {/* Brand indigo */}
      <Stack gap="sm">
        <Title order={4}>Brand Indigo (primary identity)</Title>
        <Group gap="xs" wrap="wrap">
          {brandColors.map((shade, i) => (
            <ColorSwatch key={i} color={shade} label={`brand.${i}`} />
          ))}
        </Group>
      </Stack>

      <Divider />

      {/* Navy */}
      <Stack gap="sm">
        <Title order={4}>Navy — #2A2F5F (CTA buttons, dark surfaces)</Title>
        <Group gap="xs" wrap="wrap">
          {navyColors.map((shade, i) => (
            <ColorSwatch key={i} color={shade} label={`navy.${i}`} />
          ))}
        </Group>
      </Stack>

      <Divider />

      {/* Accent lime */}
      <Stack gap="sm">
        <Title order={4}>Accent Lime — #E7FBBC (highlights, badges, prices)</Title>
        <Group gap="xs" wrap="wrap">
          {accentColors.map((shade, i) => (
            <ColorSwatch key={i} color={shade} label={`accent.${i}`} />
          ))}
        </Group>
      </Stack>

      <Divider />

      {/* Surfaces */}
      <Stack gap="sm">
        <Title order={4}>Surfaces</Title>
        <Group gap="md" wrap="wrap">
          <SurfaceSwatch color={other?.surfacePage  ?? ''} label="Page"   desc="App background" />
          <SurfaceSwatch color={other?.surfaceCard  ?? ''} label="Card"   desc="Cards / modals" />
          <SurfaceSwatch color={other?.surfacePanel ?? ''} label="Panel"  desc="Sidebar / info panels" />
          <SurfaceSwatch color={other?.surfaceInput ?? ''} label="Input"  desc="Input fields" />
          <SurfaceSwatch color={other?.borderDefault ?? ''} label="Border" desc="Default border" />
        </Group>
      </Stack>

      <Divider />

      {/* Gradient */}
      <Stack gap="sm">
        <Title order={4}>Brand Gradient</Title>
        <Box
          h={80}
          style={{
            borderRadius: 12,
            background: other?.gradientBrand,
            display: 'flex',
            alignItems: 'center',
            paddingLeft: 24,
          }}
        >
          <Text c="white" fw={600} size="lg">Voya — Your perfect trip</Text>
        </Box>
      </Stack>

      <Divider />

      {/* Buttons */}
      <Stack gap="sm">
        <Title order={4}>Buttons</Title>
        <Text size="sm" c="dimmed">Navy = primary CTA &nbsp;·&nbsp; Brand = secondary action &nbsp;·&nbsp; Accent = highlight</Text>
        <Group gap="sm" wrap="wrap">
          <Button>Book now</Button>
          <Button color="brand">View flights</Button>
          <Button color="accent">Best value</Button>
          <Button variant="outline">Outline</Button>
          <Button variant="light" color="brand">Light</Button>
          <Button variant="subtle">Subtle</Button>
          <Button disabled>Disabled</Button>
        </Group>
        <Group gap="sm">
          <Button size="xs">XSmall</Button>
          <Button size="sm">Small</Button>
          <Button size="md">Medium</Button>
          <Button size="lg">Large</Button>
        </Group>
      </Stack>

      <Divider />

      {/* Typography */}
      <Stack gap="xs">
        <Title order={4}>Typography (Inter)</Title>
        <Title order={1}>Heading 1 — Inter 700</Title>
        <Title order={2}>Heading 2 — Inter 700</Title>
        <Title order={3}>Heading 3 — Inter 700</Title>
        <Title order={4}>Heading 4 — Inter 700</Title>
        <Text size="lg">Body large — Inter 400</Text>
        <Text size="md">Body medium — Inter 400</Text>
        <Text size="sm">Body small — Inter 400</Text>
        <Text size="xs" c="dimmed">Caption / dimmed</Text>
      </Stack>

      <Divider />

      {/* Badges + Chips */}
      <Stack gap="sm">
        <Title order={4}>Badges + Chips</Title>
        <Group gap="xs">
          <Badge color="accent" style={{ backgroundColor: other?.limeAccent, color: '#1a1a1a' }}>Best value</Badge>
          <Badge color="brand">Flight</Badge>
          <Badge color="navy">Confirmed</Badge>
          <Badge color="green">Direct</Badge>
          <Badge color="red">Cancelled</Badge>
          <Badge variant="outline" color="brand">1 Stop</Badge>
        </Group>
        <Group gap="xs">
          <Chip defaultChecked color="brand">Economy</Chip>
          <Chip color="brand">Business</Chip>
          <Chip color="navy">First class</Chip>
        </Group>
      </Stack>

      <Divider />

      {/* Inputs */}
      <Stack gap="sm" maw={400}>
        <Title order={4}>Inputs</Title>
        <TextInput label="From" placeholder="City or airport" />
        <TextInput label="To" placeholder="City or airport" />
        <TextInput label="Departure" placeholder="dd / mm / yyyy" />
      </Stack>

      <Divider />

      {/* Cards */}
      <Stack gap="sm">
        <Title order={4}>Cards</Title>
        <Group align="flex-start">
          <Card w={220}>
            <Group justify="space-between" mb="xs">
              <Badge color="brand">Flight</Badge>
              <Badge variant="outline" color="dimmed">Direct</Badge>
            </Group>
            <Text fw={700} size="lg">LHR → CDG</Text>
            <Text size="sm" c="dimmed">09:00 → 11:15 · 2h 15m</Text>
            <Divider my="sm" />
            <Group justify="space-between" align="center">
              <Text fw={700} size="xl" c="navy.7">£89</Text>
              <Button size="sm">Book</Button>
            </Group>
          </Card>

          <Card w={220}>
            <Badge
              mb="xs"
              style={{ backgroundColor: other?.limeAccent, color: '#1a1a1a' }}
            >
              Best value ⭐
            </Badge>
            <Text fw={700} size="lg">The Grand Paris</Text>
            <Text size="sm" c="dimmed">★ 4.8 · City centre</Text>
            <Text size="xs" c="dimmed" mt={4}>Free cancellation</Text>
            <Divider my="sm" />
            <Group justify="space-between" align="center">
              <Text fw={700} size="xl" c="navy.7">£145<Text span size="xs" c="dimmed">/night</Text></Text>
              <Button size="sm" color="brand" variant="light">Rooms</Button>
            </Group>
          </Card>

          <Paper w={220} p="lg" style={{ background: other?.gradientBrand }}>
            <Text c="white" size="xs" mb={4} style={{ opacity: 0.7 }}>YOUR TRIP</Text>
            <Text c="white" fw={700} size="lg">Tokyo · 7 days</Text>
            <Text c="white" size="sm" mt={4} style={{ opacity: 0.85 }}>3 flights · 2 hotels</Text>
            <Button
              mt="md"
              size="sm"
              fullWidth
              style={{ backgroundColor: other?.limeAccent, color: '#1a1a1a', border: 'none' }}
            >
              View itinerary
            </Button>
          </Paper>
        </Group>
      </Stack>

    </Stack>
  );
}

const meta: Meta<typeof MantineThemeShowcase> = {
  title: 'Foundation/MantineTheme',
  component: MantineThemeShowcase,
};

export default meta;
type Story = StoryObj<typeof MantineThemeShowcase>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // Each colour scale must render its hex values in the swatches — catches empty-scale regressions
    expect(canvas.getAllByText('#667eea').length).toBeGreaterThan(0); // brand.6
    expect(canvas.getAllByText('#2A2F5F').length).toBeGreaterThan(0); // navy.7
    expect(canvas.getAllByText('#e7fbbc').length).toBeGreaterThan(0); // accent.2
  },
};

import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, within } from 'storybook/test';
import { Box, Group, Stack, Text, Title } from '@mantine/core';
import { brandScale, accentScale, navyScale, surfaces } from '@/theme/tokens';

function ColorSwatch({ color, label }: { color: string; label: string }) {
  return (
    <Stack align="center" gap={4} w={80}>
      <Box
        w={64}
        h={64}
        style={{ borderRadius: 8, backgroundColor: color, border: '1px solid rgba(0,0,0,0.1)' }}
      />
      <Text size="xs" ta="center" lh={1.2}>
        {label}
      </Text>
      <Text size="xs" c="dimmed" ta="center" ff="monospace">
        {color}
      </Text>
    </Stack>
  );
}

function ColorGroup({
  title,
  colors,
}: {
  title: string;
  colors: { color: string; label: string }[];
}) {
  return (
    <Stack gap="xs" mb="lg">
      <Title order={6}>{title}</Title>
      <Group gap="sm" wrap="wrap">
        {colors.map((c) => (
          <ColorSwatch key={c.label} {...c} />
        ))}
      </Group>
    </Stack>
  );
}

function Colors() {
  return (
    <Stack gap="md">
      <Title order={4}>Voya Color Palette</Title>

      <ColorGroup
        title="Brand (Indigo)"
        colors={brandScale.map((color, i) => ({ color, label: String(i) }))}
      />

      <ColorGroup
        title="Accent (Lime)"
        colors={accentScale.map((color, i) => ({ color, label: String(i) }))}
      />

      <ColorGroup
        title="Navy (Buttons / dark surfaces)"
        colors={navyScale.map((color, i) => ({ color, label: String(i) }))}
      />

      <ColorGroup
        title="Surfaces & borders"
        colors={[
          { color: surfaces.surfacePage, label: 'Page' },
          { color: surfaces.surfaceCard, label: 'Card' },
          { color: surfaces.surfacePanel, label: 'Panel' },
          { color: surfaces.surfaceInput, label: 'Input' },
          { color: surfaces.borderDefault, label: 'Border default' },
          { color: surfaces.borderStrong, label: 'Border strong' },
          { color: surfaces.navyBlue, label: 'Navy CTA' },
          { color: surfaces.limeAccent, label: 'Lime accent' },
          { color: surfaces.indigoMain, label: 'Indigo main' },
        ]}
      />
    </Stack>
  );
}

const meta: Meta<typeof Colors> = {
  title: 'Foundation/Colors',
  component: Colors,
};

export default meta;
type Story = StoryObj<typeof Colors>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // Guard against accidentally-emptied scales: assert each scale's signature
    // hex appears in the rendered output. Mirrors the pattern used by
    // MantineTheme.stories.tsx.
    expect(canvas.getAllByText(brandScale[6]).length).toBeGreaterThan(0); // brand main
    expect(canvas.getAllByText(navyScale[7]).length).toBeGreaterThan(0); // navy CTA
    expect(canvas.getAllByText(accentScale[2]).length).toBeGreaterThan(0); // lime accent
    expect(canvas.getAllByText(surfaces.surfacePage).length).toBeGreaterThan(0);
  },
};

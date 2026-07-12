import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, within } from 'storybook/test';
import { Divider, Group, Stack, Text, Title } from '@mantine/core';
import { typography } from '@/theme/tokens';

function TypographyShowcase() {
  const headings = [
    { order: 1 as const, token: typography.h1 },
    { order: 2 as const, token: typography.h2 },
    { order: 3 as const, token: typography.h3 },
    { order: 4 as const, token: typography.h4 },
    { order: 5 as const, token: typography.h5 },
    { order: 6 as const, token: typography.h6 },
  ];

  return (
    <Stack gap="lg" maw={800}>
      <Title order={4}>Typography Scale</Title>
      <Text size="sm" c="dimmed">
        Font family: {typography.fontFamilyMantine} (Mantine surfaces)
      </Text>

      <Divider />

      <Stack gap="sm">
        <Text size="xs" c="dimmed" tt="uppercase">
          Headings (Mantine `Title order={'{1..6}'}`, sizes from `tokens.typography.h*`)
        </Text>
        {headings.map(({ order, token }) => (
          <Group key={order} align="baseline" gap="md">
            <Title order={order}>H{order} Heading</Title>
            <Text size="xs" c="dimmed">
              {token.fontSize} / lh {token.lineHeight}
            </Text>
          </Group>
        ))}
      </Stack>

      <Divider />

      <Stack gap="sm">
        <Text size="xs" c="dimmed" tt="uppercase">
          Body & UI Text (Mantine `Text size={'{xs|sm|md|lg|xl}'}`)
        </Text>

        <Stack gap={4}>
          <Text size="md">
            Text size="md" (≈ MUI body1) — used for main content text throughout
            the application. This is the Mantine default body size.
          </Text>
          <Text size="xs" c="dimmed">
            md
          </Text>
        </Stack>

        <Stack gap={4}>
          <Text size="sm">
            Text size="sm" (≈ MUI body2) — used for secondary content,
            descriptions, and supporting text.
          </Text>
          <Text size="xs" c="dimmed">
            sm
          </Text>
        </Stack>

        <Stack gap={4}>
          <Text size="xs">Text size="xs"</Text>
          <Text size="xs" c="dimmed">
            xs (caption / labels)
          </Text>
        </Stack>

        <Stack gap={4}>
          <Text size="xs" tt="uppercase" fw={600} c="dimmed">
            Overline-style label
          </Text>
          <Text size="xs" c="dimmed">
            xs + tt="uppercase" + fw=600 (no Mantine "overline" variant; use props)
          </Text>
        </Stack>
      </Stack>

      <Divider />

      <Stack gap={4}>
        <Text size="xs" c="dimmed" tt="uppercase">
          Text Colors (Mantine `c=""` prop)
        </Text>
        <Text>Default text (theme color-scheme aware)</Text>
        <Text c="dimmed">Dimmed (≈ MUI text.secondary)</Text>
        <Text c="brand">Brand color</Text>
        <Text c="red">Semantic red</Text>
      </Stack>
    </Stack>
  );
}

const meta: Meta<typeof TypographyShowcase> = {
  title: 'Foundation/Typography',
  component: TypographyShowcase,
};

export default meta;
type Story = StoryObj<typeof TypographyShowcase>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // All six heading rows should render so the showcase doesn't silently
    // regress to e.g. half the scale during a token rename.
    for (const order of [1, 2, 3, 4, 5, 6]) {
      expect(canvas.getByText(`H${order} Heading`)).toBeInTheDocument();
    }
  },
};

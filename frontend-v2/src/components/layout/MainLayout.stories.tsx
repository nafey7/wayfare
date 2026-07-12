import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, within } from 'storybook/test';
import { Box, Text, Title } from '@mantine/core';
import { ROUTES } from '@/features/routing';
import { MainLayout } from './MainLayout';

const meta: Meta<typeof MainLayout> = {
  title: 'Layout/MainLayout',
  component: MainLayout,
  parameters: {
    layout: 'fullscreen',
    initialEntries: [ROUTES.CHAT],
  },
};

export default meta;
type Story = StoryObj<typeof MainLayout>;

const pageContent = (
  <Box style={{ padding: 32 }}>
    <Title order={4}>Page Content</Title>
    <Text c="dimmed" mt={8}>
      This is the main content area inside MainLayout. UnifiedHeader renders above.
    </Text>
  </Box>
);

export const Default: Story = {
  args: { children: pageContent },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // Desktop: logo link is visible, children render below the header.
    expect(canvas.getByRole('link', { name: /voya home/i })).toBeInTheDocument();
    expect(canvas.getByText('Page Content')).toBeInTheDocument();
  },
};

export const Mobile: Story = {
  args: { children: pageContent },
  parameters: {
    viewport: { defaultViewport: 'mobile1' },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // On mobile the logo link is display:none and hamburger is gone;
    // the section nav and page content are present instead.
    expect(canvas.queryByRole('link', { name: /voya home/i })).toBeNull();
    expect(canvas.getByRole('navigation', { name: /section navigation/i })).toBeInTheDocument();
    expect(canvas.getByText('Page Content')).toBeInTheDocument();
  },
};

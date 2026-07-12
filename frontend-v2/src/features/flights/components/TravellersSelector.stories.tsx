import { useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { Box } from '@mantine/core';
import { expect, fn, within } from 'storybook/test';
import { TravellersSelector, type TravellersData } from './TravellersSelector';
import {
  mockTravellersDefault,
  mockTravellersWithChildren,
  mockTravellersMax,
} from '../__fixtures__/mockFlightSearchData';

const meta: Meta<typeof TravellersSelector> = {
  title: 'Flights/TravellersSelector',
  component: TravellersSelector,
  parameters: { layout: 'padded' },
  decorators: [
    (Story) => (
      <Box style={{ maxWidth: 400, border: '1px solid var(--mantine-color-gray-3)', borderRadius: 12 }}>
        <Story />
      </Box>
    ),
  ],
  args: {
    onChange: fn(),
    onClose: fn(),
  },
};

export default meta;
type Story = StoryObj<typeof TravellersSelector>;

/** Default: 1 adult, 0 children, 0 infants — all minimum values. */
export const Default: Story = {
  render: function Render({ onChange, onClose }) {
    const [value, setValue] = useState<TravellersData>(mockTravellersDefault);
    return (
      <TravellersSelector
        value={value}
        onChange={(data) => {
          setValue(data);
          onChange(data);
        }}
        onClose={onClose}
      />
    );
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Adults')).toBeInTheDocument();
    expect(canvas.getByText('12+ years')).toBeInTheDocument();
    expect(canvas.getByText('Children')).toBeInTheDocument();
    expect(canvas.getByText('2–11 years')).toBeInTheDocument();
    expect(canvas.getByText('Infants')).toBeInTheDocument();
    expect(canvas.getByText('Under 2 years')).toBeInTheDocument();
    expect(canvas.getByRole('button', { name: /apply/i })).toBeInTheDocument();
  },
};

/** 2 adults + 2 children — family travel scenario. */
export const WithChildren: Story = {
  render: function Render({ onChange, onClose }) {
    const [value, setValue] = useState<TravellersData>(mockTravellersWithChildren);
    return (
      <TravellersSelector
        value={value}
        onChange={(data) => {
          setValue(data);
          onChange(data);
        }}
        onClose={onClose}
      />
    );
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // 2 adults shown
    const counts = canvas.getAllByText('2');
    expect(counts.length).toBeGreaterThanOrEqual(2); // adults + children both show 2
    expect(canvas.getByText('Apply')).toBeInTheDocument();
  },
};

/** All counters at maximum — adults=9, children=8, infants=2. Increment buttons disabled. */
export const MaxSelected: Story = {
  render: function Render({ onChange, onClose }) {
    const [value, setValue] = useState<TravellersData>(mockTravellersMax);
    return (
      <TravellersSelector
        value={value}
        onChange={(data) => {
          setValue(data);
          onChange(data);
        }}
        onClose={onClose}
      />
    );
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('9')).toBeInTheDocument(); // adults at max
    expect(canvas.getByText('8')).toBeInTheDocument(); // children at max
    expect(canvas.getByText('2')).toBeInTheDocument(); // infants at max
    // At least the three increment buttons (adults, children, infants) are disabled
    const disabledButtons = canvas
      .getAllByRole('button')
      .filter((btn) => (btn as HTMLButtonElement).disabled);
    expect(disabledButtons.length).toBeGreaterThanOrEqual(3);
  },
};

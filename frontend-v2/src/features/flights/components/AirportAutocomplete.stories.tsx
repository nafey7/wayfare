import { useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { PlaneTakeoff } from 'lucide-react';
import { expect, fn, within } from 'storybook/test';
import { AirportAutocomplete, type AirportOption } from './AirportAutocomplete';

/**
 * AirportAutocomplete is a controlled input backed by RTK Query (useSearchAirportsQuery).
 * The query is skipped when the input is shorter than 2 characters, so Default and
 * WithLabel stories make no API calls. Stories with a pre-filled value of 2+ chars
 * trigger a query that returns empty results in Storybook (no backend), showing "No
 * airports found" in the dropdown when opened.
 */
const meta: Meta<typeof AirportAutocomplete> = {
  title: 'Flights/AirportAutocomplete',
  component: AirportAutocomplete,
  parameters: { layout: 'padded' },
  decorators: [
    (Story) => (
      <div style={{ maxWidth: 400 }}>
        <Story />
      </div>
    ),
  ],
  args: {
    onChange: fn(),
  },
};

export default meta;
type Story = StoryObj<typeof AirportAutocomplete>;

/** Empty input — placeholder visible, no API call (input < 2 chars). */
export const Default: Story = {
  render: function Render({ onChange }) {
    const [value, setValue] = useState('');
    return (
      <AirportAutocomplete
        value={value}
        onChange={(v: string, airport?: AirportOption) => {
          setValue(v);
          onChange(v, airport);
        }}
        placeholder="City or airport"
      />
    );
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const input = canvas.getByRole('combobox');
    expect(input).toBeInTheDocument();
    expect(input).not.toBeDisabled();
  },
};

/** Pre-filled with "AMS" — shows typed value, query fires but resolves empty in isolation. */
export const WithValue: Story = {
  render: function Render({ onChange }) {
    const [value, setValue] = useState('AMS');
    return (
      <AirportAutocomplete
        value={value}
        onChange={(v: string, airport?: AirportOption) => {
          setValue(v);
          onChange(v, airport);
        }}
        placeholder="City or airport"
      />
    );
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const input = canvas.getByRole('combobox');
    expect(input).toBeInTheDocument();
    expect((input as HTMLInputElement).value).toBe('AMS');
  },
};

/** With label and start adornment — matches the FlightSearchBarV2 "From" field appearance. */
export const WithLabel: Story = {
  render: function Render({ onChange }) {
    const [value, setValue] = useState('');
    return (
      <AirportAutocomplete
        value={value}
        onChange={(v: string, airport?: AirportOption) => {
          setValue(v);
          onChange(v, airport);
        }}
        label="From"
        placeholder="City or airport"
        startAdornment={<PlaneTakeoff size={18} color="var(--mantine-color-brand-2)" />}
      />
    );
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByLabelText('From')).toBeInTheDocument();
  },
};

/** Error state — helperText and red border signal invalid input. */
export const WithError: Story = {
  render: function Render({ onChange }) {
    const [value, setValue] = useState('');
    return (
      <AirportAutocomplete
        value={value}
        onChange={(v: string, airport?: AirportOption) => {
          setValue(v);
          onChange(v, airport);
        }}
        placeholder="City or airport"
        error
        helperText="Please select a valid airport"
      />
    );
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Please select a valid airport')).toBeInTheDocument();
  },
};

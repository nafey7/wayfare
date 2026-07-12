import type { Meta, StoryObj } from '@storybook/react-vite';
import { useState } from 'react';
import { Stack, Text } from '@mantine/core';
import { CountrySelect, type CountrySelectVariant } from './CountrySelect';

/**
 * CountrySelect renders the full ~250-country list. Storybook stories
 * here mount the entire dataset for both variants — the regression in
 * issue #975 (Mantine "Duplicate options" crash on shared dial codes
 * like +61) only surfaces when every country is present, not on a
 * trimmed sample. Keep these stories in `play` mode CI so a future
 * dataset regression fails the build.
 */

const meta: Meta<typeof CountrySelect> = {
  title: 'Shared/CountrySelect',
  component: CountrySelect,
};

export default meta;
type Story = StoryObj<typeof CountrySelect>;

function ControlledShowcase({ variant }: { variant: CountrySelectVariant }) {
  const [value, setValue] = useState('');
  return (
    <Stack maw={400} gap="sm">
      <CountrySelect value={value} onChange={setValue} variant={variant} label="Country" />
      <Text size="xs" c="dimmed">
        Emitted value: <code>{value || '(empty)'}</code>
      </Text>
    </Stack>
  );
}

export const Country: Story = {
  render: () => <ControlledShowcase variant="country" />,
};

export const Phone: Story = {
  name: 'Phone (regression: #975)',
  render: () => <ControlledShowcase variant="phone" />,
};

export const PhonePrefilled: Story = {
  name: 'Phone — prefilled with shared dial code',
  render: () => {
    function Inner() {
      // "61" is shared by AU, CC, CX. Mantine Select used to crash when the
      // option-value array contained duplicates; this story exists to make
      // sure the prefilled state still resolves cleanly.
      const [value, setValue] = useState('61');
      return (
        <Stack maw={400} gap="sm">
          <CountrySelect value={value} onChange={setValue} variant="phone" label="Phone country" />
          <Text size="xs" c="dimmed">
            Emitted value: <code>{value}</code>
          </Text>
        </Stack>
      );
    }
    return <Inner />;
  },
};

export const CountryWithoutPhoneCode: Story = {
  name: 'Country — phone code hidden in label',
  render: () => {
    function Inner() {
      const [value, setValue] = useState('US');
      return (
        <Stack maw={400} gap="sm">
          <CountrySelect
            value={value}
            onChange={setValue}
            variant="country"
            showPhoneCode={false}
            label="Nationality"
          />
          <Text size="xs" c="dimmed">
            Emitted value: <code>{value}</code>
          </Text>
        </Stack>
      );
    }
    return <Inner />;
  },
};

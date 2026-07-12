import type { Meta, StoryObj } from '@storybook/react-vite';
import { Divider, NumberInput, Select, Stack, Text, Textarea, TextInput, Title } from '@mantine/core';
import { Search } from 'lucide-react';

/**
 * Inputs rendered with the Mantine theme. TextInput is the Mantine
 * equivalent of MUI TextField; Select / NumberInput / Textarea are the
 * type-specific primitives that MUI rolls into TextField via props.
 */
function InputShowcase() {
  return (
    <Stack gap="lg" maw={500}>
      <Title order={4}>Inputs</Title>

      <Stack gap="sm">
        <Text size="xs" c="dimmed" tt="uppercase">
          Text inputs
        </Text>
        <TextInput label="Default" placeholder="Enter text..." />
        <TextInput label="Filled" defaultValue="Pre-filled value" />
        <TextInput label="With Description" description="This is helper text" />
        <TextInput label="Error" error="This field is required" />
        <TextInput label="Disabled" disabled defaultValue="Cannot edit" />
      </Stack>

      <Divider />

      <Stack gap="sm">
        <Text size="xs" c="dimmed" tt="uppercase">
          With adornments (Mantine `leftSection` / `rightSection`)
        </Text>
        <TextInput label="Search" leftSection={<Search size={16} />} placeholder="Search…" />
        <NumberInput label="Price" leftSection="$" hideControls />
      </Stack>

      <Divider />

      <Stack gap="sm">
        <Text size="xs" c="dimmed" tt="uppercase">
          Select
        </Text>
        <Select
          label="Select option"
          defaultValue="one"
          data={[
            { value: 'one', label: 'Option One' },
            { value: 'two', label: 'Option Two' },
            { value: 'three', label: 'Option Three' },
          ]}
        />
      </Stack>

      <Divider />

      <Stack gap="sm">
        <Text size="xs" c="dimmed" tt="uppercase">
          Multiline (Textarea)
        </Text>
        <Textarea label="Message" placeholder="Type your message..." minRows={3} autosize />
      </Stack>

      <Divider />

      <Stack gap="sm">
        <Text size="xs" c="dimmed" tt="uppercase">
          Sizes
        </Text>
        <TextInput label="XS" size="xs" />
        <TextInput label="SM (≈ MUI small)" size="sm" />
        <TextInput label="MD (≈ MUI medium, default)" size="md" />
        <TextInput label="LG" size="lg" />
      </Stack>
    </Stack>
  );
}

const meta: Meta<typeof InputShowcase> = {
  title: 'Foundation/Inputs',
  component: InputShowcase,
};

export default meta;
type Story = StoryObj<typeof InputShowcase>;

export const Default: Story = {};

import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, within } from 'storybook/test';
import { FareRules } from './FareRules';
import {
  mockFareRulesData,
  mockFareRulesRestrictive,
} from '../__fixtures__/mockFlightSearchData';

const meta: Meta<typeof FareRules> = {
  title: 'Flights/FareRules',
  component: FareRules,
  parameters: { layout: 'padded' },
  decorators: [
    (Story) => (
      <div style={{ maxWidth: 700 }}>
        <Story />
      </div>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof FareRules>;

/** Standard fare rules with cancellation policy. */
export const Default: Story = {
  args: {
    fareRules: mockFareRulesData,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText(/Fare Rules & Conditions/)).toBeInTheDocument();
    expect(canvas.getByText('Cancellation Policy')).toBeInTheDocument();
    expect(canvas.getByText(/CANCELLATIONS/)).toBeInTheDocument();
  },
};

/** Strict policy — no refunds, no changes, no name changes. */
export const Restrictive: Story = {
  args: {
    fareRules: mockFareRulesRestrictive,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText(/Fare Rules & Conditions/)).toBeInTheDocument();
    expect(canvas.getByText('Cancellation Policy')).toBeInTheDocument();
    expect(canvas.getByText(/No refunds are permitted/)).toBeInTheDocument();
  },
};

/** Loading state while fetching fare rules from the API. */
export const Loading: Story = {
  args: {
    fareRules: null,
    isLoading: true,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText(/Loading fare rules/)).toBeInTheDocument();
  },
};

/** API error — displays alert with the error message. */
export const Error: Story = {
  args: {
    fareRules: null,
    error: 'Unable to retrieve fare rules. Please try again.',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText(/Unable to retrieve fare rules/)).toBeInTheDocument();
  },
};

/** No fare rules returned from the API. */
export const Empty: Story = {
  args: {
    fareRules: null,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText(/Fare Rules & Conditions/)).toBeInTheDocument();
    expect(canvas.getByText(/No fare rules available/)).toBeInTheDocument();
  },
};

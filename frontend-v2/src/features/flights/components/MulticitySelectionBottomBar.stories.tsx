import type { Meta, StoryObj } from '@storybook/react-vite';
import { fn } from 'storybook/test';
import { PHONE_VIEWPORT } from '@/stories/helpers/viewports';
import { MulticitySelectionBottomBar } from './MulticitySelectionBottomBar';
import {
  mockAllLegs,
  mockSelectedLegsPartial,
  mockSelectedLegsComplete,
} from '../__fixtures__/mockFlightData';

const meta: Meta<typeof MulticitySelectionBottomBar> = {
  title: 'Flights/MulticitySelectionBottomBar',
  component: MulticitySelectionBottomBar,
  parameters: {
    layout: 'padded',
  },
  args: {
    onReviewBook: fn(),
  },
};

export default meta;
type Story = StoryObj<typeof MulticitySelectionBottomBar>;

/** No legs selected yet — button is disabled */
export const Default: Story = {
  args: {
    allLegs: mockAllLegs,
    selectedLegs: {},
  },
};

/** One of three legs selected — partial progress */
export const PartialSelection: Story = {
  args: {
    allLegs: mockAllLegs,
    selectedLegs: mockSelectedLegsPartial,
  },
};

/** All three legs selected — "Review and book" is enabled */
export const SelectionComplete: Story = {
  args: {
    allLegs: mockAllLegs,
    selectedLegs: mockSelectedLegsComplete,
  },
};

/** Partial selection at mobile viewport — stacked column layout */
export const MobilePartial: Story = {
  parameters: { viewport: PHONE_VIEWPORT },
  args: {
    allLegs: mockAllLegs,
    selectedLegs: mockSelectedLegsPartial,
  },
};

/** All legs selected at mobile viewport — full-width CTA */
export const MobileComplete: Story = {
  parameters: { viewport: PHONE_VIEWPORT },
  args: {
    allLegs: mockAllLegs,
    selectedLegs: mockSelectedLegsComplete,
  },
};

import type { Meta, StoryObj } from '@storybook/react-vite';
import { fn, within } from 'storybook/test';
import { MulticityRecommendationsPanel } from './MulticityRecommendationsPanel';
import { mockMulticityPayload } from '../__fixtures__/mockFlightData';
import type { MulticityChatPayloadNormalized } from '@/features/chat/utils/extractMulticityFlightSearchResults';
import { ChatContext } from '@/features/chat/context/ChatContext';
import { getStubChatContextValue } from '@/stories/helpers/stubChatContextValue';
import { expectFlightCardPopulated } from '@/stories/helpers/playAssertions';

/** Two-leg variant to verify the pill tab renders correctly for the minimal case. */
const twoLegPayload: MulticityChatPayloadNormalized = {
  ...mockMulticityPayload,
  legs: mockMulticityPayload.legs.slice(0, 2),
};

const meta: Meta<typeof MulticityRecommendationsPanel> = {
  title: 'Flights/MulticityRecommendationsPanel',
  component: MulticityRecommendationsPanel,
  parameters: {
    layout: 'padded',
    initialEntries: ['/flights/search'],
  },
  decorators: [
    (Story) => (
      <ChatContext.Provider value={getStubChatContextValue()}>
        <div style={{ maxWidth: 900, minHeight: 600, display: 'flex', flexDirection: 'column' }}>
          <Story />
        </div>
      </ChatContext.Provider>
    ),
  ],
  args: {
    onActiveLegIndexChange: fn(),
  },
};

export default meta;
type Story = StoryObj<typeof MulticityRecommendationsPanel>;

/** Three-leg Circle trip — first leg active */
export const Default: Story = {
  args: {
    payload: mockMulticityPayload,
    activeLegIndex: 0,
  },
  // Active leg 0: LHR → JFK
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectFlightCardPopulated(canvas, {
      outbound: { origin: 'LHR', destination: 'JFK' },
    });
  },
};

/** Three-leg Circle trip — second leg active */
export const SecondLegActive: Story = {
  args: {
    payload: mockMulticityPayload,
    activeLegIndex: 1,
  },
  // Active leg 1: JFK → CDG
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectFlightCardPopulated(canvas, {
      outbound: { origin: 'JFK', destination: 'CDG' },
    });
  },
};

/** Two-leg variant — minimal case */
export const TwoLegs: Story = {
  args: {
    payload: twoLegPayload,
    activeLegIndex: 0,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expectFlightCardPopulated(canvas, {
      outbound: { origin: 'LHR', destination: 'JFK' },
    });
  },
};

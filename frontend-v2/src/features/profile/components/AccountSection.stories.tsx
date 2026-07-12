import type { Meta, StoryObj } from '@storybook/react-vite';
import { Provider } from 'react-redux';
import { expect, within } from 'storybook/test';
import { AccountSection } from './AccountSection';
import { createStoryStore } from '@/stories/helpers/createStoryStore';
import { itinerariesApi } from '@/api/itinerariesApi';
import type { ProfileUser } from '@/types/profile';
import type { SavedItinerary } from '@/types/itineraries';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockUser: ProfileUser = {
  id: 'u-001',
  email: 'jane.doe@example.com',
  firstName: 'Jane',
  lastName: 'Doe',
  mobile: '+31 6 1234 5678',
};

const mockItinerary: SavedItinerary = {
  id: 'itin-01',
  structuredItinerary: {
    itineraryItems: [
      {
        day: 1,
        title: 'Arrival in Barcelona',
        description: 'Check in and explore the Gothic Quarter.',
        imageUrl: '',
      },
      {
        day: 2,
        title: 'Gaudí Day',
        description: 'Sagrada Família and Park Güell.',
        imageUrl: '',
      },
    ],
  },
  tripMeta: {
    destination: 'Barcelona, Spain',
    origin: 'Amsterdam',
    departureDate: '2026-05-10',
    returnDate: '2026-05-17',
    adults: 2,
  },
  createdAt: '2026-04-01T10:00:00Z',
  updatedAt: '2026-04-01T10:00:00Z',
};

// ---------------------------------------------------------------------------
// Store factory
// ---------------------------------------------------------------------------

function storeWithItineraries(itineraries: SavedItinerary[]) {
  const store = createStoryStore();
  store.dispatch(itinerariesApi.util.upsertQueryData('getItineraries', undefined, itineraries));
  return store;
}

// ---------------------------------------------------------------------------
// Meta
// ---------------------------------------------------------------------------

const meta: Meta<typeof AccountSection> = {
  title: 'Profile/AccountSection',
  component: AccountSection,
  parameters: { layout: 'padded' },
  decorators: [
    (Story) => (
        <Story />
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof AccountSection>;

// ---------------------------------------------------------------------------
// Stories
// ---------------------------------------------------------------------------

/** Default: populated user fields and one upcoming trip card. */
export const Default: Story = {
  decorators: [
    (Story) => (
      <Provider store={storeWithItineraries([mockItinerary])}>
        <Story />
      </Provider>
    ),
  ],
  args: {
    user: mockUser,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByDisplayValue('Jane')).toBeInTheDocument();
    expect(canvas.getByDisplayValue('Doe')).toBeInTheDocument();
    expect(canvas.getByText('Account')).toBeInTheDocument();
  },
};

/** No upcoming trips — section shows "No trips" state. */
export const NoTrips: Story = {
  decorators: [
    (Story) => (
      <Provider store={storeWithItineraries([])}>
        <Story />
      </Provider>
    ),
  ],
  args: {
    user: mockUser,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByDisplayValue('Jane')).toBeInTheDocument();
  },
};

/** New user with no name set — fields start empty. */
export const NewUser: Story = {
  decorators: [
    (Story) => (
      <Provider store={storeWithItineraries([])}>
        <Story />
      </Provider>
    ),
  ],
  args: {
    user: {
      id: 'u-002',
      email: 'new@example.com',
      firstName: null,
      lastName: null,
      mobile: null,
    },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText(/new@example.com/i)).toBeInTheDocument();
  },
};

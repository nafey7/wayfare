import type { Meta, StoryObj } from '@storybook/react-vite';
import { within, expect } from 'storybook/test';
import { useEffect } from 'react';
import { useAppDispatch } from '@/store';
import { setSearchFormParams } from '@/store/slices/hotelBookingSlice';
import { HotelSearchBarV2 } from './HotelSearchBarV2';
import { mockSingleRoom, MOCK_CHECKIN, MOCK_CHECKOUT } from '../__fixtures__/mockHotelData';

/** Injects search params into the Redux store from within the story (store is provided by global decorator). */
function WithDestinationProvider({
  children,
  destination,
}: {
  children: React.ReactNode;
  destination: string;
}) {
  const dispatch = useAppDispatch();
  useEffect(() => {
    dispatch(
      setSearchFormParams({
        destination,
        checkin: MOCK_CHECKIN,
        checkout: MOCK_CHECKOUT,
        rooms: mockSingleRoom,
        nationality: 'US',
      })
    );
  }, [dispatch, destination]);
  return <>{children}</>;
}

const meta: Meta<typeof HotelSearchBarV2> = {
  title: 'Hotels/HotelSearchBarV2',
  component: HotelSearchBarV2,
  parameters: { layout: 'padded' },
};

export default meta;
type Story = StoryObj<typeof HotelSearchBarV2>;

/** Default: no destination set; shows placeholder text. */
export const Default: Story = {
  decorators: [
    (Story) => (
      <WithDestinationProvider destination="">
        <Story />
      </WithDestinationProvider>
    ),
  ],
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Destination')).toBeInTheDocument();
  },
};

/** WithDestination: destination field pre-populated from Redux store. */
export const WithDestination: Story = {
  decorators: [
    (Story) => (
      <WithDestinationProvider destination="Barcelona">
        <Story />
      </WithDestinationProvider>
    ),
  ],
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Barcelona')).toBeInTheDocument();
  },
};

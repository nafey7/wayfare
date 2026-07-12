import type { Meta, StoryObj } from '@storybook/react-vite';
import { fn } from 'storybook/test';
import type { HotelGuestDetails } from '@/types/hotels';
import type { StoredPassenger } from '@/types/passengers';
import { GuestForm } from './GuestForm';

const slotAdult = { isChild: false, label: 'Adult 1' };
const guests: HotelGuestDetails[] = [
  {
    title: 'Mr',
    firstName: '',
    lastName: '',
    roomNumber: 1,
    isChild: false,
  },
];

const savedPassengers: StoredPassenger[] = [
  {
    id: 'sp-1',
    userId: 'u',
    title: 'Ms',
    firstName: 'Jamie',
    lastName: 'Rivera',
    dateOfBirth: '1992-06-15',
    nationality: 'US',
    email: null,
    phone: null,
    passportNumber: null,
    passportExpiry: null,
    passportCountry: null,
    frequentFlyerNumber: null,
    type: 'adult',
    createdAt: '',
    updatedAt: '',
  },
];

const meta: Meta<typeof GuestForm> = {
  title: 'Hotels/GuestForm',
  component: GuestForm,
  args: {
    roomNumber: 1,
    globalSlotStartIndex: 0,
    savedPassengerByGuestIndex: { 0: 'sp-1' },
    onSavedPassengerModeChange: fn(),
    slots: [slotAdult],
    guests,
    onChange: fn(),
    touched: false,
    savedPassengers,
    onSelectSaved: fn(),
    onEditPassenger: fn(),
  },
};

export default meta;
type Story = StoryObj<typeof GuestForm>;

export const Default: Story = {};

export const ManualEntry: Story = {
  args: {
    savedPassengerByGuestIndex: { 0: 'manual' },
  },
};

export const NoSavedPassengers: Story = {
  args: {
    savedPassengers: [],
    savedPassengerByGuestIndex: {},
  },
};

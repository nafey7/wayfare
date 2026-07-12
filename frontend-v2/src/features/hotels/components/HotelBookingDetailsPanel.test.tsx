import type { ReactElement } from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { MantineProvider } from '@mantine/core';
import { mantineTheme } from '@/theme';
import { baseApi } from '@/api/baseApi';
import authReducer from '@/store/slices/authSlice';
import { HotelBookingDetailsPanel } from './HotelBookingDetailsPanel';

function makeTestStore() {
  return configureStore({
    reducer: {
      [baseApi.reducerPath]: baseApi.reducer,
      auth: authReducer,
    },
    middleware: (getDefaultMiddleware) => getDefaultMiddleware().concat(baseApi.middleware),
  });
}

const baseProps = {
  headlineCity: 'Barcelona',
  destinationTitle: 'Barcelona',
  stayDateLine: 'Jun 1–5 • 4 nights',
  hotelImageUrls: [],
  hotelName: 'Test Hotel',
  addressLine: 'Somewhere',
  nightsAdultsLine: '4 nights・2 adults',
  roomTypeName: 'Deluxe',
  reservationCode: 'VOYA-TEST',
  guests: [{ roleLabel: 'Adult 1', fullName: 'Jane Doe' }],
  paymentMethodLabel: 'Card',
  paymentTimestamp: '',
  paymentAmountFormatted: 'USD 100.00',
  nextStepsItems: [{ id: 'a', text: 'Step one' }],
};

function renderPanel(ui: ReactElement) {
  const store = makeTestStore();
  return render(
    <Provider store={store}>
      <MemoryRouter>
        <MantineProvider theme={mantineTheme} env="test">{ui}</MantineProvider>
      </MemoryRouter>
    </Provider>,
  );
}

describe('HotelBookingDetailsPanel', () => {
  it('renders headline and reservation code', () => {
    renderPanel(<HotelBookingDetailsPanel {...baseProps} />);
    expect(screen.getByText(/You're booked!/)).toBeInTheDocument();
    expect(screen.getByText('VOYA-TEST')).toBeInTheDocument();
  });

  it('hides Go to hotel website when no URL and no handler', () => {
    renderPanel(<HotelBookingDetailsPanel {...baseProps} />);
    expect(screen.queryByRole('button', { name: /Go to hotel website/i })).not.toBeInTheDocument();
  });

  it('shows Go to hotel website when URL is provided', () => {
    renderPanel(<HotelBookingDetailsPanel {...baseProps} hotelWebsiteUrl="https://hotel.example" />);
    const link = screen.getByRole('link', { name: /Go to hotel website/i });
    expect(link).toHaveAttribute('href', 'https://hotel.example');
  });
});

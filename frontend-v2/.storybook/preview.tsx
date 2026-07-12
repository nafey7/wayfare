import React from 'react';
// Mantine styles must be imported before app CSS to keep resets predictable.
import '@mantine/core/styles.css';
import '@mantine/dates/styles.css';
import type { Preview } from '@storybook/react-vite';
import { configureStore } from '@reduxjs/toolkit';
import { baseApi } from '../src/api/baseApi';
import { strapiApi } from '../src/api/strapiApi';
import authReducer from '../src/store/slices/authSlice';
import chatReducer from '../src/store/slices/chatSlice';
import uiReducer from '../src/store/slices/uiSlice';
import flightBookingReducer from '../src/store/slices/flightBookingSlice';
import hotelBookingReducer from '../src/store/slices/hotelBookingSlice';
import { StorybookProviders } from '../src/providers/AppProviders';

/** Creates a fresh Redux store per story to prevent state leaking between stories. */
function createStoryStore() {
  return configureStore({
    reducer: {
      [baseApi.reducerPath]: baseApi.reducer,
      [strapiApi.reducerPath]: strapiApi.reducer,
      auth: authReducer,
      chat: chatReducer,
      ui: uiReducer,
      flightBooking: flightBookingReducer,
      hotelBooking: hotelBookingReducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware({
        serializableCheck: {
          ignoredActions: ['persist/PERSIST', 'persist/REHYDRATE'],
        },
      }).concat(baseApi.middleware, strapiApi.middleware),
  });
}

const preview: Preview = {
  decorators: [
    // Single AppProviders wrapper (MUI outer → Mantine inner → DatesProvider → MUI X → Chat).
    // Ad-hoc providers must NOT be added here — add to src/providers/AppProviders.tsx instead.
    // Stories that need a specific initial route set `parameters.initialEntries`.
    (Story, context) => {
      const store = createStoryStore();
      const initialEntries: string[] = (context.parameters.initialEntries as string[]) ?? ['/'];
      return (
        <StorybookProviders store={store} initialEntries={initialEntries}>
          <Story />
        </StorybookProviders>
      );
    },
  ],
  parameters: {
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    a11y: {
      // 'todo' = run checks and show violations in the panel, but don't fail the test.
      // 'error' would fail CI on any violation — use that once color-contrast and aria issues are resolved.
      // Note: 'warn' is not a valid value in @storybook/addon-a11y v10; it falls through to 'error'.
      test: 'todo',
    },
    options: {
      // Sidebar order: design system first, then active features; Archived last.
      storySort: {
        order: [
          'Foundation',
          'Navigation',
          'Chat',
          'Flights',
          'Hotels',
          'Itinerary',
          'Marketing',
          'Layout',
          '*',
          'Archived',
        ],
      },
    },
  },
};

export default preview;

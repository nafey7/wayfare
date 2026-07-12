import React from 'react';
import { Provider as ReduxProvider } from 'react-redux';
import type { EnhancedStore } from '@reduxjs/toolkit';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { ThemeProvider, CssBaseline } from '@mui/material';
import { LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { MantineProvider } from '@mantine/core';
import { DatesProvider } from '@mantine/dates';
import { store as appStore } from '@/store';
import { muiTheme, mantineTheme } from '@/theme';
import { ChatProvider } from '@/features/chat';
import { ScrollToTop } from '@/components/layout';
import { configureDayjs, dayjsLocale, firstDayOfWeek, weekendDays } from './dayjsLocale';

// Configure dayjs plugins and locale once at module load time.
configureDayjs();

interface AppProvidersProps {
  children: React.ReactNode;
  /** Override Redux store — used by Storybook to inject a fresh per-story store. */
  store?: EnhancedStore;
  /** Set to false to skip BrowserRouter (Storybook stories add their own router). */
  includeRouter?: boolean;
}

/**
 * Single provider tree for both the app (main.tsx) and Storybook (preview.tsx).
 * Provider order: Redux → GoogleOAuth → BrowserRouter? → MUI → Mantine → DatesProvider → MUI X → Chat
 * Any new provider must be added here only.
 */
export function AppProviders({
  children,
  store = appStore,
  includeRouter = true,
}: AppProvidersProps) {
  const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';

  const inner = (
    <ThemeProvider theme={muiTheme}>
      <MantineProvider theme={mantineTheme} defaultColorScheme="light">
        <DatesProvider
          settings={{
            locale: dayjsLocale,
            firstDayOfWeek,
            weekendDays: [...weekendDays],
          }}
        >
          <LocalizationProvider dateAdapter={AdapterDateFns}>
            <CssBaseline />
            <ChatProvider>{children}</ChatProvider>
          </LocalizationProvider>
        </DatesProvider>
      </MantineProvider>
    </ThemeProvider>
  );

  return (
    <ReduxProvider store={store}>
      <GoogleOAuthProvider clientId={googleClientId}>
        {includeRouter ? <BrowserRouter><ScrollToTop />{inner}</BrowserRouter> : inner}
      </GoogleOAuthProvider>
    </ReduxProvider>
  );
}

/**
 * Variant used by Storybook: uses MemoryRouter so ChatProvider's useLocation() works
 * without a real browser history. Stories that need a specific initial URL pass
 * `initialEntries` via `parameters.initialEntries` in their meta; the global
 * decorator forwards it here.
 */
export function StorybookProviders({
  children,
  store,
  initialEntries = ['/'],
}: Omit<AppProvidersProps, 'includeRouter'> & { initialEntries?: string[] }) {
  return (
    <MemoryRouter initialEntries={initialEntries}>
      <AppProviders store={store} includeRouter={false}>
        {children}
      </AppProviders>
    </MemoryRouter>
  );
}

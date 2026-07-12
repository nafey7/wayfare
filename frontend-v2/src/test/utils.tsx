import { render as rtlRender, RenderOptions } from '@testing-library/react';
import { MantineProvider } from '@mantine/core';
import { ThemeProvider as MuiThemeProvider } from '@mui/material/styles';
import { mantineTheme, muiTheme } from '@/theme';

/**
 * Hybrid Mantine + MUI provider wrapper for tests. While the codebase still has
 * MUI surfaces (intentional hybrid + a few un-migrated tests), tests that render
 * any Mantine component need the MantineProvider in the tree.
 */
function AllTheProviders({ children }: { children: React.ReactNode }) {
  return (
    <MantineProvider theme={mantineTheme} env="test">
      <MuiThemeProvider theme={muiTheme}>{children}</MuiThemeProvider>
    </MantineProvider>
  );
}

function render(
  ui: React.ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) {
  return rtlRender(ui, {
    wrapper: AllTheProviders,
    ...options,
  });
}

export * from '@testing-library/react';
export { userEvent } from '@testing-library/user-event';
export { render };

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { useTheme } from '@mui/material';
import { useMantineTheme } from '@mantine/core';

// Mock heavy/icon-laden transitive deps to avoid EMFILE (too many open files) in test env.
vi.mock('@/features/chat', () => ({
  ChatProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

import { StorybookProviders } from '../AppProviders';

function ThemeProbe() {
  const muiTheme = useTheme();
  const mantineTheme = useMantineTheme();
  return (
    <div>
      <span data-testid="mui-primary">{muiTheme.palette.primary.main}</span>
      <span data-testid="mantine-primary">{mantineTheme.primaryColor}</span>
    </div>
  );
}

describe('AppProviders', () => {
  it('provides both MUI and Mantine theme contexts to children', () => {
    render(
      <StorybookProviders>
        <ThemeProbe />
      </StorybookProviders>
    );

    // MUI theme context resolves with production primary colour
    expect(screen.getByTestId('mui-primary').textContent).toBe('#BFC6F4');
    // Mantine theme context resolves with the configured primary color
    expect(screen.getByTestId('mantine-primary').textContent).toBe('navy');
  });

  it('renders children exactly once (no duplicate providers)', () => {
    const renderSpy = vi.fn();
    function Sentinel() {
      renderSpy();
      return <span data-testid="sentinel">ok</span>;
    }
    render(
      <StorybookProviders>
        <Sentinel />
      </StorybookProviders>
    );
    expect(screen.getByTestId('sentinel')).toBeInTheDocument();
    expect(renderSpy).toHaveBeenCalledTimes(1);
  });
});

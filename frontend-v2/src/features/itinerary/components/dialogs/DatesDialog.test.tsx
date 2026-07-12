import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MantineProvider } from '@mantine/core';

import { DatesDialog } from './DatesDialog';

function renderDialog(mdUp: boolean) {
  render(
    <MantineProvider env="test">
      <DatesDialog open onClose={vi.fn()} mdUp={mdUp} />
    </MantineProvider>
  );
}

describe('DatesDialog', () => {
  it('renders a single month layout below the md breakpoint', () => {
    renderDialog(false);
    expect(screen.getAllByTestId('dates-dialog-calendar')).toHaveLength(1);
  });

  it('renders two months side by side at the md breakpoint and up', () => {
    renderDialog(true);
    expect(screen.getAllByTestId('dates-dialog-calendar')).toHaveLength(2);
  });
});

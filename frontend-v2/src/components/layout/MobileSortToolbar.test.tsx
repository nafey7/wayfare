import type { ReactElement } from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';
import { mantineTheme } from '@/theme';
import { MobileSortToolbar } from './MobileSortToolbar';

vi.mock('lucide-react', () => ({
  Filter: () => null,
  ArrowUpDown: () => null,
}));

function renderToolbar(ui: ReactElement) {
  return render(<MantineProvider theme={mantineTheme}>{ui}</MantineProvider>);
}

describe('MobileSortToolbar', () => {
  it('sortVariant=value: choosing a menu item calls onSortChange with that value', async () => {
    const user = userEvent.setup();
    const onSortChange = vi.fn();
    const primaryOnClick = vi.fn();

    renderToolbar(
      <MobileSortToolbar
        sortVariant="value"
        primaryButton={{ label: 'Filters', onClick: primaryOnClick }}
        menuItems={[
          { value: 'price', label: 'Price' },
          { value: 'duration', label: 'Duration' },
        ]}
        selectedSort="price"
        onSortChange={onSortChange}
      />,
    );

    await user.click(screen.getByRole('button', { name: /^sort$/i }));
    await user.click(await screen.findByRole('menuitem', { name: /^duration$/i }));

    expect(onSortChange).toHaveBeenCalledTimes(1);
    expect(onSortChange).toHaveBeenCalledWith('duration');
    expect(primaryOnClick).not.toHaveBeenCalled();
  });

  it('sortVariant=custom: choosing a menu item runs that item onClick', async () => {
    const user = userEvent.setup();
    const onA = vi.fn();
    const onB = vi.fn();

    renderToolbar(
      <MobileSortToolbar
        sortVariant="custom"
        primaryButton={{ label: 'Filters', onClick: vi.fn() }}
        menuItems={[
          { value: 'a', label: 'Option A', selected: true, onClick: onA },
          { value: 'b', label: 'Option B', selected: false, onClick: onB },
        ]}
      />,
    );

    await user.click(screen.getByRole('button', { name: /^sort$/i }));
    await user.click(await screen.findByRole('menuitem', { name: /^option b$/i }));

    expect(onB).toHaveBeenCalledTimes(1);
    expect(onA).not.toHaveBeenCalled();
  });
});

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';

import { ItineraryHotelBookingsList } from './ItineraryHotelBookingsList';

function renderWithProviders(ui: React.ReactElement) {
  return render(<MantineProvider env="test">{ui}</MantineProvider>);
}

describe('ItineraryHotelBookingsList', () => {
  it('calls onSelectReference with the clicked ref', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();

    renderWithProviders(
      <ItineraryHotelBookingsList
        itineraryId="it-1"
        items={[
          { voyaReference: 'H-1' },
          { voyaReference: 'H-2' },
        ]}
        onSelectReference={onSelect}
      />,
    );

    await user.click(screen.getByRole('button', { name: /open hotel booking H-1/i }));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith('H-1');
  });
});

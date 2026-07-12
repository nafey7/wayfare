import { describe, it, expect, beforeAll, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Provider } from 'react-redux';
import { MantineProvider } from '@mantine/core';
import { makeTestStore } from '@/store';
import { ItineraryDetailsComponent } from './ItineraryDetailsComponent';
import type { ItineraryItem } from './ItineraryDetailsComponent';

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <MantineProvider env="test">
      <Provider store={makeTestStore()}>{ui}</Provider>
    </MantineProvider>,
  );
}

const mockItems: ItineraryItem[] = [
  {
    day: 1,
    date: 'THU 15 MAY',
    title: 'Barcelona City',
    description: 'Explore the Gothic Quarter',
    imageUrl: '',
    expandedContent: {
      activities: [
        {
          id: 'act-1',
          location: 'Sagrada Familia',
          description: 'Iconic basilica by Gaudí',
          duration: '2 hours',
          rating: 4.8,
        },
        {
          id: 'act-2',
          location: 'Park Güell',
          description: 'Modernist garden complex',
          duration: '1.5 hours',
        },
      ],
      travelBars: [],
    },
  },
];

describe('ItineraryDetailsComponent — drill-down', () => {
  it('clicking an activity in the expanded timeline swaps to stop detail', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ItineraryDetailsComponent itineraryItems={mockItems} />);

    await user.click(screen.getByRole('button', { name: 'Expand day' }));

    expect(screen.getByText('Sagrada Familia')).toBeInTheDocument();
    expect(screen.getByText('Park Güell')).toBeInTheDocument();

    await user.click(screen.getByText('Sagrada Familia'));

    expect(screen.getByTestId('itinerary-stop-detail')).toBeInTheDocument();
    expect(screen.queryByText('Park Güell')).not.toBeInTheDocument();
  });

  it('back button in stop detail returns to timeline', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ItineraryDetailsComponent itineraryItems={mockItems} />);

    await user.click(screen.getByRole('button', { name: 'Expand day' }));
    await user.click(screen.getByText('Sagrada Familia'));

    expect(screen.getByTestId('itinerary-stop-detail')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /^Day 1$/ }));

    expect(screen.queryByTestId('itinerary-stop-detail')).not.toBeInTheDocument();
    expect(screen.getByText('Sagrada Familia')).toBeInTheDocument();
    expect(screen.getByText('Park Güell')).toBeInTheDocument();
  });

  it('collapsing the day card resets selected activity so re-expand shows timeline', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ItineraryDetailsComponent itineraryItems={mockItems} />);

    await user.click(screen.getByRole('button', { name: 'Expand day' }));
    await user.click(screen.getByText('Sagrada Familia'));

    expect(screen.getByTestId('itinerary-stop-detail')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Collapse day' }));
    await user.click(screen.getByRole('button', { name: 'Expand day' }));

    expect(screen.queryByTestId('itinerary-stop-detail')).not.toBeInTheDocument();
    expect(screen.getByText('Sagrada Familia')).toBeInTheDocument();
  });
});

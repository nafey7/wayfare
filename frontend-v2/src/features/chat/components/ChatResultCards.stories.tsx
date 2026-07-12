import type { Meta, StoryObj } from '@storybook/react-vite';
import { Box, Stack } from '@mantine/core';
import { expect, within } from 'storybook/test';
import { expectDurationPresent, expectPricePresent } from '@/stories/helpers/playAssertions';
import {
  FlightResultCard,
  HotelResultCard,
  ItineraryResultCard,
  TripResultCard,
} from './ChatResultCards';

// ── Chat shell (360px panel) ──────────────────────────────────────────────────

function ChatShell({ children }: { children: React.ReactNode }) {
  return (
    <Box style={{ width: 360, background: '#F8F9FF', border: '1px solid #E4E6F5', borderRadius: 12, overflow: 'hidden' }}>
      {/* Header */}
      <Box style={{ background: '#2A2F5F', padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'white', fontWeight: 600 }}>
        <Box style={{ width: 26, height: 26, borderRadius: '50%', background: '#667eea', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12 }}>V</Box>
        Voya
      </Box>
      {/* Messages */}
      <Box style={{ padding: '14px 12px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {children}
      </Box>
      {/* Input */}
      <Box style={{ margin: '0 12px 12px', padding: '8px 12px', background: 'white', border: '1px solid #E4E6F5', borderRadius: 9999, fontSize: 13, color: '#9aa2c5', display: 'flex', alignItems: 'center', gap: 8 }}>
        <Box style={{ width: 16, height: 16, borderRadius: '50%', background: '#dde1fb' }} />
        Message Voya
      </Box>
    </Box>
  );
}

function UserBubble({ children }: { children: string }) {
  return (
    <Box style={{ background: '#2A2F5F', color: 'white', borderRadius: '12px 12px 2px 12px', padding: '8px 12px', fontSize: 13, alignSelf: 'flex-end', maxWidth: '88%', lineHeight: 1.5 }}>
      {children}
    </Box>
  );
}

function BotBubble({ children }: { children: string }) {
  return (
    <Box style={{ background: 'white', border: '1px solid #E4E6F5', borderRadius: '12px 12px 12px 2px', padding: '8px 12px', fontSize: 13, color: '#2A2F5F', alignSelf: 'flex-start', maxWidth: '88%', lineHeight: 1.5 }}>
      {children}
    </Box>
  );
}

// ── Fixtures ──────────────────────────────────────────────────────────────────

const FLIGHT_PICKS = [
  { label: 'Best value',  airline: 'TAP Air Portugal', departure: '07:00', arrival: '10:25', duration: '2h 25m', stops: 'Non-stop', price: '£178', tag: 'Best'     },
  { label: 'Cheapest',    airline: 'Ryanair',           departure: '06:15', arrival: '09:55', duration: '3h 40m', stops: 'Non-stop', price: '£142', tag: 'Cheapest' },
  { label: 'Fastest',     airline: 'easyJet',           departure: '11:00', arrival: '13:10', duration: '2h 10m', stops: 'Non-stop', price: '£272', tag: 'Fastest'  },
];

const HOTEL_PICKS = [
  { name: 'Hotel Avenida Palace', stars: 5, area: 'Baixa',  rating: 9.4, price: '£142', priceUnit: '/night', imageUrl: 'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=100', badge: 'Best' },
  { name: 'Memmo Alfama',         stars: 4, area: 'Alfama', rating: 9.3, price: '£198', priceUnit: '/night', imageUrl: 'https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=100' },
  { name: 'Corinthia Lisbon',     stars: 4, area: 'Praça',  rating: 9.1, price: '£168', priceUnit: '/night', imageUrl: 'https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?w=100' },
];

const ITIN_DAYS = [
  { dayNumber: 1, date: 'Thu 15 May', title: 'Arrival in Lisbon & Riverside Welcome', stopCount: 6 },
  { dayNumber: 2, date: 'Fri 16 May', title: 'Sintra Palaces & Mountain Villages',    stopCount: 5 },
  { dayNumber: 3, date: 'Sat 17 May', title: 'Belém · Monasteries, Pastéis & Museums', stopCount: 6 },
  { dayNumber: 4, date: 'Sun 18 May', title: 'LX Factory, Shopping & Departure',      stopCount: 4 },
];

const TRIP_SECTIONS = [
  { emoji: '✈️', title: 'TAP · 07:00–10:25', sub: 'Non-stop · 2h 25m · LHR → LIS', price: '£178' },
  { emoji: '🏨', title: 'Hotel Avenida Palace', sub: '4 nights · Baixa · ★★★★★', price: '£568' },
  { emoji: '🗺️', title: '4-day Lisbon itinerary', sub: '20 stops · Sintra · Belém · LX Factory' },
];

// ── Meta ──────────────────────────────────────────────────────────────────────

const meta: Meta = {
  title: 'Chat/Result Cards',
  parameters: { layout: 'centered' },
};

export default meta;
type Story = StoryObj;

// ── Stories ───────────────────────────────────────────────────────────────────

export const Flights: Story = {
  name: 'Flights found',
  render: () => (
    <ChatShell>
      <UserBubble>Flights London → Lisbon, 15–25 May, 2 passengers</UserBubble>
      <BotBubble>Found 38 flights. Here are the top picks:</BotBubble>
      <FlightResultCard
        route="LHR → LIS"
        totalCount={38}
        picks={FLIGHT_PICKS}
      />
    </ChatShell>
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('TAP Air Portugal')).toBeTruthy();
    expectDurationPresent(canvas);
    expectPricePresent(canvas, '£');
  },
};

export const Hotels: Story = {
  name: 'Hotels found',
  render: () => (
    <ChatShell>
      <UserBubble>Hotels in Lisbon, 15–25 May, 2 guests</UserBubble>
      <BotBubble>48 hotels found. Top picks for you:</BotBubble>
      <HotelResultCard
        destination="Lisbon"
        totalCount={48}
        fromPrice="£142"
        picks={HOTEL_PICKS}
      />
    </ChatShell>
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Hotel Avenida Palace')).toBeTruthy();
    expectPricePresent(canvas, '£');
  },
};

export const Itinerary: Story = {
  name: 'Itinerary ready',
  render: () => (
    <ChatShell>
      <UserBubble>Plan a 4-day trip to Lisbon for 2</UserBubble>
      <BotBubble>Here's your personalised 4-day Lisbon itinerary:</BotBubble>
      <ItineraryResultCard
        destination="Lisbon"
        dateRange="15–18 May"
        days={ITIN_DAYS}
      />
    </ChatShell>
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Arrival in Lisbon & Riverside Welcome')).toBeTruthy();
    expect(canvas.getByText('Sintra Palaces & Mountain Villages')).toBeTruthy();
  },
};

export const WholeTrip: Story = {
  name: 'Whole trip ready',
  render: () => (
    <ChatShell>
      <UserBubble>Book everything for my Lisbon trip</UserBubble>
      <BotBubble>Your Lisbon trip is all set! Here's a summary:</BotBubble>
      <TripResultCard
        tripSummary="London → Lisbon · 15–18 May · 2"
        sections={TRIP_SECTIONS}
        totalEstimate="£746"
      />
    </ChatShell>
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('Hotel Avenida Palace')).toBeTruthy();
    expect(canvas.getByText('£746')).toBeTruthy();
  },
};

export const AllCards: Story = {
  name: 'All result types',
  render: () => (
    <Stack gap={24} style={{ maxWidth: 360 }}>
      <FlightResultCard route="LHR → LIS" totalCount={38} picks={FLIGHT_PICKS} />
      <HotelResultCard destination="Lisbon" totalCount={48} fromPrice="£142" picks={HOTEL_PICKS} />
      <ItineraryResultCard destination="Lisbon" dateRange="15–18 May" days={ITIN_DAYS} />
      <TripResultCard tripSummary="London → Lisbon · 15–18 May · 2" sections={TRIP_SECTIONS} totalEstimate="£746" />
    </Stack>
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByText('TAP Air Portugal')).toBeTruthy();
    expect(canvas.getAllByText('Hotel Avenida Palace')).toBeTruthy();
    expect(canvas.getByText('Arrival in Lisbon & Riverside Welcome')).toBeTruthy();
    expect(canvas.getByText('£746')).toBeTruthy();
  },
};

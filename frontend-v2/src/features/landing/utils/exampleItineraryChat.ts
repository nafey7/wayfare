import type { ItineraryCardItem } from '../components/ExampleItinerariesSection';

export function itineraryCardChatPrompt(item: ItineraryCardItem): string {
  const dedicated = item.examplePrompt?.trim();
  if (dedicated) return dedicated;
  return `Plan a trip like: ${item.tripTitle}, ${item.location}`;
}

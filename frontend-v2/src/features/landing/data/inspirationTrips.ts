import type { InspirationTripData } from '../components/InspirationTripCard';

import kyotoTokyoImage from '@/assets/images/landing-page/inspiration-trips/kyoto-tokyo.jpg';
import icelandRingRoadImage from '@/assets/images/landing-page/inspiration-trips/iceland-ring-road.jpg';
import pragueImage from '@/assets/images/landing-page/inspiration-trips/prague.jpg';
import marrakechAtlasImage from '@/assets/images/landing-page/inspiration-trips/marrakech-atlas.jpg';
import rioDeJaneiroHikeImage from '@/assets/images/landing-page/inspiration-trips/rio-de-janeiro-hike.jpg';
import victoriaFallsImage from '@/assets/images/landing-page/inspiration-trips/victoria-falls.jpg';
import lisbonImage from '@/assets/images/landing-page/inspiration-trips/lisbon.jpg';
import budapestImage from '@/assets/images/landing-page/inspiration-trips/budapest.jpg';
import miamiImage from '@/assets/images/landing-page/inspiration-trips/miami.jpg';
import sanSebastianImage from '@/assets/images/landing-page/inspiration-trips/san-sebastian.jpg';
import mykonosSantoriniImage from '@/assets/images/landing-page/inspiration-trips/mykonos-santorini.jpg';
import dubaiImage from '@/assets/images/landing-page/inspiration-trips/dubai.jpg';
import bangkokImage from '@/assets/images/landing-page/inspiration-trips/bangkok.jpg';
import copenhagenImage from '@/assets/images/landing-page/inspiration-trips/copenhagen.jpg';
import barcelonaImage from '@/assets/images/landing-page/inspiration-trips/barcelona.jpg';
import bergenImage from '@/assets/images/landing-page/inspiration-trips/bergen.jpg';
import amazonManausImage from '@/assets/images/landing-page/inspiration-trips/amazon-manaus.jpg';
import kenyaNairobiImage from '@/assets/images/landing-page/inspiration-trips/kenya-nairobi.jpg';
import cairoImage from '@/assets/images/landing-page/inspiration-trips/cairo.jpg';
import hanoiImage from '@/assets/images/landing-page/inspiration-trips/hanoi.jpg';

/** Destination city (used by trip-click handlers to set destination prompt). */
export interface InspirationTrip extends InspirationTripData {
  /** Required for hardcoded trips; absent on Strapi-sourced cards (use chatPrompt instead). */
  destinationCity?: string;
  /** Explicit origin city for the chat prompt. Falls back to parsing flightRoute if absent. */
  originCity?: string;
  /** Strapi-sourced prompt without origin. The frontend appends "My origin is {city}" before sending. */
  chatPrompt?: string;
}

// "From London" — built around a London origin (4 cards)
export const FROM_LONDON_TRIPS: InspirationTrip[] = [
  { id: 'lon-jpn',  originCity: 'London', destinationCity: 'Tokyo',     title: '7 days in Kyoto + Tokyo',       builtInSeconds: 58, flightRoute: 'LHR → KIX, HND → LHR', hotelName: 'The Hiramatsu · Park Hyatt', stops: 17, priceAmount: 2310, duration: '7 nights', theme: 'tokyo',   imageUrl: kyotoTokyoImage, tag: 'Culture',     rating: 4.9 },
  { id: 'lon-dxb', originCity: 'London', destinationCity: 'Dubai',      title: 'Family week in Dubai',          builtInSeconds: 62, flightRoute: 'LHR → DXB',            hotelName: 'Atlantis The Palm',          stops: 13, priceAmount: 2890, duration: '7 nights', theme: 'bali',    imageUrl: dubaiImage, tag: 'Family',      rating: 4.8 },
  { id: 'lon-rey',  originCity: 'London', destinationCity: 'Reykjavik', title: 'Iceland ring-road, 5 days',     builtInSeconds: 49, flightRoute: 'LHR → KEF',            hotelName: 'ION Adventure Hotel',        stops: 10, priceAmount: 1420, duration: '5 nights', theme: 'tokyo',   imageUrl: icelandRingRoadImage, tag: 'Adventure',   rating: 4.9 },
  { id: 'lon-bkk',  originCity: 'London', destinationCity: 'Bangkok',   title: 'Long weekend in Bangkok',       builtInSeconds: 41, flightRoute: 'LHR → BKK',            hotelName: 'The Siam',                   stops: 10, priceAmount: 1180, duration: '4 nights', theme: 'bangkok', imageUrl: bangkokImage, tag: 'City break',  rating: 4.6 },
];

// "Trips for this weekend" — short escapes with varied origins (4 cards)
export const WEEKEND_TRIPS: InspirationTrip[] = [
  { id: 'we-lis', originCity: 'Madrid',    destinationCity: 'Lisbon',     title: 'Weekend in Lisbon',     builtInSeconds: 41, flightRoute: 'MAD → LIS', hotelName: 'Memmo Alfama',   stops: 8,  priceAmount: 390,  duration: '2 nights', theme: 'lisbon',  imageUrl: lisbonImage, tag: 'Quick getaway', rating: 4.8 },
  { id: 'we-cph', originCity: 'Amsterdam', destinationCity: 'Copenhagen', title: 'Weekend in Copenhagen', builtInSeconds: 38, flightRoute: 'AMS → CPH', hotelName: 'Hotel Sanders',  stops: 7,  priceAmount: 440,  duration: '2 nights', theme: 'tokyo',   imageUrl: copenhagenImage, tag: 'Design',        rating: 4.9 },
  { id: 'we-bcn', originCity: 'Paris',     destinationCity: 'Barcelona',  title: 'Weekend in Barcelona',  builtInSeconds: 36, flightRoute: 'CDG → BCN', hotelName: 'Hotel Brummell', stops: 9,  priceAmount: 360,  duration: '2 nights', theme: 'bali',    imageUrl: barcelonaImage, tag: 'Foodie',        rating: 4.7 },
  { id: 'we-prg', originCity: 'Vienna',    destinationCity: 'Prague',     title: 'Weekend in Prague',     builtInSeconds: 44, flightRoute: 'VIE → PRG', hotelName: 'Aria Hotel Prague', stops: 10, priceAmount: 310,  duration: '3 nights', theme: 'bangkok', imageUrl: pragueImage, tag: 'Culture',       rating: 4.7 },
];

// "By your interests" — chip-filtered, varied global origins
export const INTEREST_TRIPS: Record<string, InspirationTrip[]> = {
  adventure: [
    { id: 'int-vfa', originCity: 'New York',  destinationCity: 'Victoria Falls', title: 'Victoria Falls + safari, 6 days', builtInSeconds: 57, flightRoute: 'JFK → VFA',       hotelName: 'Victoria Falls Hotel',    stops: 13, priceAmount: 3260, duration: '6 nights',  theme: 'tokyo',   imageUrl: victoriaFallsImage, tag: 'Adventure', rating: 4.9 },
    { id: 'int-rio', originCity: 'Miami',       destinationCity: 'Rio de Janeiro', title: 'Rio + jungle hikes, 8 days', builtInSeconds: 64, flightRoute: 'MIA → GIG',       hotelName: 'Belmond Copacabana Palace', stops: 11, priceAmount: 3490, duration: '8 nights',  theme: 'bali',    imageUrl: rioDeJaneiroHikeImage, tag: 'Adventure', rating: 4.9 },
    { id: 'int-nor', originCity: 'Amsterdam',   destinationCity: 'Bergen',     title: 'Norwegian fjords cruise',    builtInSeconds: 53, flightRoute: 'AMS → BGO',       hotelName: 'Hurtigruten coastal',     stops: 12, priceAmount: 1980, duration: '6 nights',  theme: 'tokyo',   imageUrl: bergenImage, tag: 'Adventure', rating: 4.8 },
  ],
  beach: [
    { id: 'bch-gri', originCity: 'Berlin',    destinationCity: 'Mykonos', title: 'Mykonos + Santorini hop', builtInSeconds: 47, flightRoute: 'BER → JMK', hotelName: 'Cavo Tagoo · Canaves Oia', stops: 11, priceAmount: 2050, duration: '7 nights', theme: 'lisbon',  imageUrl: mykonosSantoriniImage, tag: 'Beach', rating: 4.8 },
    { id: 'bch-mia', originCity: 'New York',  destinationCity: 'Miami',   title: 'Miami Beach long weekend', builtInSeconds: 38, flightRoute: 'JFK → MIA', hotelName: 'Faena Hotel Miami Beach',  stops: 9,  priceAmount: 1290, duration: '4 nights', theme: 'bangkok', imageUrl: miamiImage, tag: 'Beach', rating: 4.7 },
  ],
  nature: [
    { id: 'nat-amz', originCity: 'Miami',      destinationCity: 'Manaus',     title: 'Amazon rainforest adventure',    builtInSeconds: 58, flightRoute: 'MIA → MAO',            hotelName: 'Anavilhanas Jungle Lodge',         stops: 13, priceAmount: 2640, duration: '8 nights', theme: 'tokyo',   imageUrl: amazonManausImage, tag: 'Nature', rating: 4.9 },
    { id: 'nat-nai', originCity: 'Cape Town',  destinationCity: 'Nairobi',    title: 'Kenya safari + Masai Mara',      builtInSeconds: 67, flightRoute: 'CPT → NBO',            hotelName: 'Giraffe Manor · Angama Mara',      stops: 14, priceAmount: 38000, duration: '9 nights', theme: 'tokyo',   imageUrl: kenyaNairobiImage, tag: 'Nature', rating: 4.9 },
  ],
  // Intentionally one card — San Sebastián is a standout single destination for this category.
  food: [
    { id: 'fd-sse', originCity: 'Barcelona',  destinationCity: 'San Sebastián', title: 'San Sebastián pintxos crawl', builtInSeconds: 42, flightRoute: 'BCN → BIO', hotelName: 'Hotel Maria Cristina',    stops: 12, priceAmount: 1480, duration: '4 nights', theme: 'lisbon', imageUrl: sanSebastianImage, tag: 'Foodie',      rating: 4.9 },
  ],
  culture: [
    { id: 'cul-cai', originCity: 'Dubai',     destinationCity: 'Cairo',     title: 'Cairo + pyramids week',       builtInSeconds: 59, flightRoute: 'DXB → CAI', hotelName: 'Marriott Mena House',      stops: 12, priceAmount: 3200, duration: '7 nights', theme: 'bangkok', imageUrl: cairoImage, tag: 'Culture', rating: 4.7 },
    { id: 'cul-han', originCity: 'Singapore', destinationCity: 'Hanoi',     title: 'Hanoi + Halong Bay',          builtInSeconds: 63, flightRoute: 'SIN → HAN', hotelName: 'Sofitel Legend Metropole', stops: 13, priceAmount: 2100, duration: '8 nights', theme: 'tokyo',   imageUrl: hanoiImage, tag: 'Culture', rating: 4.9 },
  ],
  hidden: [
    { id: 'hid-mrk', originCity: 'London',      destinationCity: 'Marrakech',     title: 'Marrakech medina & Atlas trek', builtInSeconds: 54, flightRoute: 'LHR → RAK',       hotelName: 'La Mamounia',          stops: 11, priceAmount: 980,  duration: '6 nights',  theme: 'bangkok', imageUrl: marrakechAtlasImage, tag: 'Hidden gem', rating: 4.8 },
    { id: 'hid-bud', originCity: 'Paris',        destinationCity: 'Budapest',      title: 'Budapest thermal baths & ruin bars', builtInSeconds: 47, flightRoute: 'CDG → BUD', hotelName: 'Aria Hotel Budapest',  stops: 9,  priceAmount: 840,  duration: '6 nights',  theme: 'lisbon',  imageUrl: budapestImage, tag: 'Hidden gem', rating: 4.7 },
  ],
};

export const INTEREST_CHIPS = [
  { id: 'adventure', label: 'Adventure',   icon: '🏔' },
  { id: 'beach',     label: 'Beach',       icon: '🏖' },
  { id: 'nature',    label: 'Nature',      icon: '🌿' },
  { id: 'food',      label: 'Food & wine', icon: '🍽' },
  { id: 'culture',   label: 'Culture',     icon: '🎭' },
  { id: 'hidden',    label: 'Hidden gems', icon: '💎' },
];

/**
 * Public landing (`/`) and authenticated home (`/home`). Stable marketing DOM ids on `/` only —
 * see `docs/LANDING_DOM_IDS.md` (`frontend-v2/docs/LANDING_DOM_IDS.md`).
 */
export { PublicLandingPage } from './PublicLandingPage';
export { HomePage } from './HomePage';
export {
  ExampleItinerariesSection,
  HomeHero,
  HomeSignInCard,
  InspirationTripCard,
  TripsRail,
  EditorialCard,
} from './components';
export type {
  InspirationTripData,
  RailChip,
  HomeHeroProps,
  HomeHeroDomIds,
  TripsRailProps,
  TripsRailDomIds,
  EditorialCardProps,
  EditorialCardDomIds,
} from './components';

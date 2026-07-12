import type { InspirationTrip } from '@/features/landing/data/inspirationTrips';
import { pickMediaUrl } from './strapiMedia';

const VALID_THEMES = ['lisbon', 'tokyo', 'bali', 'bangkok'] as const;
type Theme = (typeof VALID_THEMES)[number];

type StrapiRecord = Record<string, unknown>;

function isRecord(v: unknown): v is StrapiRecord {
  return v !== null && typeof v === 'object' && !Array.isArray(v);
}

function componentFields(node: unknown): StrapiRecord {
  if (!isRecord(node)) return {};
  if (isRecord(node.attributes)) return node.attributes as StrapiRecord;
  return node;
}

function str(raw: unknown): string | undefined {
  if (raw == null) return undefined;
  if (typeof raw === 'string') return raw.length ? raw : undefined;
  if (typeof raw === 'number') return String(raw);
  return undefined;
}

function num(raw: unknown): number | undefined {
  if (typeof raw === 'number') return raw;
  if (typeof raw === 'string') {
    const n = Number(raw);
    return Number.isFinite(n) ? n : undefined;
  }
  return undefined;
}

function parsePriceAmount(raw: unknown): number | undefined {
  const s = str(raw);
  if (!s) return undefined;
  const n = parseFloat(s.replace(/[^0-9.]/g, ''));
  return Number.isFinite(n) && n > 0 ? n : undefined;
}

function mapTripCard(item: unknown, strapiBaseUrl: string, index: number): InspirationTrip | null {
  const f = componentFields(item);
  const title = str(f.title);
  const flightRoute = str(f.flightRoute);
  const hotelName = str(f.hotelName);
  // Currency is not sourced from Strapi — the codebase default (USD) is applied by InspirationTripCard.
  const priceAmount = parsePriceAmount(f.totalPrice) ?? parsePriceAmount(f.priceAmount);
  const duration = str(f.duration);
  const chatPrompt = str(f.chatPrompt);

  if (!title || !flightRoute || !hotelName || priceAmount == null || !duration || !chatPrompt) {
    return null;
  }

  const rawTheme = f.theme;
  const theme: Theme = VALID_THEMES.includes(rawTheme as Theme) ? (rawTheme as Theme) : 'lisbon';
  const imageUrl = pickMediaUrl(f.image, strapiBaseUrl);
  const builtInSeconds = num(f.builtInSeconds) ?? 45;
  const stops = num(f.stops) ?? 0;
  const rating = num(f.rating);
  const tag = str(f.tag);

  const id = `strapi-${index}-${title.toLowerCase().replace(/\s+/g, '-').slice(0, 20)}`;

  return {
    id,
    title,
    flightRoute,
    hotelName,
    priceAmount,
    duration,
    builtInSeconds,
    stops,
    theme,
    chatPrompt,
    ...(imageUrl ? { imageUrl } : {}),
    ...(rating != null ? { rating } : {}),
    ...(tag ? { tag } : {}),
  };
}

function mapTripCards(raw: unknown, strapiBaseUrl: string): InspirationTrip[] {
  if (!Array.isArray(raw)) return [];
  const out: InspirationTrip[] = [];
  raw.forEach((item, i) => {
    const card = mapTripCard(item, strapiBaseUrl, i);
    if (card) out.push(card);
  });
  return out;
}

export interface InspirationRailOverride {
  title?: string;
  subtitle?: string;
  trips: InspirationTrip[];
}

export interface VoyaPicksCardData {
  eyebrow?: string;
  title?: string;
  body?: string;
  chatPrompt?: string;
  meta?: string[];
  ctaLabel?: string;
  imageUrl?: string;
}

export interface HeroContent {
  headline?: string;
  subheadline?: string;
  calloutText?: string;
  calloutTextMobile?: string;
  avatarImageUrl?: string;
  flightOrigin?: string;
  flightDestination?: string;
  flightDetails?: string;
  hotelName?: string;
  hotelDetails?: string;
  ctaLabel?: string;
}

export interface InspirationRailsData {
  weekendRail?: InspirationRailOverride;
  fromCityRail?: InspirationRailOverride;
  /** Keyed by interest id: adventure, beach, nature, food, culture, hidden */
  interestRails?: Partial<Record<string, InspirationTrip[]>>;
  voyaPicksCard?: VoyaPicksCardData;
  heroContent?: HeroContent;
}

export function mapInspirationRailsResponse(
  json: unknown,
  strapiBaseUrl: string,
): InspirationRailsData {
  if (!isRecord(json)) return {};

  // Strapi collection type: { data: [{ id, attributes: {...} }] } — pick first entry.
  // Also handles legacy flat shape for resilience.
  let attrs: StrapiRecord;
  if (Array.isArray(json.data) && json.data.length > 0) {
    const first = json.data[0] as unknown;
    if (isRecord(first)) {
      attrs = isRecord(first.attributes) ? (first.attributes as StrapiRecord) : first;
    } else {
      return {};
    }
  } else if (isRecord(json.data)) {
    const d = json.data as StrapiRecord;
    attrs = isRecord(d.attributes) ? (d.attributes as StrapiRecord) : d;
  } else {
    attrs = json as StrapiRecord;
  }

  const result: InspirationRailsData = {};

  const weekendTrips = mapTripCards(attrs.weekendTrips, strapiBaseUrl);
  if (weekendTrips.length > 0) {
    result.weekendRail = {
      trips: weekendTrips,
      ...(str(attrs.weekendRailTitle) ? { title: str(attrs.weekendRailTitle) } : {}),
      ...(str(attrs.weekendRailSubtitle) ? { subtitle: str(attrs.weekendRailSubtitle) } : {}),
    };
  }

  const fromCityTrips = mapTripCards(attrs.fromCityTrips, strapiBaseUrl);
  if (fromCityTrips.length > 0) {
    result.fromCityRail = {
      trips: fromCityTrips,
      ...(str(attrs.fromCityRailTitle) ? { title: str(attrs.fromCityRailTitle) } : {}),
      ...(str(attrs.fromCityRailSubtitle) ? { subtitle: str(attrs.fromCityRailSubtitle) } : {}),
    };
  }

  const interestKeys = ['adventure', 'beach', 'nature', 'food', 'culture', 'hidden'] as const;
  const interestRails: Partial<Record<string, InspirationTrip[]>> = {};
  let hasAnyInterest = false;
  for (const key of interestKeys) {
    const trips = mapTripCards(attrs[`${key}Trips`], strapiBaseUrl);
    if (trips.length > 0) {
      interestRails[key] = trips;
      hasAnyInterest = true;
    }
  }
  if (hasAnyInterest) result.interestRails = interestRails;

  const voyaPicksTitle = str(attrs.voyaPicksTitle);
  if (voyaPicksTitle) {
    const metaRaw = str(attrs.voyaPicksMeta);
    const imageUrl = pickMediaUrl(attrs.voyaPicksImage, strapiBaseUrl);
    result.voyaPicksCard = {
      title: voyaPicksTitle,
      ...(str(attrs.voyaPicksEyebrow) ? { eyebrow: str(attrs.voyaPicksEyebrow) } : {}),
      ...(str(attrs.voyaPicksBody) ? { body: str(attrs.voyaPicksBody) } : {}),
      ...(str(attrs.voyaPicksChatPrompt) ? { chatPrompt: str(attrs.voyaPicksChatPrompt) } : {}),
      ...(metaRaw ? { meta: metaRaw.split('|').map((m) => m.trim()).filter(Boolean) } : {}),
      ...(str(attrs.voyaPicksCtaLabel) ? { ctaLabel: str(attrs.voyaPicksCtaLabel) } : {}),
      ...(imageUrl ? { imageUrl } : {}),
    };
  }

  const heroHeadline = str(attrs.heroHeadline);
  const heroSubheadline = str(attrs.heroSubheadline);
  const heroCalloutText = str(attrs.heroCalloutText);
  const heroCalloutTextMobile = str(attrs.heroCalloutTextMobile);
  const heroAvatarImageUrl = pickMediaUrl(attrs.heroAvatarImage, strapiBaseUrl);
  const heroFlightOrigin = str(attrs.heroFlightOrigin);
  const heroFlightDestination = str(attrs.heroFlightDestination);
  const heroFlightDetails = str(attrs.heroFlightDetails);
  const heroHotelName = str(attrs.heroHotelName);
  const heroHotelDetails = str(attrs.heroHotelDetails);
  // Preserve empty string: '' signals "hide CTA" in HomeHero, unlike other fields where '' → undefined.
  const heroCtaLabel = typeof attrs.heroCtaLabel === 'string' ? attrs.heroCtaLabel : undefined;

  if (
    heroHeadline ||
    heroSubheadline ||
    heroCalloutText ||
    heroAvatarImageUrl ||
    heroFlightOrigin
  ) {
    result.heroContent = {
      ...(heroHeadline ? { headline: heroHeadline } : {}),
      ...(heroSubheadline ? { subheadline: heroSubheadline } : {}),
      ...(heroCalloutText ? { calloutText: heroCalloutText } : {}),
      ...(heroCalloutTextMobile ? { calloutTextMobile: heroCalloutTextMobile } : {}),
      ...(heroAvatarImageUrl ? { avatarImageUrl: heroAvatarImageUrl } : {}),
      ...(heroFlightOrigin ? { flightOrigin: heroFlightOrigin } : {}),
      ...(heroFlightDestination ? { flightDestination: heroFlightDestination } : {}),
      ...(heroFlightDetails ? { flightDetails: heroFlightDetails } : {}),
      ...(heroHotelName ? { hotelName: heroHotelName } : {}),
      ...(heroHotelDetails ? { hotelDetails: heroHotelDetails } : {}),
      ...(heroCtaLabel !== undefined ? { ctaLabel: heroCtaLabel } : {}),
    };
  }

  return result;
}

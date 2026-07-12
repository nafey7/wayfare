import { formatPrice } from '@/features/chat/utils/formatters';

/**
 * Shared intro extraction: backend sends full markdown with category sections;
 * chat UIs often show only the text before `###` headings or legacy `**` blocks.
 */
function getMarkdownIntroSummary(text: string): string {
  if (!text?.trim()) return '';
  const beforeCategories = text.split(/\n+###\s|\n+\*\*/)[0]?.trim();
  return beforeCategories || text;
}

/**
 * Extract the summary portion of a flight search message for chat display.
 * Backend sends full message including category sections ("### Best Value", "**Cheapest**", etc.);
 * in chat we show only the intro (e.g. "I found several one-way flights... Here are your top options:").
 */
export function getFlightSearchMessageSummary(text: string): string {
  const intro = getMarkdownIntroSummary(text);
  if (!intro) return 'Here are your flight options.';
  return intro;
}

/**
 * Short summary for hotel search in chat; full results UI lives in /hotels/search.
 */
export function getHotelSearchMessageSummary(
  text: string,
  extraData?: Record<string, unknown>
): string {
  const root = extraData as
    | {
        data?: {
          summary?: {
            total_found?: number;
            total_hotels?: number;
            nights?: number;
            price_range?: { min?: number; currency?: string };
          };
          search_params?: Record<string, unknown>;
        };
      }
    | undefined;
  const data = root?.data;
  if (data?.summary && data.search_params) {
    const summary = data.summary;
    const sp = data.search_params;
    const dest = String(
      sp.destination_city ?? sp.destination ?? sp.city_name ?? 'your destination'
    );
    const total = summary.total_found ?? summary.total_hotels ?? 0;
    const nights = summary.nights ?? 1;
    const priceRange = summary.price_range ?? {};
    const minPrice = (priceRange as { min?: number }).min;
    const currency = (priceRange as { currency?: string }).currency ?? 'GBP';
    if (total > 0) {
      return `We found ${total} hotel${total !== 1 ? 's' : ''} in ${dest} for ${nights} night${nights !== 1 ? 's' : ''}${minPrice != null ? `. Prices start from ${formatPrice(minPrice, currency)}.` : '.'}`;
    }
    return `Here are the hotel options in ${dest}.`;
  }
  const intro = getMarkdownIntroSummary(text);
  if (!intro) return 'Here are your hotel options.';
  return intro;
}

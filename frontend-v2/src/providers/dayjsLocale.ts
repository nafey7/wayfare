import dayjs from 'dayjs';
import customParseFormat from 'dayjs/plugin/customParseFormat';
import localizedFormat from 'dayjs/plugin/localizedFormat';

dayjs.extend(customParseFormat);
dayjs.extend(localizedFormat);

/** Locale string used by DatesProvider and any direct dayjs calls in product code. */
export const dayjsLocale = 'en';

/** First day of week: 1 = Monday (ISO standard). Applies to DatesProvider and should match MUI X. */
export const firstDayOfWeek = 1 as const;

/** Weekend days: 0 = Sunday, 6 = Saturday. Co-located with firstDayOfWeek for future i18n. */
export const weekendDays = [0, 6] as const;

/**
 * Configure dayjs with the chosen locale.
 * Call once at app startup before rendering. Used by AppProviders.
 * Accepts an optional locale to enable future i18n switching without touching AppProviders.
 */
export function configureDayjs(locale: string = dayjsLocale): void {
  dayjs.locale(locale);
}

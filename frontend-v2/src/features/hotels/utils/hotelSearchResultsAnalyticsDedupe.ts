const firedKeys = new Set<string>();

export function hotelSearchResultsShownDedupeKey(
  source: string,
  sessionId: string | undefined,
  sp: Record<string, unknown> | undefined
): string {
  const dest = String(sp?.destination_city ?? sp?.destination ?? sp?.city_name ?? '');
  const cin = String(sp?.check_in_date ?? sp?.checkin ?? '');
  const cout = String(sp?.check_out_date ?? sp?.checkout ?? '');
  return `${source}|${sessionId ?? ''}|${dest}|${cin}|${cout}`;
}

/** Returns true the first time this key is seen (module-scoped, survives remounts). */
export function tryMarkHotelSearchResultsShown(dedupeKey: string): boolean {
  if (firedKeys.has(dedupeKey)) return false;
  firedKeys.add(dedupeKey);
  return true;
}

/** For tests only — clears dedupe state between cases. */
export function resetHotelSearchResultsShownDedupeForTests(): void {
  firedKeys.clear();
}

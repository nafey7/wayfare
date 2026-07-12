/** ISO `YYYY-MM-DD` → `MM/DD/YYYY` for passenger summary lines. */
export function formatIsoDobForDisplay(iso: string | null | undefined): string {
  if (!iso?.trim()) return '—';
  const m = iso.trim().match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!m) return iso;
  return `${m[2]}/${m[3]}/${m[1]}`;
}

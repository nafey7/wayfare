export function getStructuredItinerary(
  extra: Record<string, unknown> | undefined
): Record<string, unknown> | null {
  if (!extra) return null;
  const structured = extra.structured_itinerary;
  return structured && typeof structured === 'object' ? (structured as Record<string, unknown>) : null;
}

/** Reject missing, non-finite, out-of-range, and (0,0) sentinel coords from bad API data. */
export function isValidHotelMapCoordinates(
  latitude: number | undefined,
  longitude: number | undefined,
): boolean {
  if (latitude === undefined || longitude === undefined) return false;
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return false;
  if (latitude === 0 && longitude === 0) return false;
  if (latitude < -90 || latitude > 90) return false;
  if (longitude < -180 || longitude > 180) return false;
  return true;
}

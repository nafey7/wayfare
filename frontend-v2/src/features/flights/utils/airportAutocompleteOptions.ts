import type { AirportOption } from '@/types/flights';

/** Raw row from airport search (before city-wide option rows are added). */
export type AirportSearchResultRow = {
  iata: string;
  name: string;
  city: string;
  state?: string;
  country: string;
};

/**
 * Builds Autocomplete options: one "City (Any)" row per city, then individual airports.
 * Both city-wide and individual airport rows are always emitted so that IATA-code
 * searches surface a directly selectable airport row.
 */
export function buildAirportAutocompleteOptions(
  airports: AirportSearchResultRow[]
): AirportOption[] {
  if (airports.length === 0) return [];

  const cityCountryGroups: Record<string, AirportSearchResultRow[]> = {};

  airports.forEach((airport) => {
    const cityKey = `${airport.city.toLowerCase()}|${airport.country}`;
    if (!cityCountryGroups[cityKey]) {
      cityCountryGroups[cityKey] = [];
    }
    cityCountryGroups[cityKey].push(airport);
  });

  const results: AirportOption[] = [];

  Object.entries(cityCountryGroups).forEach(([, cityAirports]) => {
    // The city-wide option uses the first airport's IATA as a representative code.
    // This depends on backend result ordering, which is not guaranteed to be stable.
    const firstAirport = cityAirports[0];
    if (firstAirport) {
      results.push({
        iata: firstAirport.iata,
        name: `${firstAirport.city} (Any)`,
        city: firstAirport.city,
        state: firstAirport.state,
        country: firstAirport.country,
        isCityOption: true,
      });
    }
  });

  airports.forEach((airport) => {
    results.push({ ...airport });
  });

  return results;
}

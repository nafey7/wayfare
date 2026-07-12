/**
 * Curated country / city / currency dataset for the onboarding location step (Screen 2)
 * and legacy hydration for trip city fields saved as short names.
 *
 * Trip step (Screen 3) uses live city search via Open-Meteo Geocoding (see `openMeteoGeocoding.ts`).
 */

export interface CountryEntry {
  code: string; // ISO 3166-1 alpha-2
  name: string;
  currency: string; // ISO 4217
  currencySymbol: string;
  cities: string[];
}

export const COUNTRIES: CountryEntry[] = [
  { code: 'GB', name: 'United Kingdom', currency: 'GBP', currencySymbol: '£', cities: ['London', 'Manchester', 'Edinburgh', 'Birmingham', 'Glasgow', 'Liverpool', 'Bristol'] },
  { code: 'US', name: 'United States', currency: 'USD', currencySymbol: '$', cities: ['New York', 'Los Angeles', 'Chicago', 'San Francisco', 'Miami', 'Boston', 'Seattle', 'Washington DC'] },
  { code: 'CA', name: 'Canada', currency: 'CAD', currencySymbol: '$', cities: ['Toronto', 'Vancouver', 'Montreal', 'Calgary', 'Ottawa'] },
  { code: 'IE', name: 'Ireland', currency: 'EUR', currencySymbol: '€', cities: ['Dublin', 'Cork', 'Galway'] },
  { code: 'FR', name: 'France', currency: 'EUR', currencySymbol: '€', cities: ['Paris', 'Lyon', 'Marseille', 'Nice', 'Bordeaux', 'Toulouse'] },
  { code: 'DE', name: 'Germany', currency: 'EUR', currencySymbol: '€', cities: ['Berlin', 'Munich', 'Hamburg', 'Frankfurt', 'Cologne', 'Düsseldorf'] },
  { code: 'ES', name: 'Spain', currency: 'EUR', currencySymbol: '€', cities: ['Madrid', 'Barcelona', 'Valencia', 'Seville', 'Málaga', 'Bilbao'] },
  { code: 'IT', name: 'Italy', currency: 'EUR', currencySymbol: '€', cities: ['Rome', 'Milan', 'Florence', 'Venice', 'Naples', 'Turin'] },
  { code: 'PT', name: 'Portugal', currency: 'EUR', currencySymbol: '€', cities: ['Lisbon', 'Porto', 'Faro'] },
  { code: 'NL', name: 'Netherlands', currency: 'EUR', currencySymbol: '€', cities: ['Amsterdam', 'Rotterdam', 'The Hague', 'Utrecht'] },
  { code: 'BE', name: 'Belgium', currency: 'EUR', currencySymbol: '€', cities: ['Brussels', 'Antwerp', 'Ghent'] },
  { code: 'CH', name: 'Switzerland', currency: 'CHF', currencySymbol: 'CHF', cities: ['Zurich', 'Geneva', 'Basel', 'Bern'] },
  { code: 'AT', name: 'Austria', currency: 'EUR', currencySymbol: '€', cities: ['Vienna', 'Salzburg', 'Innsbruck'] },
  { code: 'DK', name: 'Denmark', currency: 'DKK', currencySymbol: 'kr', cities: ['Copenhagen', 'Aarhus'] },
  { code: 'SE', name: 'Sweden', currency: 'SEK', currencySymbol: 'kr', cities: ['Stockholm', 'Gothenburg', 'Malmö'] },
  { code: 'NO', name: 'Norway', currency: 'NOK', currencySymbol: 'kr', cities: ['Oslo', 'Bergen'] },
  { code: 'FI', name: 'Finland', currency: 'EUR', currencySymbol: '€', cities: ['Helsinki', 'Turku'] },
  { code: 'PL', name: 'Poland', currency: 'PLN', currencySymbol: 'zł', cities: ['Warsaw', 'Krakow', 'Gdańsk'] },
  { code: 'CZ', name: 'Czech Republic', currency: 'CZK', currencySymbol: 'Kč', cities: ['Prague', 'Brno'] },
  { code: 'GR', name: 'Greece', currency: 'EUR', currencySymbol: '€', cities: ['Athens', 'Thessaloniki'] },
  { code: 'TR', name: 'Turkey', currency: 'TRY', currencySymbol: '₺', cities: ['Istanbul', 'Ankara', 'Antalya'] },
  { code: 'AE', name: 'United Arab Emirates', currency: 'AED', currencySymbol: 'د.إ', cities: ['Dubai', 'Abu Dhabi'] },
  { code: 'SG', name: 'Singapore', currency: 'SGD', currencySymbol: '$', cities: ['Singapore'] },
  { code: 'HK', name: 'Hong Kong', currency: 'HKD', currencySymbol: '$', cities: ['Hong Kong'] },
  { code: 'JP', name: 'Japan', currency: 'JPY', currencySymbol: '¥', cities: ['Tokyo', 'Osaka', 'Kyoto'] },
  { code: 'KR', name: 'South Korea', currency: 'KRW', currencySymbol: '₩', cities: ['Seoul', 'Busan'] },
  { code: 'CN', name: 'China', currency: 'CNY', currencySymbol: '¥', cities: ['Beijing', 'Shanghai', 'Guangzhou', 'Shenzhen'] },
  { code: 'IN', name: 'India', currency: 'INR', currencySymbol: '₹', cities: ['Mumbai', 'Delhi', 'Bangalore', 'Chennai'] },
  { code: 'TH', name: 'Thailand', currency: 'THB', currencySymbol: '฿', cities: ['Bangkok', 'Phuket', 'Chiang Mai'] },
  { code: 'AU', name: 'Australia', currency: 'AUD', currencySymbol: '$', cities: ['Sydney', 'Melbourne', 'Brisbane', 'Perth'] },
  { code: 'NZ', name: 'New Zealand', currency: 'NZD', currencySymbol: '$', cities: ['Auckland', 'Wellington', 'Christchurch'] },
  { code: 'BR', name: 'Brazil', currency: 'BRL', currencySymbol: 'R$', cities: ['São Paulo', 'Rio de Janeiro', 'Brasília'] },
  { code: 'MX', name: 'Mexico', currency: 'MXN', currencySymbol: '$', cities: ['Mexico City', 'Cancún', 'Guadalajara'] },
  { code: 'AR', name: 'Argentina', currency: 'ARS', currencySymbol: '$', cities: ['Buenos Aires'] },
  { code: 'ZA', name: 'South Africa', currency: 'ZAR', currencySymbol: 'R', cities: ['Johannesburg', 'Cape Town'] },
  { code: 'EG', name: 'Egypt', currency: 'EGP', currencySymbol: 'E£', cities: ['Cairo'] },
  { code: 'IL', name: 'Israel', currency: 'ILS', currencySymbol: '₪', cities: ['Tel Aviv', 'Jerusalem'] },
  { code: 'SA', name: 'Saudi Arabia', currency: 'SAR', currencySymbol: 'ر.س', cities: ['Riyadh', 'Jeddah'] },
  { code: 'MY', name: 'Malaysia', currency: 'MYR', currencySymbol: 'RM', cities: ['Kuala Lumpur'] },
  { code: 'ID', name: 'Indonesia', currency: 'IDR', currencySymbol: 'Rp', cities: ['Jakarta', 'Bali'] },
];

export function findCountryByCode(code: string): CountryEntry | undefined {
  return COUNTRIES.find((c) => c.code === code);
}

export function findCountryByName(name: string): CountryEntry | undefined {
  return COUNTRIES.find((c) => c.name.toLowerCase() === name.toLowerCase());
}

export interface CurrencyEntry {
  code: string; // ISO 4217
  symbol: string;
  name: string;
}

export const CURRENCIES: CurrencyEntry[] = [
  { code: 'GBP', symbol: '£', name: 'British Pound' },
  { code: 'EUR', symbol: '€', name: 'Euro' },
  { code: 'USD', symbol: '$', name: 'US Dollar' },
  { code: 'CAD', symbol: '$', name: 'Canadian Dollar' },
  { code: 'AUD', symbol: '$', name: 'Australian Dollar' },
  { code: 'NZD', symbol: '$', name: 'New Zealand Dollar' },
  { code: 'CHF', symbol: 'CHF', name: 'Swiss Franc' },
  { code: 'SEK', symbol: 'kr', name: 'Swedish Krona' },
  { code: 'NOK', symbol: 'kr', name: 'Norwegian Krone' },
  { code: 'DKK', symbol: 'kr', name: 'Danish Krone' },
  { code: 'PLN', symbol: 'zł', name: 'Polish Złoty' },
  { code: 'CZK', symbol: 'Kč', name: 'Czech Koruna' },
  { code: 'HUF', symbol: 'Ft', name: 'Hungarian Forint' },
  { code: 'TRY', symbol: '₺', name: 'Turkish Lira' },
  { code: 'AED', symbol: 'د.إ', name: 'UAE Dirham' },
  { code: 'SAR', symbol: 'ر.س', name: 'Saudi Riyal' },
  { code: 'ILS', symbol: '₪', name: 'Israeli Shekel' },
  { code: 'EGP', symbol: 'E£', name: 'Egyptian Pound' },
  { code: 'ZAR', symbol: 'R', name: 'South African Rand' },
  { code: 'SGD', symbol: '$', name: 'Singapore Dollar' },
  { code: 'HKD', symbol: '$', name: 'Hong Kong Dollar' },
  { code: 'JPY', symbol: '¥', name: 'Japanese Yen' },
  { code: 'KRW', symbol: '₩', name: 'South Korean Won' },
  { code: 'CNY', symbol: '¥', name: 'Chinese Yuan' },
  { code: 'INR', symbol: '₹', name: 'Indian Rupee' },
  { code: 'THB', symbol: '฿', name: 'Thai Baht' },
  { code: 'MYR', symbol: 'RM', name: 'Malaysian Ringgit' },
  { code: 'IDR', symbol: 'Rp', name: 'Indonesian Rupiah' },
  { code: 'BRL', symbol: 'R$', name: 'Brazilian Real' },
  { code: 'MXN', symbol: '$', name: 'Mexican Peso' },
  { code: 'ARS', symbol: '$', name: 'Argentine Peso' },
];

export function findCurrencyByCode(code: string): CurrencyEntry | undefined {
  return CURRENCIES.find((c) => c.code === code);
}

export interface CityOption {
  value: string; // unique: `${city}|${countryCode}`
  city: string;
  country: string;
  countryCode: string;
  label: string; // display: "City · Country"
}

export const ALL_CITIES: CityOption[] = COUNTRIES.flatMap((c) =>
  c.cities.map((city) => ({
    value: `${city}|${c.code}`,
    city,
    country: c.name,
    countryCode: c.code,
    label: `${city} · ${c.name}`,
  }))
).sort((a, b) => a.city.localeCompare(b.city));

export function findCityByValue(value: string): CityOption | undefined {
  return ALL_CITIES.find((c) => c.value === value);
}

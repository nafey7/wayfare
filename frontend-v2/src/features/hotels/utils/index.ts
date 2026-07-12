/**
 * Hotel-specific helpers.
 */
export {
  serializeHotelSearchParamsToUrl,
  deserializeHotelSearchParamsFromUrl,
} from './urlParams';
export {
  filterHotels,
  toFilterableHotel,
  getHotelTotal,
  getHotelCurrency,
  hotelCurrencySymbol,
  countActiveHotelFilters,
  defaultHotelFilterState,
  isDefaultHotelFilterState,
  extractPropertyTypesFromHotels,
  getDistanceBounds,
  extractFacilitiesFromHotels,
  extractLocalitiesFromHotels,
  type HotelFilterState,
  type FilterableHotel,
} from './hotelFilters';
export {
  sortHotels,
  getHotelPrice,
  getHotelRating,
  getHotelName,
  DEFAULT_HOTEL_SORT,
  HOTEL_SORT_OPTIONS,
  type HotelSortOption,
} from './hotelSort';
export {
  validateEmail,
  validatePhoneE164,
  buildE164Phone,
  validatePhoneWithCountryCode,
} from './validation';
export {
  DEFAULT_CURRENCY,
  formatHotelPrice,
  formatHotelDate,
  getNightsBetweenDates,
} from './hotelUtils';
export { getHotelStayNights } from './dateHelpers';
export { resolveHotelImageUrl } from './imageUtils';

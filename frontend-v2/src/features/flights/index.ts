/**
 * Flight booking feature module
 *
 * This module contains:
 * - Search components (FlightSearchBar)
 * - Results components (FlightResults, FlightCard)
 * - Filter components (FlightFiltersDialog)
 * - Pages (FlightSearchPage)
 */

// Export components
export { FlightSearchBar } from './components/FlightSearchBar';
export { FlightSearchBarV2 } from './components/FlightSearchBarV2';
export { FlightResults } from './components/FlightResults';
export { FlightCard } from './components/FlightCard';
export { FlightFiltersDialog } from './components/FlightFiltersDialog';
export { FareRules } from './components/FareRules';

// Export pages
export { FlightSearchPage } from './pages/FlightSearchPage';
export { FlightDetailsPage } from './pages/FlightDetailsPage';
export { PassengerInfoPage } from './pages/PassengerInfoPage';
export { ReviewBookingPage } from './pages/ReviewBookingPage';
export { PaymentPage } from './pages/PaymentPage';
export { ConfirmationPage } from './pages/ConfirmationPage';
export { FlightBookingDetailsPage } from './pages/FlightBookingDetailsPage.tsx';

import { Routes, Route, Navigate, Outlet } from 'react-router-dom';

import { useAppSelector } from '@/store';
import { selectIsAuthenticated } from '@/store/slices/authSlice';
import { ROUTES, PublicRoute, toRelativePath } from '@/features/routing';
import { PublicChatPostAuthConversionTracker } from '@/features/chat/components/PublicChatPostAuthConversionTracker';
import { PublicChatRouteGate } from '@/features/chat/components/PublicChatRouteGate';

// Pages
import { PublicLandingPage, HomePage } from '@/features/landing';
import { ForgotPasswordPage, ResetPasswordPage, CompleteRegistrationPage } from '@/features/auth';
import { LayoutNoChat, LayoutWithChat, PublicChatWithContentLayout } from '@/components/layout';
import { ProfilePage } from '@/features/profile';
import {
  ItineraryPage,
  ItinerariesListPage,
  ItineraryFlightBookingsListPage,
  ItineraryHotelBookingsListPage,
} from '@/features/itinerary';
import {
  FlightSearchPage,
  FlightDetailsPage,
  PassengerInfoPage,
  ReviewBookingPage,
  PaymentPage,
  ConfirmationPage,
  FlightBookingDetailsPage,
} from '@/features/flights';
import {
  AdminBookingsPage,
  AdminDiscountBatchDetailPage,
  AdminDiscountsPage,
  AdminFlightBookingDetailPage,
  AdminHotelBookingDetailPage,
} from '@/features/admin';
import {
  HotelSearchPage,
  HotelDetailPage,
  GuestInfoPage,
  HotelReviewBookingPage,
  HotelPaymentPage,
  HotelConfirmationPage,
  HotelBookingDetailsPage,
} from '@/features/hotels';
import {
  OnboardingRouter,
  OnboardingScreen1,
  OnboardingScreen2,
  OnboardingScreen3,
} from '@/features/onboarding';
/**
 * Protected layout route – redirects to landing if not authenticated
 */
function ProtectedRoute() {
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  if (!isAuthenticated) return <Navigate to="/" replace />;
  return <Outlet />;
}

/**
 * Main App component with routing
 */
function App() {
  return (
    <>
      <PublicChatPostAuthConversionTracker />
      <Routes>
        {/* Landing page (default) */}
        <Route
          path="/"
          element={
            <PublicRoute>
              <PublicLandingPage />
            </PublicRoute>
          }
        />
        {/* Campaign landing page by slug */}
        <Route
          path="/l/:slug"
          element={<PublicLandingPage />}
        />

        {/* Pre-signup onboarding wizard (accessible to guests and authenticated users) */}
        <Route path={toRelativePath(ROUTES.ONBOARDING)} element={<OnboardingRouter />} />
        <Route
          path={toRelativePath(ROUTES.ONBOARDING_WELCOME)}
          element={<OnboardingScreen1 />}
        />
        <Route
          path={toRelativePath(ROUTES.ONBOARDING_LOCATION)}
          element={<OnboardingScreen2 />}
        />
        <Route
          path={toRelativePath(ROUTES.ONBOARDING_TRIP)}
          element={<OnboardingScreen3 />}
        />

        {/* Password reset flows - separate pages */}
        <Route
          path="/forgot-password"
          element={
            <PublicRoute>
              <ForgotPasswordPage />
            </PublicRoute>
          }
        />
        <Route
          path="/reset-password"
          element={
            <PublicRoute>
              <ResetPasswordPage />
            </PublicRoute>
          }
        />
        <Route
          path={toRelativePath(ROUTES.COMPLETE_REGISTRATION)}
          element={
            <PublicRoute>
              <CompleteRegistrationPage />
            </PublicRoute>
          }
        />

        <Route
          path={toRelativePath(ROUTES.PUBLIC_CHAT)}
          element={
            <PublicRoute>
              <PublicChatRouteGate>
                <PublicChatWithContentLayout />
              </PublicChatRouteGate>
            </PublicRoute>
          }
        >
          <Route index element={null} />
          <Route path="itinerary" element={<ItineraryPage />} />
          <Route path="itinerary/:id" element={<ItineraryPage />} />
          <Route path="flights/search" element={<FlightSearchPage />} />
          <Route path="hotels/search" element={<HotelSearchPage />} />
        </Route>

        {/* Protected routes */}
        <Route element={<ProtectedRoute />}>
          {/* Home: same sections as landing — no marketing DOM ids */}
          <Route path={toRelativePath(ROUTES.HOME)} element={<HomePage />} />

          {/* Chat + 2-column: LayoutWithChat owns view (chat = standalone, itinerary/flights/hotels = 2-column) */}
          <Route element={<LayoutWithChat />}>
            <Route path="chat" element={null} />
            <Route path="itinerary/:id" element={<ItineraryPage />} />
            <Route
              path="itinerary/:id/bookings/flights"
              element={<ItineraryFlightBookingsListPage />}
            />
            <Route
              path="itinerary/:id/bookings/hotels"
              element={<ItineraryHotelBookingsListPage />}
            />
            <Route path="itinerary" element={<ItineraryPage />} />
            <Route path="flights/search" element={<FlightSearchPage />} />
            <Route path="flights/details/:fareSourceCode" element={<FlightDetailsPage />} />
            <Route path="flights/passenger-info" element={<PassengerInfoPage />} />
            <Route path="flights/review-booking" element={<ReviewBookingPage />} />
            <Route path="flights/payment/:bookingRef" element={<PaymentPage />} />
            <Route path="flights/payment" element={<PaymentPage />} />
            <Route path="flights/bookings/:bookingRef" element={<FlightBookingDetailsPage />} />
            <Route path="flights/confirmation" element={<ConfirmationPage />} />
            <Route path="hotels/search" element={<HotelSearchPage />} />
            <Route path="hotels/rooms/:tokenId" element={<HotelDetailPage />} />
            <Route path="hotels/guest-info" element={<GuestInfoPage />} />
            <Route path="hotels/review-booking" element={<HotelReviewBookingPage />} />
            <Route path="hotels/payment/:bookingRef" element={<HotelPaymentPage />} />
            <Route path="hotels/payment" element={<HotelPaymentPage />} />
            <Route path="hotels/bookings/:bookingRef" element={<HotelBookingDetailsPage />} />
            <Route path="hotels/confirmation" element={<HotelConfirmationPage />} />
          </Route>

          {/* No chat: profile, itineraries list, itinerary view, admin */}
          <Route element={<LayoutNoChat />}>
            <Route path="profile" element={<ProfilePage />} />
            <Route path="itineraries" element={<ItinerariesListPage />} />
            <Route path="itineraries/:id" element={<ItineraryPage />} />
            <Route
              path="itineraries/:id/bookings/flights"
              element={<ItineraryFlightBookingsListPage />}
            />
            <Route
              path="itineraries/:id/bookings/hotels"
              element={<ItineraryHotelBookingsListPage />}
            />
            <Route path="admin/bookings" element={<AdminBookingsPage />} />
            <Route path="admin/bookings/flight/:voyaBookingReference" element={<AdminFlightBookingDetailPage />} />
            <Route path="admin/bookings/hotel/:voyaBookingReference" element={<AdminHotelBookingDetailPage />} />
            <Route path="admin/discounts" element={<AdminDiscountsPage />} />
            <Route path="admin/discounts/:batchId" element={<AdminDiscountBatchDetailPage />} />
          </Route>
        </Route>

        {/* Catch all - redirect to landing */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}

export default App;

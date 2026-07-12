// Base API
export { baseApi } from './baseApi';

// Strapi (headless CMS — landing page)
export { strapiApi, encodeStrapi5Populate, useGetLandingPageQuery } from './strapiApi';

// Auth API
export { authApi } from './authApi';
export {
  useCheckEmailMutation,
  useRegisterMutation,
  useCompleteRegistrationMutation,
  useLoginMutation,
  useGoogleAuthMutation,
  useForgotPasswordMutation,
  useValidateResetTokenMutation,
  useValidateRegistrationTokenMutation,
  useResetPasswordMutation,
  useRefreshTokenMutation,
  useLogoutMutation,
  useGetGoogleConfigQuery,
} from './authApi';

// Users API
export { usersApi } from './usersApi';
export {
  useGetMeQuery,
  useUpdateMeMutation,
  useChangePasswordMutation,
  useGetSessionsQuery,
  useDeleteSessionMutation,
  useLogoutAllSessionsMutation,
  useGetPassengersQuery,
  useLazyGetPassengersQuery,
  useGetPassengerQuery,
  useLazyGetPassengerQuery,
  useCreatePassengerMutation,
  useUpdatePassengerMutation,
  useDeletePassengerMutation,
} from './usersApi';

// Chat API
export { chatApi } from './chatApi';
export {
  useGetFrontendConfigQuery,
  useSendMessageMutation,
  useSendPublicMessageMutation,
  useRefreshPublicPlacesSessionTokenMutation,
  useGetChatHistoryQuery,
  useGetLatestChatQuery,
  useClearChatMutation,
  useClearLatestChatMutation,
  useListConversationsQuery,
  useCreateConversationMutation,
  useRenameConversationMutation,
  useDeleteConversationMutation,
  useSubmitFeedbackMutation,
  useClaimGuestChatMutation,
} from './chatApi';

// Flights API
export { flightsApi } from './flightsApi';
export {
  useSearchFlightsQuery,
  useLazySearchFlightsQuery,
  useSelectFlightMutation,
  useRevalidateFlightMutation,
  useGetFareRulesMutation,
  useGetFlightSessionQuery,
  useBookFlightFromSessionMutation,
  useBookFlightMutation,
  useGetMyBookingsQuery,
  useGetTripDetailsMutation,
  useSearchRedirectMutation,
  useSearchAirportsQuery,
  useResolveAirportQuery,
  useLazyResolveAirportQuery,
} from './flightsApi';

// Hotels API
export { hotelsApi } from './hotelsApi';
export {
  useSearchHotelsQuery,
  useLazySearchHotelsQuery,
  useGetMoreResultsMutation,
  useGetRoomRatesMutation,
  useGetRateRulesMutation,
  useGetHotelSessionQuery,
  useBookHotelMutation,
  useGetHotelBookingDetailsMutation,
  useGetHotelTripDetailsMutation,
  useExchangeHotelBookingTokenMutation,
  useSelectHotelMutation,
  useGetMyHotelBookingsQuery,
} from './hotelsApi';

// Payments API (booking expiry only; Revolut is in revolutPaymentsApi)
export { paymentsApi } from './paymentsApi';
export { useCheckBookingExpiryMutation } from './paymentsApi';

// Revolut Payments API
export { revolutPaymentsApi } from './revolutPaymentsApi';
export {
  useCreateRevolutOrderMutation,
  useGetExistingRevolutOrderQuery,
  useLazyGetExistingRevolutOrderQuery,
  useGetRevolutTransactionQuery,
  useLazyGetRevolutTransactionQuery,
  useGetRevolutTransactionsByBookingQuery,
} from './revolutPaymentsApi';

/**
 * Hotel trip booking confirmation UI — matches Paula / Figma "Template - Side Sheet" (node 809:90374).
 * Presentational only; data is supplied via props. Subcomponents live alongside this file.
 */
import { Box, Stack } from '@mantine/core';

import type {
  HotelGuestPassengerRow,
  HotelNextStepItem,
} from '@/features/hotels/utils/hotelBookingDetailsUtils';

import { HotelBookingDetailsPanelConfirmationRow } from './HotelBookingDetailsPanelConfirmationRow';
import { HotelBookingDetailsPanelGuestsSection } from './HotelBookingDetailsPanelGuestsSection';
import { HotelBookingDetailsPanelHotelCard } from './HotelBookingDetailsPanelHotelCard';
import { HotelBookingDetailsPanelNextStepsSection } from './HotelBookingDetailsPanelNextStepsSection';
import { HotelBookingDetailsPanelPaymentSection } from './HotelBookingDetailsPanelPaymentSection';
import { HotelBookingDetailsPanelSuccessHeader } from './HotelBookingDetailsPanelSuccessHeader';

export type { HotelGuestPassengerRow, HotelNextStepItem };

export interface HotelBookingDetailsPanelProps {
  headlineCity: string;
  confirmationEmail?: string | null;
  /** Router path for primary CTA (e.g. /itinerary). If omitted, button is disabled. */
  viewItineraryTo?: string;
  onShareReservation?: () => void;
  onDownloadInvoice?: () => void;
  destinationTitle: string;
  stayDateLine: string;
  hotelImageUrls: string[];
  /** City for Places fallback (same as profile / search cards). */
  hotelCity?: string | null;
  hotelName: string;
  addressLine: string;
  showOnMapHref?: string | null;
  hotelDescription?: string | null;
  nightsAdultsLine: string;
  roomTypeName: string;
  roomAmenityChip?: string | null;
  reservationCode: string;
  guests: HotelGuestPassengerRow[];
  paymentMethodLabel: string;
  paymentTimestamp: string;
  paymentAmountFormatted: string;
  paymentApproved?: boolean;
  showPaymentSection?: boolean;
  hotelWebsiteUrl?: string | null;
  onGoToHotelWebsite?: () => void;
  nextStepsItems: HotelNextStepItem[];
  /** View itinerary / Share / Download row. Off by default for /hotels/confirmation and /hotels/bookings/:ref. */
  showPrimaryBookingActions?: boolean;
}

export function HotelBookingDetailsPanel({
  headlineCity,
  confirmationEmail,
  viewItineraryTo,
  onShareReservation,
  onDownloadInvoice,
  destinationTitle,
  stayDateLine,
  hotelImageUrls,
  hotelCity,
  hotelName,
  addressLine,
  showOnMapHref,
  hotelDescription,
  nightsAdultsLine,
  roomTypeName,
  roomAmenityChip,
  reservationCode,
  guests,
  paymentMethodLabel,
  paymentTimestamp,
  paymentAmountFormatted,
  paymentApproved = false,
  showPaymentSection = true,
  hotelWebsiteUrl,
  onGoToHotelWebsite,
  nextStepsItems,
  showPrimaryBookingActions = false,
}: HotelBookingDetailsPanelProps) {
  return (
    <Box
      py="md"
      style={{
        backgroundColor: 'white',
        width: '100%',
        overflow: 'hidden',
        borderRadius: 8,
        boxShadow: 'var(--mantine-shadow-sm)',
      }}
    >
      <Stack
        gap={32}
        pb="md"
        align="stretch"
        style={{
          maxHeight: 'calc(100vh - 120px)',
          overflowY: 'auto',
        }}
      >
        <HotelBookingDetailsPanelSuccessHeader headlineCity={headlineCity} />

        <HotelBookingDetailsPanelConfirmationRow
          confirmationEmail={confirmationEmail}
          viewItineraryTo={viewItineraryTo}
          onShareReservation={onShareReservation}
          onDownloadInvoice={onDownloadInvoice}
          showPrimaryBookingActions={showPrimaryBookingActions}
        />

        <HotelBookingDetailsPanelHotelCard
          destinationTitle={destinationTitle}
          stayDateLine={stayDateLine}
          hotelImageUrls={hotelImageUrls}
          hotelCity={hotelCity}
          hotelName={hotelName}
          addressLine={addressLine}
          showOnMapHref={showOnMapHref}
          hotelDescription={hotelDescription}
          nightsAdultsLine={nightsAdultsLine}
          roomTypeName={roomTypeName}
          roomAmenityChip={roomAmenityChip}
          reservationCode={reservationCode}
        />

        <HotelBookingDetailsPanelGuestsSection guests={guests} />

        {showPaymentSection ? (
          <HotelBookingDetailsPanelPaymentSection
            paymentMethodLabel={paymentMethodLabel}
            paymentTimestamp={paymentTimestamp}
            paymentAmountFormatted={paymentAmountFormatted}
            paymentApproved={paymentApproved}
          />
        ) : null}

        <HotelBookingDetailsPanelNextStepsSection
          nextStepsItems={nextStepsItems}
          hotelWebsiteUrl={hotelWebsiteUrl}
          onGoToHotelWebsite={onGoToHotelWebsite}
        />
      </Stack>
    </Box>
  );
}

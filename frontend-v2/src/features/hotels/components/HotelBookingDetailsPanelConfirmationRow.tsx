import { Link } from 'react-router-dom';
import { Button, Group, Stack, Text, Tooltip } from '@mantine/core';
import { Download, Eye, Share2 } from 'lucide-react';

import {
  HOTEL_BOOKING_DETAILS_FF,
  hotelBookingDetailsPalette as palette,
} from './hotelBookingDetailsPanel.theme';

export interface HotelBookingDetailsPanelConfirmationRowProps {
  confirmationEmail?: string | null;
  viewItineraryTo?: string;
  onShareReservation?: () => void;
  onDownloadInvoice?: () => void;
  showPrimaryBookingActions?: boolean;
}

const filledButtonStyle: React.CSSProperties = {
  backgroundColor: palette.base,
  color: 'white',
};

const outlineButtonStyle: React.CSSProperties = {
  borderColor: palette.base,
  color: palette.text,
};

const sharedButtonRoot: React.CSSProperties = {
  paddingLeft: 16,
  paddingRight: 24,
  paddingTop: 10,
  paddingBottom: 10,
  fontFamily: HOTEL_BOOKING_DETAILS_FF,
  fontSize: 14,
  fontWeight: 600,
  letterSpacing: '0.1px',
};

export function HotelBookingDetailsPanelConfirmationRow({
  confirmationEmail,
  viewItineraryTo,
  onShareReservation,
  onDownloadInvoice,
  showPrimaryBookingActions = false,
}: HotelBookingDetailsPanelConfirmationRowProps) {
  return (
    <Stack gap={32} style={{ width: '100%' }}>
      <Stack gap={0} style={{ width: '100%' }}>
        <Text
          component="span"
          py={10}
          style={{
            margin: 0,
            display: 'block',
            fontFamily: HOTEL_BOOKING_DETAILS_FF,
            fontSize: '1rem',
            fontWeight: 600,
            lineHeight: '20px',
            color: palette.text,
          }}
        >
          {confirmationEmail
            ? `Your confirmation has been sent to ${confirmationEmail}.`
            : 'Your confirmation has been sent to your email.'}
        </Text>
      </Stack>

      {showPrimaryBookingActions ? (
        <Group wrap="wrap" gap={24} align="center">
          {viewItineraryTo ? (
            <Button
              component={Link}
              to={viewItineraryTo}
              size="sm"
              radius={9999}
              tt="none"
              leftSection={<Eye size={18} />}
              styles={{ root: { ...sharedButtonRoot, ...filledButtonStyle } }}
            >
              View itinerary
            </Button>
          ) : (
            <Button
              size="sm"
              radius={9999}
              tt="none"
              disabled
              leftSection={<Eye size={18} />}
              styles={{ root: { ...sharedButtonRoot, ...filledButtonStyle } }}
            >
              View itinerary
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            radius={9999}
            tt="none"
            onClick={() => onShareReservation?.()}
            leftSection={<Share2 size={18} color={palette.base} />}
            styles={{ root: { ...sharedButtonRoot, ...outlineButtonStyle } }}
          >
            Share reservation
          </Button>
          {onDownloadInvoice ? (
            <Button
              variant="outline"
              size="sm"
              radius={9999}
              tt="none"
              onClick={() => onDownloadInvoice()}
              leftSection={<Download size={18} color={palette.base} />}
              styles={{ root: { ...sharedButtonRoot, ...outlineButtonStyle } }}
            >
              Download invoice
            </Button>
          ) : (
            <Tooltip label="Invoice download is not available yet">
              <span>
                <Button
                  variant="outline"
                  size="sm"
                  radius={9999}
                  tt="none"
                  disabled
                  leftSection={<Download size={18} color={palette.base} />}
                  styles={{ root: { ...sharedButtonRoot, ...outlineButtonStyle } }}
                >
                  Download invoice
                </Button>
              </span>
            </Tooltip>
          )}
        </Group>
      ) : null}
    </Stack>
  );
}

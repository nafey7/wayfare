import { useEffect, useState } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import {
  Alert,
  Anchor,
  Box,
  Button,
  Card,
  Container,
  Divider,
  Group,
  Loader,
  Modal,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { ArrowLeft, Hotel as HotelIcon, RefreshCw } from 'lucide-react';
import { useAppSelector } from '@/store/hooks';
import { selectCurrentUser } from '@/store/slices/authSlice';
import {
  useGetAdminBookingEventByReferenceQuery,
  useAdminRetryBookingMutation,
} from '@/api/adminBookingsApi';
import { useGetHotelBookingDetailsMutation } from '@/api/hotelsApi';
import { showErrorToastFromError, showSuccessToast } from '@/utils/toast';
import type { HotelBookingDetailsResponse } from '@/types/hotels';

/**
 * Admin-only page: view hotel booking details by VOYA reference.
 */
export function AdminHotelBookingDetailPage() {
  const { voyaBookingReference } = useParams<{ voyaBookingReference: string }>();
  const navigate = useNavigate();
  const user = useAppSelector(selectCurrentUser);
  const [detail, setDetail] = useState<HotelBookingDetailsResponse | null>(null);
  const [detailError, setDetailError] = useState(false);
  const [retryDialogOpen, setRetryDialogOpen] = useState(false);

  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin';

  const { data: bookingEvent, refetch: refetchEvent } =
    useGetAdminBookingEventByReferenceQuery(voyaBookingReference ?? '', {
      skip: !voyaBookingReference || !isAdmin,
    });

  const [getHotelBookingDetails, { isLoading: isLoadingDetails }] =
    useGetHotelBookingDetailsMutation();

  const [retryBooking, { isLoading: isRetrying }] =
    useAdminRetryBookingMutation();

  useEffect(() => {
    if (user != null && !isAdmin) {
      navigate('/home', { replace: true });
    }
  }, [user, isAdmin, navigate]);

  useEffect(() => {
    if (
      !voyaBookingReference ||
      !isAdmin ||
      !bookingEvent?.hotelReferenceNumber ||
      !bookingEvent?.externalBookingReference
    ) {
      setDetail(null);
      setDetailError(false);
      return;
    }
    setDetailError(false);
    getHotelBookingDetails({
      supplierConfirmationNum: bookingEvent.externalBookingReference,
      referenceNum: bookingEvent.hotelReferenceNumber,
    })
      .unwrap()
      .then((res) => setDetail(res ?? null))
      .catch(() => {
        setDetail(null);
        setDetailError(true);
      });
  }, [
    voyaBookingReference,
    isAdmin,
    bookingEvent?.hotelReferenceNumber,
    bookingEvent?.externalBookingReference,
    getHotelBookingDetails,
  ]);

  const handleRetry = async () => {
    if (!bookingEvent?.id) return;
    try {
      await retryBooking({ bookingEventId: bookingEvent.id }).unwrap();
      showSuccessToast('Retry completed successfully.');
      const { data: updated } = await refetchEvent();
      if (
        updated?.externalBookingReference &&
        updated?.hotelReferenceNumber
      ) {
        const res = await getHotelBookingDetails({
          supplierConfirmationNum: updated.externalBookingReference,
          referenceNum: updated.hotelReferenceNumber,
        }).unwrap();
        setDetail(res ?? null);
      }
    } catch (err) {
      showErrorToastFromError(err, 'Retry failed.');
    }
  };

  const bookingDetailsStatus =
    detail?.bookingDetails &&
    (detail.bookingDetails['status'] ?? detail.bookingDetails['Status']);
  const isConfirmed =
    bookingDetailsStatus != null &&
    String(bookingDetailsStatus).toLowerCase().trim() === 'confirmed';

  const canRetry =
    bookingEvent?.eventType === 'HOTEL' &&
    bookingEvent?.action === 'BOOKED' &&
    Boolean(bookingEvent?.id) &&
    !isConfirmed;

  const hasHotelRef = Boolean(bookingEvent?.hotelReferenceNumber);
  const bookingDetailsApiCompleted = !hasHotelRef || !isLoadingDetails;
  const showRetryCard = canRetry && bookingDetailsApiCompleted;

  if (user == null || !isAdmin) return null;

  if (!voyaBookingReference) {
    return (
      <Container size="md" py="lg">
        <Alert color="yellow">Missing VOYA booking reference.</Alert>
        <Button component={Link} to="/admin/bookings" leftSection={<ArrowLeft size={18} />} mt="md" tt="none">
          Back to bookings
        </Button>
      </Container>
    );
  }

  const bookingDetails = detail?.bookingDetails ?? {};

  return (
    <Container size="lg" py="lg">
      <Group justify="space-between" align="flex-start" gap="md" mb="md" wrap="wrap">
        <Button
          component={Link}
          to="/admin/bookings"
          leftSection={<ArrowLeft size={18} />}
          variant="subtle"
          tt="none"
        >
          Back to bookings
        </Button>
        <Group gap="md" align="center" wrap="wrap">
          <Anchor
            href="https://travelnext.biz/agents/bookingQueue"
            target="_blank"
            rel="noopener noreferrer"
            size="sm"
            fw={500}
          >
            Bookings overview
          </Anchor>
          <Anchor
            href="https://travelnext.biz/agents/ledgerStatement"
            target="_blank"
            rel="noopener noreferrer"
            size="sm"
            fw={500}
          >
            Account statement
          </Anchor>
          {showRetryCard && (
            <>
              <Button
                tt="none"
                fw={600}
                leftSection={isRetrying ? <Loader size={16} color="white" /> : <RefreshCw size={18} />}
                onClick={() => setRetryDialogOpen(true)}
                disabled={isRetrying}
              >
                {isRetrying ? 'Retrying…' : 'Retry'}
              </Button>
              <Modal
                opened={retryDialogOpen}
                onClose={() => !isRetrying && setRetryDialogOpen(false)}
                title="Confirm retry"
                centered
              >
                <Stack gap="md">
                  <Text size="sm">
                    Retry this hotel booking? The booking will be retried with the supplier. This
                    action cannot be undone.
                  </Text>
                  <Group justify="flex-end" gap="xs">
                    <Button variant="subtle" tt="none" onClick={() => setRetryDialogOpen(false)} disabled={isRetrying}>
                      Cancel
                    </Button>
                    <Button
                      tt="none"
                      fw={600}
                      onClick={() => {
                        setRetryDialogOpen(false);
                        void handleRetry();
                      }}
                      disabled={isRetrying}
                    >
                      Retry
                    </Button>
                  </Group>
                </Stack>
              </Modal>
            </>
          )}
        </Group>
      </Group>

      {bookingEvent && (!hasHotelRef || detailError) && (
        <Card withBorder padding="lg" mb="lg" style={{ border: '2px solid var(--mantine-color-brand-6)' }}>
          <Title order={4} fw={700} mb="xs">
            Booking event
          </Title>
          <Divider mb="sm" />
          <Stack gap="xs">
            <AttrRow label="VOYA booking reference" value={bookingEvent.voyaBookingReference} />
            <AttrRow label="External reference" value={bookingEvent.externalBookingReference} />
            <AttrRow label="Hotel reference number" value={bookingEvent.hotelReferenceNumber} />
            <AttrRow label="Status" value="Not Confirmed" />
            <AttrRow label="Event type" value={bookingEvent.eventType} />
            <AttrRow
              label="Timestamp"
              value={
                bookingEvent.timestamp ? new Date(bookingEvent.timestamp).toLocaleString() : undefined
              }
            />
            <AttrRow label="User ID" value={bookingEvent.userId} />
            <AttrRow label="User" value={bookingEvent.userDisplayName} />
            <AttrRow label="Contact email" value={bookingEvent.contactEmail} />
          </Stack>
        </Card>
      )}

      {!hasHotelRef && bookingEvent?.eventType === 'HOTEL' && (
        <Alert color="blue" mb="md">
          Hotel reference number is missing. Booking details API is only called when the event has a
          hotel reference number (from a successful book response). Use Retry if the book had failed
          earlier.
        </Alert>
      )}

      {hasHotelRef && (
        <>
          {isLoadingDetails ? (
            <Group justify="center" py="lg">
              <Loader />
            </Group>
          ) : detailError ? (
            <Alert color="red" mt="md">
              Failed to load hotel booking details.
            </Alert>
          ) : detail && Object.keys(bookingDetails).length > 0 ? (
            <Card withBorder padding="lg" mb="lg">
              <Title order={4} fw={700} mb="xs">
                <HotelIcon size={20} style={{ marginRight: 8, verticalAlign: 'middle' }} />
                Hotel booking details
              </Title>
              <Divider mb="sm" />
              <BookingDetailsDisplay details={bookingDetails} />
            </Card>
          ) : null}
        </>
      )}

      {bookingEvent && !bookingEvent.voyaBookingReference && (
        <Alert color="yellow">Booking event not found for this reference.</Alert>
      )}
    </Container>
  );
}

function AttrRow({
  label,
  value,
}: {
  label: string;
  value: string | number | undefined | null;
}) {
  if (value == null || value === '') return null;
  return (
    <Group gap="xs" align="baseline" wrap="wrap">
      <Text size="sm" c="dimmed" style={{ minWidth: 180 }}>
        {label}
      </Text>
      <Text size="md" fw={600}>
        {String(value)}
      </Text>
    </Group>
  );
}

/** Prefer first non-empty value (camelCase/snake_case agnostic). */
function pickStr(details: Record<string, unknown>, ...keys: string[]): string | null {
  for (const k of keys) {
    const v = details[k];
    if (v != null && v !== '') return String(v);
  }
  return null;
}

function formatPrice(amount: unknown, currency: string): string {
  if (amount == null) return '—';
  const n = typeof amount === 'number' ? amount : parseFloat(String(amount));
  return Number.isFinite(n) ? `${currency} ${n.toFixed(2)}` : String(amount);
}

function BookingDetailsDisplay({ details }: { details: Record<string, unknown> }) {
  const hotelName = pickStr(details, 'hotel_name', 'hotelName', 'name', 'Name') ?? '—';
  const address = pickStr(details, 'address');
  const city = pickStr(details, 'city');
  const country = pickStr(details, 'country');
  const postalCode = pickStr(details, 'postalCode', 'postal_code');
  const rating = details.hotel_rating ?? details.rating;
  const imageUrl = pickStr(details, 'image');
  const email = pickStr(details, 'email', 'customer_email', 'customerEmail');
  const phone = pickStr(details, 'phone', 'customer_phone', 'customerPhone');

  const checkIn = pickStr(details, 'check_in', 'checkIn', 'check_in_date', 'checkInDate') ?? '—';
  const checkOut = pickStr(details, 'check_out', 'checkOut', 'check_out_date', 'checkOutDate') ?? '—';
  const daysStr = pickStr(details, 'days');
  const currency = (details.currency ?? details.Currency ?? 'USD') as string;
  const totalPrice = details.total_price ?? details.totalPrice ?? details.NetPrice ?? details.netPrice;
  const originalPrice =
    details.original_net_price ??
    details.originalNetPrice ??
    details.original_total_price ??
    details.originalTotalPrice;
  const platformFeePct = details.platform_fee_percentage ?? details.platformFeePercentage;
  const fareType = pickStr(details, 'fare_type', 'fareType');
  const cancellationPolicy = pickStr(details, 'cancellation_policy', 'cancellationPolicy');
  const status = pickStr(details, 'status', 'Status') ?? '—';
  const supplierConfirmationNum = pickStr(details, 'supplierConfirmationNum', 'supplier_confirmation_num');
  const referenceNum = pickStr(details, 'referenceNum', 'reference_num');
  const clientRefNum = pickStr(details, 'clientRefNum', 'client_ref_num');
  const bookingDateTime = pickStr(details, 'booking_date_time', 'bookingDateTime');
  const productId = pickStr(details, 'productId', 'product_id');

  const rooms = details.rooms as Array<Record<string, unknown>> | undefined;
  const guests = details.guests as Array<Record<string, unknown>> | undefined;

  return (
    <Stack gap="lg">
      <Box>
        <Text size="sm" c="dimmed" mb="xs">
          Hotel
        </Text>
        <Group gap="md" wrap="wrap" align="flex-start">
          {imageUrl && (
            <Box
              component="img"
              src={imageUrl}
              alt=""
              style={{ width: 120, height: 90, objectFit: 'cover', borderRadius: 4 }}
            />
          )}
          <Box style={{ flex: 1, minWidth: 200 }}>
            <Text size="md" fw={600}>
              {hotelName}
            </Text>
            {rating != null && (
              <Text size="sm" c="dimmed">
                Rating: {String(rating)}
              </Text>
            )}
            {address && (
              <Text size="sm" c="dimmed" mt={2}>
                {address}
              </Text>
            )}
            {(city ?? country) && (
              <Text size="sm" c="dimmed">
                {[city, postalCode, country].filter(Boolean).join(', ')}
              </Text>
            )}
            {email && (
              <Anchor href={`mailto:${email}`} size="sm" display="block" mt={2}>
                {email}
              </Anchor>
            )}
            {phone && (
              <Anchor href={`tel:${phone}`} size="sm">
                {phone}
              </Anchor>
            )}
          </Box>
        </Group>
      </Box>

      <Divider />

      <Stack gap="xs">
        <Text size="sm" c="dimmed" mb={4}>
          Stay & pricing
        </Text>
        <AttrRow label="Check-in" value={checkIn} />
        <AttrRow label="Check-out" value={checkOut} />
        {daysStr && <AttrRow label="Nights" value={daysStr} />}
        <AttrRow label="Status" value={status} />
        {originalPrice != null && (
          <AttrRow label="Price (before platform fee)" value={formatPrice(originalPrice, currency)} />
        )}
        {totalPrice != null && (
          <AttrRow
            label={originalPrice != null ? 'Total (with platform fee)' : 'Total'}
            value={formatPrice(totalPrice, currency)}
          />
        )}
        {platformFeePct != null && (
          <AttrRow label="Platform fee" value={`${String(platformFeePct)}%`} />
        )}
        {fareType && <AttrRow label="Fare type" value={fareType} />}
        {cancellationPolicy && (
          <Box mt={4}>
            <Text size="sm" c="dimmed">
              Cancellation policy
            </Text>
            <Text size="sm" style={{ whiteSpace: 'pre-wrap' }}>
              {cancellationPolicy}
            </Text>
          </Box>
        )}
      </Stack>

      <Divider />

      <Stack gap="xs">
        <Text size="sm" c="dimmed" mb={4}>
          References
        </Text>
        {supplierConfirmationNum && <AttrRow label="Supplier confirmation" value={supplierConfirmationNum} />}
        {referenceNum && <AttrRow label="Reference number" value={referenceNum} />}
        {clientRefNum && <AttrRow label="Client ref" value={clientRefNum} />}
        {productId && <AttrRow label="Product ID" value={productId} />}
        {bookingDateTime && <AttrRow label="Booking date/time" value={bookingDateTime} />}
      </Stack>

      {Array.isArray(rooms) && rooms.length > 0 && (
        <>
          <Divider />
          <Box>
            <Text size="sm" c="dimmed" mb="xs">
              Rooms
            </Text>
            {rooms.map((room, idx) => {
              const name = String(room.name ?? room.roomName ?? `Room ${idx + 1}`);
              const desc = room.description ?? room.roomDescription;
              const board = room.boardType ?? room.board_type;
              const pax = room.paxDetails ?? room.pax_details;
              const paxNames = Array.isArray((pax as Record<string, unknown>)?.name)
                ? ((pax as Record<string, unknown>).name as string[]).join(', ')
                : null;
              return (
                <Box
                  key={idx}
                  py="xs"
                  px="md"
                  mb="xs"
                  style={{ backgroundColor: 'var(--mantine-color-gray-0)', borderRadius: 4 }}
                >
                  <Text size="md" fw={600}>
                    {name}
                  </Text>
                  {desc != null && desc !== '' && (
                    <Text size="sm" c="dimmed">
                      {String(desc)}
                    </Text>
                  )}
                  {board != null && board !== '' && (
                    <Text size="sm" c="dimmed">
                      {String(board)}
                    </Text>
                  )}
                  {paxNames && (
                    <Text size="sm" mt={2}>
                      {paxNames}
                    </Text>
                  )}
                </Box>
              );
            })}
          </Box>
        </>
      )}

      {Array.isArray(guests) && guests.length > 0 && (
        <>
          <Divider />
          <Box>
            <Text size="sm" c="dimmed" mb="xs">
              Guests
            </Text>
            {guests.map((g, idx) => {
              const title = String(g.title ?? '');
              const first = String(g.first_name ?? g.firstName ?? '');
              const last = String(g.last_name ?? g.lastName ?? '');
              const roomNum = g.room_number ?? g.roomNumber;
              const full = [title, first, last].filter(Boolean).join(' ') || `Guest ${idx + 1}`;
              return (
                <Text key={idx} size="sm" py={2}>
                  {roomNum != null ? `Room ${roomNum}: ` : ''}
                  {full}
                </Text>
              );
            })}
          </Box>
        </>
      )}
    </Stack>
  );
}

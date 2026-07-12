import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Alert,
  Container,
  Group,
  Loader,
  Pagination,
  Paper,
  ScrollArea,
  Stack,
  Table,
  Text,
  Title,
} from '@mantine/core';
import { useAppSelector } from '@/store/hooks';
import { selectCurrentUser } from '@/store/slices/authSlice';
import { useGetAdminBookingsQuery } from '@/api/adminBookingsApi';

const PAGE_SIZE = 25;

/**
 * Admin-only page: view all booking events in a table.
 */
export function AdminBookingsPage() {
  const navigate = useNavigate();
  const user = useAppSelector(selectCurrentUser);
  const [page, setPage] = useState(1);

  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin';

  useEffect(() => {
    if (user != null && !isAdmin) {
      navigate('/home', { replace: true });
    }
  }, [user, isAdmin, navigate]);

  const offset = (page - 1) * PAGE_SIZE;
  const { data, isLoading, error } = useGetAdminBookingsQuery(
    { limit: PAGE_SIZE, offset },
    { skip: !isAdmin }
  );

  if (user == null) return null;
  if (!isAdmin) return null;

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <Container size="xl" py="lg">
      <Stack gap="md">
        <Title order={1}>All Bookings (Admin)</Title>
        <Text size="sm" c="dimmed">
          Booking events from the database. Sorted by timestamp (newest first).
        </Text>

        {error && (
          <Alert color="red">Failed to load bookings. You may need admin access.</Alert>
        )}

        {isLoading ? (
          <Group justify="center" py="lg">
            <Loader />
          </Group>
        ) : data ? (
          <Stack gap="md">
            <Group justify="flex-end">
              <Pagination value={page} onChange={setPage} total={totalPages} size="sm" />
            </Group>
            <Paper withBorder>
              <ScrollArea>
                <Table striped highlightOnHover style={{ minWidth: 1200 }}>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th
                        style={{
                          position: 'sticky',
                          left: 0,
                          zIndex: 11,
                          backgroundColor: 'var(--mantine-color-body)',
                          boxShadow: '2px 0 4px -2px rgba(0,0,0,0.1)',
                        }}
                      >
                        VOYA Reference
                      </Table.Th>
                      <Table.Th>External Reference</Table.Th>
                      <Table.Th>User email</Table.Th>
                      <Table.Th>Type</Table.Th>
                      <Table.Th>Carrier</Table.Th>
                      <Table.Th>Contact Email</Table.Th>
                      <Table.Th>Timestamp</Table.Th>
                      <Table.Th>Date booked</Table.Th>
                      <Table.Th>Date paid</Table.Th>
                      <Table.Th>Date tickets issued</Table.Th>
                      <Table.Th>Amount</Table.Th>
                      <Table.Th>Payment ID</Table.Th>
                      <Table.Th>Confirmation Email Sent</Table.Th>
                      <Table.Th>PNR</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {data.events.length === 0 ? (
                      <Table.Tr>
                        <Table.Td colSpan={14} ta="center">
                          No booking events found.
                        </Table.Td>
                      </Table.Tr>
                    ) : (
                      data.events.map((ev) => (
                        <Table.Tr key={ev.id}>
                          <Table.Td
                            style={{
                              position: 'sticky',
                              left: 0,
                              zIndex: 1,
                              backgroundColor: 'var(--mantine-color-body)',
                              boxShadow: '2px 0 4px -2px rgba(0,0,0,0.1)',
                            }}
                          >
                            {ev.voyaBookingReference ? (
                              ev.eventType === 'HOTEL' ? (
                                <Link
                                  to={`/admin/bookings/hotel/${encodeURIComponent(ev.voyaBookingReference)}`}
                                  style={{ fontWeight: 500 }}
                                >
                                  {ev.voyaBookingReference}
                                </Link>
                              ) : ev.eventType === 'FLIGHT' ? (
                                <Link
                                  to={`/admin/bookings/flight/${encodeURIComponent(ev.voyaBookingReference)}`}
                                  style={{ fontWeight: 500 }}
                                >
                                  {ev.voyaBookingReference}
                                </Link>
                              ) : (
                                ev.voyaBookingReference
                              )
                            ) : (
                              '—'
                            )}
                          </Table.Td>
                          <Table.Td>{ev.externalBookingReference || '—'}</Table.Td>
                          <Table.Td>{ev.userDisplayName ?? 'Unknown'}</Table.Td>
                          <Table.Td>{ev.eventType}</Table.Td>
                          <Table.Td>{ev.carrierType ?? '—'}</Table.Td>
                          <Table.Td>{ev.contactEmail || '—'}</Table.Td>
                          <Table.Td>
                            {ev.timestamp ? new Date(ev.timestamp).toLocaleString() : '—'}
                          </Table.Td>
                          <Table.Td>
                            {ev.dateBooked ? new Date(ev.dateBooked).toLocaleString() : '—'}
                          </Table.Td>
                          <Table.Td>
                            {ev.datePaid ? new Date(ev.datePaid).toLocaleString() : '—'}
                          </Table.Td>
                          <Table.Td>
                            {ev.dateTicketsIssued
                              ? new Date(ev.dateTicketsIssued).toLocaleString()
                              : '—'}
                          </Table.Td>
                          <Table.Td>
                            {ev.amount != null
                              ? ev.amount.toLocaleString(undefined, {
                                  minimumFractionDigits: 2,
                                  maximumFractionDigits: 2,
                                })
                              : '—'}
                          </Table.Td>
                          <Table.Td>{ev.paymentIntentId || '—'}</Table.Td>
                          <Table.Td>
                            {ev.confirmationEmailSent === true
                              ? 'Yes'
                              : ev.confirmationEmailSent === false
                                ? 'No'
                                : '—'}
                          </Table.Td>
                          <Table.Td>{ev.pnr?.length ? ev.pnr.join(', ') : '—'}</Table.Td>
                        </Table.Tr>
                      ))
                    )}
                  </Table.Tbody>
                </Table>
              </ScrollArea>
            </Paper>
          </Stack>
        ) : null}
      </Stack>
    </Container>
  );
}

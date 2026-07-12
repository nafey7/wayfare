import { useEffect, useState } from 'react';
import { Link as RouterLink, useNavigate, useParams } from 'react-router-dom';
import {
  ActionIcon,
  Alert,
  Box,
  Button,
  Container,
  Group,
  Loader,
  Pagination,
  Paper,
  ScrollArea,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Title,
  Tooltip,
} from '@mantine/core';
import { ArrowLeft, Ban, Download } from 'lucide-react';

import { useAppSelector } from '@/store/hooks';
import { selectCurrentUser } from '@/store/slices/authSlice';
import {
  useGetAdminBatchDetailQuery,
  useDisableAdminDiscountMutation,
  useLazyGetAdminBatchCsvQuery,
} from '@/api/adminDiscountsApi';
import { ROUTES } from '@/features/routing';
import { formatUsdCentsOrDash } from '@/utils/formatCurrency';

const PAGE_SIZE = 50;

const STATUS_OPTIONS = [
  { value: '__all', label: 'All statuses' },
  { value: 'active', label: 'Active' },
  { value: 'reserved', label: 'Reserved' },
  { value: 'used', label: 'Used' },
  { value: 'expired', label: 'Expired' },
  { value: 'disabled', label: 'Disabled' },
];


/**
 * Admin-only: codes in one batch, CSV export, optional disable per code.
 */
export function AdminDiscountBatchDetailPage() {
  const { batchId = '' } = useParams<{ batchId: string }>();
  const navigate = useNavigate();
  const user = useAppSelector(selectCurrentUser);
  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin';

  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('__all');
  const offset = (page - 1) * PAGE_SIZE;

  const { data, isLoading, error, refetch } = useGetAdminBatchDetailQuery(
    {
      batchId,
      status: statusFilter === '__all' ? undefined : statusFilter,
      limit: PAGE_SIZE,
      offset,
    },
    { skip: !isAdmin || !batchId }
  );

  const [disableCode, { isLoading: isDisabling }] =
    useDisableAdminDiscountMutation();
  const [fetchCsv, { isFetching: isCsvLoading }] = useLazyGetAdminBatchCsvQuery();

  useEffect(() => {
    if (user != null && !isAdmin) {
      navigate('/home', { replace: true });
    }
  }, [user, isAdmin, navigate]);

  useEffect(() => {
    setPage(1);
  }, [statusFilter]);

  if (user == null || !isAdmin) {
    return null;
  }

  const handleDownloadCsv = async () => {
    try {
      const blob = await fetchCsv(batchId).unwrap();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `voya-batch-${batchId}.csv`;
      a.rel = 'noopener';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      // surfaced via error state if we add toast; keep minimal
    }
  };

  const handleDisable = async (id: string) => {
    if (!window.confirm('Disable this code? It cannot be redeemed after this.')) {
      return;
    }
    try {
      await disableCode(id).unwrap();
      void refetch();
    } catch {
      void refetch();
    }
  };

  const totalPages = data ? Math.max(1, Math.ceil(data.totalCodes / PAGE_SIZE)) : 1;

  return (
    <Container size="xl" py="lg">
      <Button
        component={RouterLink}
        to={ROUTES.ADMIN_DISCOUNTS}
        leftSection={<ArrowLeft size={18} />}
        variant="subtle"
        tt="none"
        mb="md"
      >
        All batches
      </Button>

      <Title order={1} mb="xs">
        Batch detail
      </Title>
      <Text size="sm" c="dimmed" mb="md" style={{ fontFamily: 'monospace' }}>
        {batchId}
      </Text>

      {error && (
        <Alert color="red" mb="md">
          Failed to load batch (not found or no access).
        </Alert>
      )}

      {isLoading ? (
        <Group justify="center" py="lg">
          <Loader />
        </Group>
      ) : data ? (
        <Stack gap="md">
          <Paper p="md" withBorder>
            <Text fw={600} mb="xs">
              Summary
            </Text>
            <SimpleGrid cols={{ base: 2, sm: 3, md: 4, lg: 6 }} spacing="sm">
              <Text size="sm">
                <strong>Source:</strong> {data.source || '—'}
              </Text>
              <Text size="sm">
                <strong>Total codes:</strong> {data.summary.total}
              </Text>
              <Text size="sm">
                <strong>Active:</strong> {data.summary.active}
              </Text>
              <Text size="sm">
                <strong>Reserved:</strong> {data.summary.reserved}
              </Text>
              <Text size="sm">
                <strong>Used:</strong> {data.summary.used}
              </Text>
              <Text size="sm">
                <strong>Face value total:</strong>{' '}
                {formatUsdCentsOrDash(data.summary.totalAmountCents ?? undefined)}
              </Text>
            </SimpleGrid>
          </Paper>

          <Group gap="md" align="center" wrap="wrap">
            <Select
              label="Status"
              value={statusFilter}
              onChange={(v) => setStatusFilter(v ?? '__all')}
              data={STATUS_OPTIONS}
              size="sm"
              style={{ minWidth: 200 }}
              allowDeselect={false}
            />
            <Button
              variant="outline"
              leftSection={<Download size={18} />}
              onClick={() => void handleDownloadCsv()}
              disabled={isCsvLoading || !batchId}
              tt="none"
            >
              {isCsvLoading ? 'Downloading…' : 'Download CSV'}
            </Button>
          </Group>

          <Group justify="flex-end">
            <Pagination value={page} onChange={setPage} total={totalPages} size="sm" />
          </Group>

          <Paper withBorder>
            <ScrollArea>
              <Table striped highlightOnHover style={{ minWidth: 720 }}>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Code</Table.Th>
                    <Table.Th>Status</Table.Th>
                    <Table.Th style={{ textAlign: 'right' }}>Face value</Table.Th>
                    <Table.Th>Expires</Table.Th>
                    <Table.Th style={{ textAlign: 'right', width: 72 }}>Actions</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {data.codes.map((row) => {
                    const canDisable =
                      row.status === 'active' || row.status === 'reserved';
                    return (
                      <Table.Tr key={row.id}>
                        <Table.Td style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
                          {row.code}
                        </Table.Td>
                        <Table.Td>{row.status}</Table.Td>
                        <Table.Td style={{ textAlign: 'right' }}>
                          {formatUsdCentsOrDash(row.amountCents)}
                        </Table.Td>
                        <Table.Td>
                          {row.expiresAt ? new Date(row.expiresAt).toLocaleString() : '—'}
                        </Table.Td>
                        <Table.Td style={{ textAlign: 'right' }}>
                          {canDisable ? (
                            <Tooltip label="Disable code">
                              <ActionIcon
                                size="md"
                                variant="subtle"
                                color="gray"
                                aria-label="Disable code"
                                disabled={isDisabling}
                                onClick={() => void handleDisable(row.id)}
                              >
                                <Ban size={18} />
                              </ActionIcon>
                            </Tooltip>
                          ) : (
                            <Box ta="right">—</Box>
                          )}
                        </Table.Td>
                      </Table.Tr>
                    );
                  })}
                </Table.Tbody>
              </Table>
            </ScrollArea>
          </Paper>
        </Stack>
      ) : null}
    </Container>
  );
}

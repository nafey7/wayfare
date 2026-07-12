import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Container,
  Group,
  Loader,
  Modal,
  Paper,
  ScrollArea,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { Plus } from 'lucide-react';

import { useAppSelector } from '@/store/hooks';
import { selectCurrentUser } from '@/store/slices/authSlice';
import {
  useListAdminDiscountBatchesQuery,
  useCreateAdminDiscountBatchMutation,
} from '@/api/adminDiscountsApi';
import { adminDiscountBatchDetailPath } from '@/features/routing';
import { formatUsdCentsOrDash } from '@/utils/formatCurrency';

/**
 * Admin-only: list voucher batches, generate new batches (USD), open batch detail.
 */
export function AdminDiscountsPage() {
  const navigate = useNavigate();
  const user = useAppSelector(selectCurrentUser);
  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin';

  const { data, isLoading, error, refetch } = useListAdminDiscountBatchesQuery(
    undefined,
    { skip: !isAdmin }
  );
  const [createBatch, { isLoading: isCreating }] =
    useCreateAdminDiscountBatchMutation();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [countStr, setCountStr] = useState('10');
  const [amountUsdStr, setAmountUsdStr] = useState('50');
  const [source, setSource] = useState('G2A_batch');
  const [prefix, setPrefix] = useState('');
  const [expiresAtLocal, setExpiresAtLocal] = useState('');
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (user != null && !isAdmin) {
      navigate('/home', { replace: true });
    }
  }, [user, isAdmin, navigate]);

  if (user == null || !isAdmin) {
    return null;
  }

  const openDialog = () => {
    setFormError(null);
    setDialogOpen(true);
  };

  const closeDialog = () => {
    setDialogOpen(false);
    setFormError(null);
  };

  const handleCreate = async () => {
    setFormError(null);
    const count = Number.parseInt(countStr, 10);
    const amountUsd = Number.parseFloat(amountUsdStr);
    if (!Number.isFinite(count) || count < 1 || count > 10_000) {
      setFormError('Count must be between 1 and 10,000.');
      return;
    }
    if (!Number.isFinite(amountUsd) || amountUsd <= 0) {
      setFormError('Amount must be a positive USD value.');
      return;
    }
    const amountCents = Math.round(amountUsd * 100);
    if (amountCents < 1) {
      setFormError('Amount is too small after converting to cents.');
      return;
    }
    if (!source.trim()) {
      setFormError('Source label is required.');
      return;
    }

    let expiresAtIso: string | undefined;
    if (expiresAtLocal.trim()) {
      const d = new Date(expiresAtLocal);
      if (Number.isNaN(d.getTime())) {
        setFormError('Invalid expiry date.');
        return;
      }
      expiresAtIso = d.toISOString();
    }

    try {
      await createBatch({
        count,
        amountCents,
        source: source.trim(),
        ...(prefix.trim() ? { prefix: prefix.trim() } : {}),
        ...(expiresAtIso ? { expiresAt: expiresAtIso } : {}),
      }).unwrap();
      closeDialog();
      void refetch();
    } catch (e: unknown) {
      const msg =
        e &&
        typeof e === 'object' &&
        'data' in e &&
        e.data &&
        typeof e.data === 'object' &&
        'detail' in e.data
          ? String((e.data as { detail: unknown }).detail)
          : 'Failed to create batch.';
      setFormError(msg);
    }
  };

  return (
    <Container size="xl" py="lg">
      <Group justify="space-between" align="flex-start" gap="md" wrap="wrap" mb="md">
        <Box>
          <Title order={1} mb="xs">
            Discount batches (admin)
          </Title>
          <Text size="sm" c="dimmed">
            Generate G2A SafeKeys-style voucher codes. All face values and MyVoya checkout totals
            for this program are USD only — create matching USD listings on G2A.
          </Text>
        </Box>
        <Button
          leftSection={<Plus size={18} />}
          onClick={openDialog}
          tt="none"
          fw={600}
          style={{ flexShrink: 0 }}
        >
          Generate batch
        </Button>
      </Group>

      {error && (
        <Alert color="red" mb="md">
          Failed to load batches. You may need admin access.
        </Alert>
      )}

      {isLoading ? (
        <Group justify="center" py="lg">
          <Loader />
        </Group>
      ) : data?.batches?.length ? (
        <Paper withBorder>
          <ScrollArea>
            <Table striped highlightOnHover style={{ minWidth: 960 }}>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Source</Table.Th>
                  <Table.Th>Batch ID</Table.Th>
                  <Table.Th style={{ textAlign: 'right' }}>Created</Table.Th>
                  <Table.Th style={{ textAlign: 'right' }}>Total</Table.Th>
                  <Table.Th style={{ textAlign: 'right' }}>Active</Table.Th>
                  <Table.Th style={{ textAlign: 'right' }}>Reserved</Table.Th>
                  <Table.Th style={{ textAlign: 'right' }}>Used</Table.Th>
                  <Table.Th style={{ textAlign: 'right' }}>Expired</Table.Th>
                  <Table.Th style={{ textAlign: 'right' }}>Disabled</Table.Th>
                  <Table.Th style={{ textAlign: 'right' }}>Batch face value</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {data.batches.map((b) => (
                  <Table.Tr
                    key={b.batchId}
                    style={{ cursor: 'pointer' }}
                    onClick={() => navigate(adminDiscountBatchDetailPath(b.batchId))}
                  >
                    <Table.Td>{b.source || '—'}</Table.Td>
                    <Table.Td style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                      {b.batchId}
                    </Table.Td>
                    <Table.Td style={{ textAlign: 'right' }}>
                      {b.createdAt ? new Date(b.createdAt).toLocaleString() : '—'}
                    </Table.Td>
                    <Table.Td style={{ textAlign: 'right' }}>{b.total}</Table.Td>
                    <Table.Td style={{ textAlign: 'right' }}>{b.active}</Table.Td>
                    <Table.Td style={{ textAlign: 'right' }}>{b.reserved}</Table.Td>
                    <Table.Td style={{ textAlign: 'right' }}>{b.used}</Table.Td>
                    <Table.Td style={{ textAlign: 'right' }}>{b.expired}</Table.Td>
                    <Table.Td style={{ textAlign: 'right' }}>{b.disabled}</Table.Td>
                    <Table.Td style={{ textAlign: 'right' }}>
                      {formatUsdCentsOrDash(b.totalAmountCents ?? undefined)}
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </ScrollArea>
        </Paper>
      ) : (
        <Text c="dimmed">No batches yet.</Text>
      )}

      <Modal opened={dialogOpen} onClose={closeDialog} title="Generate batch" size="md" centered>
        <Stack gap="md" pt={4}>
          {formError && <Alert color="red">{formError}</Alert>}
          <TextInput
            label="Number of codes"
            type="number"
            value={countStr}
            onChange={(e) => setCountStr(e.currentTarget.value)}
            min={1}
            max={10_000}
            required
          />
          <TextInput
            label="Face value (USD per code)"
            type="number"
            value={amountUsdStr}
            onChange={(e) => setAmountUsdStr(e.currentTarget.value)}
            step={0.01}
            required
            description="Stored as integer cents server-side. Currency is always USD."
          />
          <TextInput
            label="Source label"
            value={source}
            onChange={(e) => setSource(e.currentTarget.value)}
            required
            description="e.g. G2A listing or internal batch name."
          />
          <TextInput
            label="Optional code prefix"
            value={prefix}
            onChange={(e) => setPrefix(e.currentTarget.value)}
            description="Overrides default VOYA-style prefix when set (see server rules)."
          />
          <TextInput
            label="Optional expiry (local)"
            type="datetime-local"
            value={expiresAtLocal}
            onChange={(e) => setExpiresAtLocal(e.currentTarget.value)}
          />
          <Group justify="flex-end" gap="xs">
            <Button variant="subtle" onClick={closeDialog} tt="none">
              Cancel
            </Button>
            <Button onClick={() => void handleCreate()} disabled={isCreating} tt="none" fw={600}>
              {isCreating ? 'Creating…' : 'Create'}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}

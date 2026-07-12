import { useMemo, useState } from 'react';
import {
  Box,
  Button,
  Modal,
  Stack,
  Text,
  TextInput,
  Title,
  UnstyledButton,
} from '@mantine/core';
import { MapPin } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store';
import {
  selectHotelSearchFormParams,
  setSearchFormParams,
  triggerSearchFromChips,
} from '@/store/slices/hotelBookingSlice';
import { buildHotelSearchRequestFromFormParams } from '../utils/buildHotelSearchRequest';

/**
 * Destination row + dialog for city (dates / rooms live in ContentPanel header chips, like flights).
 */
export function HotelSearchBarV2() {
  const dispatch = useAppDispatch();
  const searchFormParams = useAppSelector(selectHotelSearchFormParams);
  const [destinationDialogOpen, setDestinationDialogOpen] = useState(false);

  const destinationDisplay =
    searchFormParams.destination?.trim() || 'Destination';

  const canRunSearch = useMemo(
    () => buildHotelSearchRequestFromFormParams(searchFormParams) != null,
    [searchFormParams]
  );

  const handlePrimaryAction = () => {
    setDestinationDialogOpen(false);
    // Only bump the chip trigger when a real API request can be built (parity with HotelSearchPage).
    if (!canRunSearch) return;
    dispatch(triggerSearchFromChips());
  };

  return (
    <Box style={{ width: '100%' }}>
      {/* Row: destination — keyboard-accessible (WCAG) */}
      <UnstyledButton
        onClick={() => setDestinationDialogOpen(true)}
        aria-label="Edit destination"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 12,
          width: '100%',
          padding: '4px 0',
          borderRadius: 4,
          color: 'var(--mantine-color-dark-8)',
        }}
      >
        <Title order={5} fw={700}>
          {destinationDisplay}
        </Title>
      </UnstyledButton>

      <Modal
        opened={destinationDialogOpen}
        onClose={() => setDestinationDialogOpen(false)}
        title="Edit destination"
        size="md"
        centered
      >
        <Stack gap="md" mt={4}>
          <Box>
            <Text size="xs" c="dimmed" mb={4}>
              Destination
            </Text>
            <TextInput
              placeholder="City or destination"
              value={searchFormParams.destination}
              onChange={(e) =>
                dispatch(
                  setSearchFormParams({
                    ...searchFormParams,
                    destination: e.currentTarget.value,
                  })
                )
              }
              size="sm"
              data-autofocus
              leftSection={<MapPin size={18} color="var(--mantine-color-navy-7)" />}
            />
          </Box>
          {!canRunSearch && (
            <Text size="xs" c="dimmed">
              Set check-in and check-out in the header to run a search. Your destination is saved as
              you type.
            </Text>
          )}
          <Button
            onClick={handlePrimaryAction}
            style={{ alignSelf: 'flex-start' }}
          >
            {canRunSearch ? 'Search' : 'Close'}
          </Button>
        </Stack>
      </Modal>
    </Box>
  );
}

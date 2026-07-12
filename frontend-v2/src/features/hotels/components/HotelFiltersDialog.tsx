import { Button, Group, Modal, ScrollArea } from '@mantine/core';
import { zIndex } from '@/theme';
import { HotelFiltersPanel } from './HotelFiltersPanel';
import { countActiveHotelFilters, defaultHotelFilterState } from '../utils/hotelFilters';
import type { HotelFilterState, FilterableHotel } from '../utils/hotelFilters';

export interface HotelFiltersDialogProps {
  opened: boolean;
  onClose: () => void;
  filterState: HotelFilterState;
  onFilterChange: (next: HotelFilterState) => void;
  allHotels: FilterableHotel[];
  filteredHotelCount: number;
}

export function HotelFiltersDialog({
  opened,
  onClose,
  filterState,
  onFilterChange,
  allHotels,
  filteredHotelCount,
}: HotelFiltersDialogProps) {
  const activeCount = countActiveHotelFilters(filterState);
  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title="Filters"
      size="xl"
      zIndex={zIndex.detailModal}
      scrollAreaComponent={ScrollArea.Autosize}
      styles={{ title: { fontWeight: 700 } }}
    >
      <HotelFiltersPanel
        filterState={filterState}
        onFilterChange={onFilterChange}
        allHotels={allHotels}
      />
      <Group justify={activeCount > 0 ? 'space-between' : 'flex-end'} mt="md">
        {activeCount > 0 && (
          <Button variant="subtle" onClick={() => onFilterChange(defaultHotelFilterState)}>
            Clear all
          </Button>
        )}
        <Button onClick={onClose}>
          Show {filteredHotelCount} hotel{filteredHotelCount !== 1 ? 's' : ''}
        </Button>
      </Group>
    </Modal>
  );
}

import { ActionIcon, Button, Group, Select, Tooltip, type GroupProps } from '@mantine/core';
import { Filter, SlidersHorizontal } from 'lucide-react';
import type { HotelSortOption } from '../utils/hotelSort';

export interface HotelSortAndFiltersHeaderProps extends Omit<GroupProps, 'onChange'> {
  sortBy: HotelSortOption;
  onSortChange: (value: HotelSortOption) => void;
  sortMenuItems: { value: string; label: string }[];
  activeFilterCount: number;
  onFiltersClick: () => void;
  onChangePreferences?: () => void;
  selectMinWidth?: number;
}

export function HotelSortAndFiltersHeader({
  sortBy,
  onSortChange,
  sortMenuItems,
  activeFilterCount,
  onFiltersClick,
  onChangePreferences,
  selectMinWidth = 200,
  ...groupProps
}: HotelSortAndFiltersHeaderProps) {
  return (
    <Group gap="sm" {...groupProps}>
      <Select
        value={sortBy}
        onChange={(value) => value && onSortChange(value as HotelSortOption)}
        data={sortMenuItems}
        size="sm"
        style={{ minWidth: selectMinWidth }}
        allowDeselect={false}
      />
      {onChangePreferences ? (
        <Tooltip label="Change preferences" withArrow>
          <ActionIcon
            variant="outline"
            size="lg"
            radius="xl"
            aria-label="Change preferences"
            onClick={onChangePreferences}
          >
            <SlidersHorizontal size={16} />
          </ActionIcon>
        </Tooltip>
      ) : null}
      <Button
        variant="outline"
        size="sm"
        leftSection={<Filter size={16} />}
        onClick={onFiltersClick}
        style={{ borderRadius: 100 }}
      >
        {activeFilterCount > 0 ? `Filters (${activeFilterCount})` : 'Filters'}
      </Button>
    </Group>
  );
}

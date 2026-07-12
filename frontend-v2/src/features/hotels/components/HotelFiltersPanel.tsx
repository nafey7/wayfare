import { useMemo } from 'react';
import {
  Accordion,
  Box,
  Button,
  Checkbox,
  Group,
  Paper,
  RangeSlider,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import type { HotelFilterState } from '../utils/hotelFilters';
import {
  defaultHotelFilterState,
  isDefaultHotelFilterState,
  extractPropertyTypesFromHotels,
  getDistanceBounds,
  extractFacilitiesFromHotels,
  extractLocalitiesFromHotels,
  type FilterableHotel,
} from '../utils/hotelFilters';

const ACCORDION_VALUES = [
  'name',
  'price',
  'property-type',
  'star-rating',
  'facilities',
  'locality',
  'fare-type',
  'distance',
];

export interface HotelFiltersPanelProps {
  filterState: HotelFilterState;
  onFilterChange: (next: HotelFilterState) => void;
  allHotels: FilterableHotel[];
}

function getPriceBounds(hotels: FilterableHotel[]): { priceMin: number; priceMax: number } {
  if (hotels.length === 0) return { priceMin: 0, priceMax: 500 };
  const prices = hotels.map((h) => h.total).filter((p) => p > 0);
  if (prices.length === 0) return { priceMin: 0, priceMax: 500 };
  const min = Math.floor(Math.min(...prices));
  const max = Math.ceil(Math.max(...prices));
  return { priceMin: min, priceMax: max <= min ? min + 100 : max };
}

function formatPriceForSlider(value: number, currency: string): string {
  try {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency,
      maximumFractionDigits: 0,
    }).format(value);
  } catch {
    return `${currency} ${value.toLocaleString()}`;
  }
}

export function HotelFiltersPanel({
  filterState,
  onFilterChange,
  allHotels,
}: HotelFiltersPanelProps) {
  const bounds = useMemo(() => getPriceBounds(allHotels), [allHotels]);
  const distanceBounds = useMemo(() => getDistanceBounds(allHotels), [allHotels]);
  const currency = allHotels[0]?.currency ?? 'USD';
  const propertyTypes = useMemo(
    () => extractPropertyTypesFromHotels(allHotels),
    [allHotels]
  );
  const facilities = useMemo(
    () => extractFacilitiesFromHotels(allHotels),
    [allHotels]
  );
  const localities = useMemo(
    () => extractLocalitiesFromHotels(allHotels),
    [allHotels]
  );

  const update = (patch: Partial<HotelFilterState>) => {
    onFilterChange({ ...filterState, ...patch });
  };
  const handleReset = () => {
    onFilterChange(defaultHotelFilterState);
  };
  const hasActiveFilters = !isDefaultHotelFilterState(filterState);

  const priceValue: [number, number] = [
    filterState.priceMin ?? bounds.priceMin,
    filterState.priceMax ?? bounds.priceMax,
  ];
  const handlePriceChange = (value: [number, number]) => {
    update({ priceMin: value[0], priceMax: value[1] });
  };

  const distanceValue: [number, number] = [
    filterState.distanceMin ?? distanceBounds.distanceMin,
    filterState.distanceMax ?? distanceBounds.distanceMax,
  ];
  const handleDistanceChange = (value: [number, number]) => {
    update({ distanceMin: value[0], distanceMax: value[1] });
  };

  const toggleStar = (rating: number) => {
    const next = filterState.starRatings.includes(rating)
      ? filterState.starRatings.filter((r) => r !== rating)
      : [...filterState.starRatings, rating].sort((a, b) => a - b);
    update({ starRatings: next });
  };

  const togglePropertyType = (type: string) => {
    const next = filterState.propertyTypes.includes(type)
      ? filterState.propertyTypes.filter((t) => t !== type)
      : [...filterState.propertyTypes, type];
    update({ propertyTypes: next });
  };

  const toggleFacility = (facility: string) => {
    const next = filterState.facilities.includes(facility)
      ? filterState.facilities.filter((f) => f !== facility)
      : [...filterState.facilities, facility];
    update({ facilities: next });
  };

  const toggleLocality = (locality: string) => {
    const next = filterState.localities.includes(locality)
      ? filterState.localities.filter((l) => l !== locality)
      : [...filterState.localities, locality];
    update({ localities: next });
  };

  return (
    <Paper shadow="sm" radius="md" p="lg">
      <Group justify="space-between" align="center" mb="md">
        <Title order={6} fw={700}>
          Filters
        </Title>
        <Button
          variant="subtle"
          size="compact-sm"
          onClick={handleReset}
          disabled={!hasActiveFilters}
          tt="none"
          px={0}
          styles={{
            root: {
              minWidth: 'auto',
              fontWeight: 'inherit',
              fontSize: 'inherit',
            },
          }}
        >
          Reset all
        </Button>
      </Group>

      <Accordion multiple defaultValue={ACCORDION_VALUES} variant="default">
        {/* Hotel name */}
        <Accordion.Item value="name">
          <Accordion.Control>
            <Text fw={500}>Hotel name</Text>
          </Accordion.Control>
          <Accordion.Panel>
            <TextInput
              size="sm"
              placeholder="Search by name"
              value={filterState.nameQuery}
              onChange={(e) => update({ nameQuery: e.currentTarget.value })}
            />
          </Accordion.Panel>
        </Accordion.Item>

        {/* Price */}
        <Accordion.Item value="price">
          <Accordion.Control>
            <Text fw={500}>Price</Text>
          </Accordion.Control>
          <Accordion.Panel>
            <Box px={4}>
              <RangeSlider
                value={priceValue}
                onChange={handlePriceChange}
                min={bounds.priceMin}
                max={bounds.priceMax}
                step={Math.max(1, Math.floor((bounds.priceMax - bounds.priceMin) / 100))}
                label={(v) => formatPriceForSlider(v, currency)}
              />
              <Group justify="space-between" mt={8}>
                <Text size="sm">{formatPriceForSlider(priceValue[0], currency)}</Text>
                <Text size="sm">{formatPriceForSlider(priceValue[1], currency)}</Text>
              </Group>
            </Box>
          </Accordion.Panel>
        </Accordion.Item>

        {/* Property Type */}
        {propertyTypes.length > 0 && (
          <Accordion.Item value="property-type">
            <Accordion.Control>
              <Text fw={500}>Property type</Text>
            </Accordion.Control>
            <Accordion.Panel>
              <Stack gap={4}>
                {propertyTypes.map((type) => (
                  <Checkbox
                    key={type}
                    label={type}
                    checked={filterState.propertyTypes.includes(type)}
                    onChange={() => togglePropertyType(type)}
                  />
                ))}
              </Stack>
            </Accordion.Panel>
          </Accordion.Item>
        )}

        {/* Star rating */}
        <Accordion.Item value="star-rating">
          <Accordion.Control>
            <Text fw={500}>Star rating</Text>
          </Accordion.Control>
          <Accordion.Panel>
            <Stack gap={4}>
              {[1, 2, 3, 4, 5].map((rating) => (
                <Checkbox
                  key={rating}
                  label={`${rating} star${rating !== 1 ? 's' : ''}`}
                  checked={filterState.starRatings.includes(rating)}
                  onChange={() => toggleStar(rating)}
                />
              ))}
            </Stack>
          </Accordion.Panel>
        </Accordion.Item>

        {/* Facilities */}
        {facilities.length > 0 && (
          <Accordion.Item value="facilities">
            <Accordion.Control>
              <Text fw={500}>Facilities</Text>
            </Accordion.Control>
            <Accordion.Panel>
              <Stack gap={4} style={{ maxHeight: 200, overflowY: 'auto' }}>
                {facilities.map((facility) => (
                  <Checkbox
                    key={facility}
                    label={facility}
                    checked={filterState.facilities.includes(facility)}
                    onChange={() => toggleFacility(facility)}
                  />
                ))}
              </Stack>
            </Accordion.Panel>
          </Accordion.Item>
        )}

        {/* Neighbourhood / Locality */}
        {localities.length > 0 && (
          <Accordion.Item value="locality">
            <Accordion.Control>
              <Text fw={500}>Neighbourhood / Locality</Text>
            </Accordion.Control>
            <Accordion.Panel>
              <Stack gap={4} style={{ maxHeight: 200, overflowY: 'auto' }}>
                {localities.map((locality) => (
                  <Checkbox
                    key={locality}
                    label={locality}
                    checked={filterState.localities.includes(locality)}
                    onChange={() => toggleLocality(locality)}
                  />
                ))}
              </Stack>
            </Accordion.Panel>
          </Accordion.Item>
        )}

        {/* Fare type */}
        <Accordion.Item value="fare-type">
          <Accordion.Control>
            <Text fw={500}>Fare type</Text>
          </Accordion.Control>
          <Accordion.Panel>
            <Stack gap={4}>
              <Checkbox
                label="Refundable"
                checked={filterState.refundableOnly}
                onChange={(e) => update({ refundableOnly: e.currentTarget.checked })}
              />
              <Checkbox
                label="Non-refundable"
                checked={filterState.nonRefundableOnly}
                onChange={(e) => update({ nonRefundableOnly: e.currentTarget.checked })}
              />
            </Stack>
          </Accordion.Panel>
        </Accordion.Item>

        {/* Distance from city center - only when at least one hotel has distance */}
        {distanceBounds.hasDistance && (
          <Accordion.Item value="distance">
            <Accordion.Control>
              <Text fw={500}>Distance from center (km)</Text>
            </Accordion.Control>
            <Accordion.Panel>
              <Box px={4}>
                <RangeSlider
                  value={distanceValue}
                  onChange={handleDistanceChange}
                  min={distanceBounds.distanceMin}
                  max={distanceBounds.distanceMax}
                  step={0.1}
                  label={(v) => `${v.toFixed(1)} km`}
                />
                <Group justify="space-between" mt={8}>
                  <Text size="sm">{distanceValue[0].toFixed(1)} km</Text>
                  <Text size="sm">{distanceValue[1].toFixed(1)} km</Text>
                </Group>
              </Box>
            </Accordion.Panel>
          </Accordion.Item>
        )}
      </Accordion>
    </Paper>
  );
}

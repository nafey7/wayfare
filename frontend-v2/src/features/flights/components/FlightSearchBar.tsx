import { useState, useMemo } from 'react';
import { showErrorToast } from '@/utils/toast';
import {
  ActionIcon,
  Box,
  Button,
  Group,
  Menu,
  Paper,
  Popover,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { DatePickerInput } from '@mantine/dates';
import {
  ArrowLeftRight,
  Calendar,
  ChevronDown,
  PlaneLanding,
  PlaneTakeoff,
  Plus,
  Trash2,
  Users,
} from 'lucide-react';
import { TravellersSelector, TravellersData } from './TravellersSelector';
import { AirportAutocomplete, AirportOption } from './AirportAutocomplete';
import { formatTravellersDisplayText, getTripTypeLabel } from '../utils/flightUtils';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import {
  selectSearchFormParams,
  setTripType,
  setFrom,
  setTo,
  swapAirports,
  setDate,
  setReturnDate,
  setTravellers,
  setMultiCitySegments as setMultiCitySegmentsAction,
  updateMultiCitySegment,
  type SerializableAirportOption,
  type SerializableFlightSegment,
} from '@/store/slices/flightBookingSlice';
import type { TripType, FlightSearchSegment, FlightSearchParamsUI } from '@/types/flights';
import { today } from '@/utils/dates';

export type { TripType, FlightSearchSegment, FlightSearchParamsUI as FlightSearchParams };

const ICON_COLOR = 'var(--mantine-color-navy-2)';
const FromIcon = () => <PlaneTakeoff size={18} color={ICON_COLOR} />;
const ToIcon = () => <PlaneLanding size={18} color={ICON_COLOR} />;
const DateIcon = () => <Calendar size={18} color={ICON_COLOR} />;
const PassengersIcon = () => <Users size={18} color={ICON_COLOR} />;

const TRAVELLERS_INPUT_STYLES = {
  input: {
    backgroundColor: 'var(--mantine-color-gray-0)',
    cursor: 'pointer',
  },
} as const;

// Same shape as the V2 sibling — caption-style label above each form field.
const FIELD_LABEL_PROPS = {
  size: 'xs' as const,
  c: 'dimmed',
  display: 'block' as const,
  mb: 4,
} as const;

interface FlightSearchBarProps {
  onSearch: (searchParams: FlightSearchParamsUI) => void;
  /** When true, search button is disabled (during API call or loading) */
  isSearching?: boolean;
}

export function FlightSearchBar({ onSearch, isSearching = false }: FlightSearchBarProps) {
  // Mantine `useMediaQuery` mirrors MUI `theme.breakpoints.down('md')` (under 768px).
  const isMobile = useMediaQuery('(max-width: 768px)') ?? false;
  const dispatch = useAppDispatch();
  const searchFormParams = useAppSelector(selectSearchFormParams);

  const tripType = searchFormParams.tripType;
  const from = searchFormParams.from;
  const to = searchFormParams.to;
  const fromAirport: AirportOption | undefined = searchFormParams.fromAirport
    ? {
        iata: searchFormParams.fromAirport.iata,
        name: searchFormParams.fromAirport.name,
        city: searchFormParams.fromAirport.city,
        state: searchFormParams.fromAirport.state,
        country: searchFormParams.fromAirport.country,
        isCityOption: searchFormParams.fromAirport.isCityOption,
      }
    : undefined;
  const toAirport: AirportOption | undefined = searchFormParams.toAirport
    ? {
        iata: searchFormParams.toAirport.iata,
        name: searchFormParams.toAirport.name,
        city: searchFormParams.toAirport.city,
        state: searchFormParams.toAirport.state,
        country: searchFormParams.toAirport.country,
        isCityOption: searchFormParams.toAirport.isCityOption,
      }
    : undefined;
  const date = useMemo(() => {
    return searchFormParams.date ? new Date(searchFormParams.date) : null;
  }, [searchFormParams.date]);
  const returnDate = useMemo(() => {
    return searchFormParams.returnDate ? new Date(searchFormParams.returnDate) : null;
  }, [searchFormParams.returnDate]);
  const travellers = searchFormParams.travellers;
  const multiCitySegments = useMemo<FlightSearchSegment[]>(() => {
    if (!searchFormParams.segments) return [];
    return searchFormParams.segments.map((seg) => ({
      from: seg.from,
      to: seg.to,
      date: seg.date ? new Date(seg.date) : null,
    }));
  }, [searchFormParams.segments]);

  const [travellersOpen, setTravellersOpen] = useState(false);

  const handleTripTypeSelect = (type: TripType) => {
    dispatch(setTripType(type));
  };

  const handleSwap = () => {
    dispatch(swapAirports());
  };

  const handleTravellersChange = (data: TravellersData) => {
    dispatch(setTravellers(data));
  };

  const handleAddSegment = () => {
    const newSegments: SerializableFlightSegment[] = [
      ...(searchFormParams.segments || []),
      { from: '', to: '', date: null },
    ];
    dispatch(setMultiCitySegmentsAction(newSegments));
  };

  const handleDeleteSegment = (index: number) => {
    if (multiCitySegments.length > 2) {
      const newSegments = multiCitySegments.filter((_, i) => i !== index);
      const serializableSegments: SerializableFlightSegment[] = newSegments.map((seg) => ({
        from: seg.from,
        to: seg.to,
        date: seg.date ? seg.date.toISOString() : null,
      }));
      dispatch(setMultiCitySegmentsAction(serializableSegments));
    }
  };

  const handleSegmentChange = (
    index: number,
    field: keyof FlightSearchSegment,
    value: string | Date | null
  ) => {
    const segment = multiCitySegments[index];
    if (!segment) return;

    const updatedSegment: SerializableFlightSegment = {
      from: field === 'from' ? (value as string) : segment.from,
      to: field === 'to' ? (value as string) : segment.to,
      date:
        field === 'date'
          ? value
            ? (value as Date).toISOString()
            : null
          : segment.date
            ? segment.date.toISOString()
            : null,
    };

    dispatch(updateMultiCitySegment({ index, segment: updatedSegment }));
  };

  const handleSegmentSwap = (index: number) => {
    const segment = multiCitySegments[index];
    if (!segment) return;

    const updatedSegment: SerializableFlightSegment = {
      from: segment.to,
      to: segment.from,
      date: segment.date ? segment.date.toISOString() : null,
    };

    dispatch(updateMultiCitySegment({ index, segment: updatedSegment }));
  };

  const handleSearch = () => {
    if (tripType === 'multi-city') {
      const invalidSegment = multiCitySegments.findIndex(
        (segment) => !segment.from || !segment.to || !segment.date
      );
      if (invalidSegment >= 0) {
        showErrorToast(
          `Please fill in From, To, and Depart date for flight ${invalidSegment + 1}.`
        );
        return;
      }
      if (multiCitySegments.length < 2) {
        showErrorToast('Multi-city search requires at least 2 flight segments.');
        return;
      }
      onSearch({
        from: '',
        to: '',
        date: null,
        segments: multiCitySegments,
        travellers,
        tripType,
      });
    } else {
      if (!from?.trim()) {
        showErrorToast('Please enter an origin (city or airport).');
        return;
      }
      if (!to?.trim()) {
        showErrorToast('Please enter a destination (city or airport).');
        return;
      }
      if (!date) {
        showErrorToast('Please select a departure date.');
        return;
      }
      if (tripType === 'round-trip' && !returnDate) {
        showErrorToast('Please select a return date.');
        return;
      }
      onSearch({
        from: from.trim(),
        to: to.trim(),
        date,
        returnDate: tripType === 'round-trip' ? returnDate : null,
        travellers,
        tripType,
        fromAirport,
        toAirport,
      });
    }
  };

  return (
    <Box w="100%">
      {/* Trip Type Selector */}
      <Box mb={12}>
        <Menu position="bottom-start" withinPortal>
          <Menu.Target>
            <Button
              variant="default"
              size="xs"
              rightSection={<ChevronDown size={16} />}
              styles={{
                root: {
                  borderColor: 'var(--mantine-color-gray-3)',
                  color: 'var(--mantine-color-black)',
                  borderRadius: 8,
                  paddingLeft: 12,
                  paddingRight: 12,
                  height: 32,
                },
              }}
            >
              {getTripTypeLabel(tripType)}
            </Button>
          </Menu.Target>
          <Menu.Dropdown>
            <Menu.Item onClick={() => handleTripTypeSelect('one-way')}>One way</Menu.Item>
            <Menu.Item onClick={() => handleTripTypeSelect('round-trip')}>Round trip</Menu.Item>
            <Menu.Item onClick={() => handleTripTypeSelect('multi-city')} disabled>
              Multi city
            </Menu.Item>
          </Menu.Dropdown>
        </Menu>
      </Box>

      {/* Search Bar */}
      <Paper shadow="sm" radius="md" p="sm" w="100%" withBorder>
        {tripType === 'multi-city' ? (
          /* Multi-city UI */
          <Box>
            {/* Flight Segments */}
            <Stack gap={12} mb={12}>
              {multiCitySegments.map((segment, index) => (
                <Group
                  key={index}
                  gap={12}
                  wrap="wrap"
                  align={isMobile ? 'stretch' : 'flex-end'}
                  style={{ flexDirection: isMobile ? 'column' : 'row', position: 'relative' }}
                >
                  {/* FROM */}
                  <Box style={{ flex: isMobile ? 1 : '2 1 180px', minWidth: 0 }}>
                    <Text {...FIELD_LABEL_PROPS}>
                      From
                    </Text>
                    <AirportAutocomplete
                      value={segment.from}
                      onChange={(value) => handleSegmentChange(index, 'from', value)}
                      placeholder="City or airport"
                      size="small"
                      startAdornment={<FromIcon />}
                      fullWidth
                    />
                  </Box>

                  {/* Swap Button */}
                  <ActionIcon
                    size="md"
                    onClick={() => handleSegmentSwap(index)}
                    aria-label="Swap origin and destination for this leg"
                    color="navy.7"
                    variant="filled"
                    style={{
                      alignSelf: isMobile ? 'center' : 'flex-end',
                      marginBottom: isMobile ? 0 : 12,
                      transform: isMobile ? 'rotate(90deg)' : 'none',
                    }}
                  >
                    <ArrowLeftRight size={18} color="white" />
                  </ActionIcon>

                  {/* TO */}
                  <Box style={{ flex: isMobile ? 1 : '2 1 180px', minWidth: 0 }}>
                    <Text {...FIELD_LABEL_PROPS}>
                      To
                    </Text>
                    <AirportAutocomplete
                      value={segment.to}
                      onChange={(value) => handleSegmentChange(index, 'to', value)}
                      placeholder="City or airport"
                      size="small"
                      startAdornment={<ToIcon />}
                      fullWidth
                    />
                  </Box>

                  {/* DEPART DATE */}
                  <Box style={{ flex: isMobile ? 1 : '0 0 140px', minWidth: 0 }}>
                    <Text {...FIELD_LABEL_PROPS}>
                      Depart
                    </Text>
                    <DatePickerInput
                      value={segment.date}
                      minDate={
                        index === 0
                          ? today()
                          : multiCitySegments[index - 1]?.date ?? today()
                      }
                      onChange={(newDate) => {
                        // DatePickerInput returns Date | null in default mode.
                        const d = newDate ?? null;
                        handleSegmentChange(index, 'date', d);
                      }}
                      placeholder={segment.date ? undefined : 'Add date'}
                      size="sm"
                      leftSection={<DateIcon />}
                      w="100%"
                    />
                  </Box>

                  {/* Delete Button */}
                  <ActionIcon
                    size="md"
                    onClick={() => handleDeleteSegment(index)}
                    disabled={multiCitySegments.length <= 2}
                    aria-label="Remove leg"
                    color="red"
                    variant="filled"
                    style={{
                      alignSelf: isMobile ? 'center' : 'flex-end',
                      marginBottom: isMobile ? 0 : 12,
                    }}
                  >
                    <Trash2 size={18} color="white" />
                  </ActionIcon>
                </Group>
              ))}
            </Stack>

            {/* Add Flight Button */}
            <Group justify="center" mb={12}>
              <Button
                variant="default"
                size="xs"
                leftSection={<Plus size={16} />}
                onClick={handleAddSegment}
                styles={{
                  root: {
                    borderColor: 'var(--mantine-color-navy-2)',
                    color: 'var(--mantine-color-navy-7)',
                  },
                }}
              >
                Add another flight
              </Button>
            </Group>

            {/* Bottom Row: Travellers and Search Button */}
            <Group
              gap={12}
              align={isMobile ? 'stretch' : 'flex-end'}
              style={{ flexDirection: isMobile ? 'column' : 'row' }}
            >
              {/* TRAVELLERS AND CABIN CLASS */}
              <Box style={{ flex: isMobile ? 1 : '0 0 160px', minWidth: 0 }}>
                <Text {...FIELD_LABEL_PROPS}>
                  Travellers and cabin class
                </Text>
                <Popover
                  opened={travellersOpen}
                  onClose={() => setTravellersOpen(false)}
                  position="bottom-start"
                  shadow="md"
                  radius="md"
                  withinPortal
                >
                  <Popover.Target>
                    <TextInput
                      readOnly
                      placeholder="1 Adult, Economy"
                      value={formatTravellersDisplayText(travellers)}
                      onClick={() => setTravellersOpen((p) => !p)}
                      size="sm"
                      leftSection={<PassengersIcon />}
                      rightSection={<ChevronDown size={16} color="var(--mantine-color-gray-6)" />}
                      styles={TRAVELLERS_INPUT_STYLES}
                    />
                  </Popover.Target>
                  <Popover.Dropdown>
                    <TravellersSelector
                      value={travellers}
                      onChange={handleTravellersChange}
                      onClose={() => setTravellersOpen(false)}
                    />
                  </Popover.Dropdown>
                </Popover>
              </Box>

              {/* SEARCH BUTTON */}
              <Box style={{ flex: isMobile ? 1 : '0 0 auto', minWidth: isMobile ? '100%' : 100 }}>
                <Button
                  variant="filled"
                  size="sm"
                  onClick={handleSearch}
                  disabled={
                    isSearching ||
                    !multiCitySegments.every((s) => s.from && s.to && s.date) ||
                    multiCitySegments.length < 2
                  }
                  fullWidth
                  fw={600}
                >
                  Search
                </Button>
              </Box>
            </Group>
          </Box>
        ) : (
          /* One-way / Round-trip UI */
          <Group
            gap={12}
            align={isMobile ? 'stretch' : 'flex-end'}
            wrap="wrap"
            style={{ flexDirection: isMobile ? 'column' : 'row', width: '100%' }}
          >
            {/* FROM */}
            <Box style={{ flex: isMobile ? 1 : '2 1 200px', minWidth: 0 }}>
              <Text {...FIELD_LABEL_PROPS}>
                From
              </Text>
              <AirportAutocomplete
                value={from}
                onChange={(value, airport) => {
                  const serializableAirport: SerializableAirportOption | undefined = airport
                    ? {
                        iata: airport.iata,
                        name: airport.name,
                        city: airport.city,
                        state: airport.state,
                        country: airport.country,
                        isCityOption: airport.isCityOption,
                      }
                    : undefined;
                  dispatch(setFrom({ value, airport: serializableAirport }));
                }}
                placeholder="City or airport"
                size="small"
                startAdornment={<FromIcon />}
                fullWidth
              />
            </Box>

            {/* Swap Button */}
            <ActionIcon
              size="md"
              onClick={handleSwap}
              aria-label="Swap origin and destination"
              color="navy.7"
              variant="filled"
              style={{
                alignSelf: isMobile ? 'center' : 'flex-end',
                marginBottom: isMobile ? 0 : 12,
                transform: isMobile ? 'rotate(90deg)' : 'none',
              }}
            >
              <ArrowLeftRight size={18} color="white" />
            </ActionIcon>

            {/* TO */}
            <Box style={{ flex: isMobile ? 1 : '2 1 200px', minWidth: 0 }}>
              <Text {...FIELD_LABEL_PROPS}>
                To
              </Text>
              <AirportAutocomplete
                value={to}
                onChange={(value, airport) => {
                  const serializableAirport: SerializableAirportOption | undefined = airport
                    ? {
                        iata: airport.iata,
                        name: airport.name,
                        city: airport.city,
                        state: airport.state,
                        country: airport.country,
                        isCityOption: airport.isCityOption,
                      }
                    : undefined;
                  dispatch(setTo({ value, airport: serializableAirport }));
                }}
                placeholder="City or airport"
                size="small"
                startAdornment={<ToIcon />}
                fullWidth
              />
            </Box>

            {/* DEPART DATE */}
            <Box style={{ flex: isMobile ? 1 : '0 0 140px', minWidth: 0 }}>
              <Text {...FIELD_LABEL_PROPS}>
                Depart
              </Text>
              <DatePickerInput
                value={date}
                minDate={today()}
                onChange={(newDate) => {
                  const d = newDate ?? null;
                  dispatch(setDate(d ? d.toISOString() : null));
                }}
                placeholder="Select date"
                size="sm"
                leftSection={<DateIcon />}
                w="100%"
              />
            </Box>

            {/* RETURN DATE - Only shown for round trip */}
            {tripType === 'round-trip' && (
              <Box style={{ flex: isMobile ? 1 : '0 0 140px', minWidth: 0 }}>
                <Text {...FIELD_LABEL_PROPS}>
                  Return
                </Text>
                <DatePickerInput
                  value={returnDate}
                  minDate={date ?? today()}
                  onChange={(newDate) => {
                    const d = newDate ?? null;
                    dispatch(setReturnDate(d ? d.toISOString() : null));
                  }}
                  placeholder="Select date"
                  size="sm"
                  leftSection={<DateIcon />}
                  w="100%"
                />
              </Box>
            )}

            {/* TRAVELLERS AND CABIN CLASS */}
            <Box style={{ flex: isMobile ? 1 : '0 0 160px', minWidth: 0 }}>
              <Text {...FIELD_LABEL_PROPS}>
                Travellers and cabin class
              </Text>
              <Popover
                opened={travellersOpen}
                onClose={() => setTravellersOpen(false)}
                position="bottom-start"
                shadow="md"
                radius="md"
                withinPortal
              >
                <Popover.Target>
                  <TextInput
                    readOnly
                    placeholder="1 Adult, Economy"
                    value={formatTravellersDisplayText(travellers)}
                    onClick={() => setTravellersOpen((p) => !p)}
                    size="sm"
                    leftSection={<PassengersIcon />}
                    rightSection={<ChevronDown size={16} color="var(--mantine-color-gray-6)" />}
                    styles={TRAVELLERS_INPUT_STYLES}
                  />
                </Popover.Target>
                <Popover.Dropdown>
                  <TravellersSelector
                    value={travellers}
                    onChange={handleTravellersChange}
                    onClose={() => setTravellersOpen(false)}
                  />
                </Popover.Dropdown>
              </Popover>
            </Box>

            {/* SEARCH BUTTON */}
            <Box style={{ flex: isMobile ? 1 : '0 0 auto', minWidth: isMobile ? '100%' : 100 }}>
              <Button
                variant="filled"
                size="sm"
                onClick={handleSearch}
                disabled={
                  isSearching ||
                  !from ||
                  !to ||
                  !date ||
                  (tripType === 'round-trip' && !returnDate)
                }
                fullWidth
                fw={600}
              >
                Search
              </Button>
            </Box>
          </Group>
        )}
      </Paper>
    </Box>
  );
}

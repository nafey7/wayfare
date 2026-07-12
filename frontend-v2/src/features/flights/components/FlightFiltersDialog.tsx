import { useState, useMemo, useEffect } from 'react';
import { zIndex } from '@/theme';
import {
  Modal,
  ScrollArea,
  Box,
  Group,
  Text,
  Button,
  ActionIcon,
  Accordion,
  Checkbox,
  RangeSlider,
  Stack,
  Tabs,
} from '@mantine/core';
import { X } from 'lucide-react';
import type { FlightFilterState } from '../utils/flightFilters';
import {
  defaultFlightFilterState,
  minutesToTime,
  extractAirlinesFromFlights,
  extractCabinClassesFromFlights,
  extractDepartureAirportsFromFlights,
  extractArrivalAirportsFromFlights,
  extractReturnDepartureAirportsFromFlights,
  extractReturnArrivalAirportsFromFlights,
  type FilterableFlight,
} from '../utils/flightFilters';

const MINUTES_IN_DAY = 24 * 60;

const ACCORDION_ITEM_VALUES = [
  'price',
  'stops',
  'airlines',
  'cabin',
  'departure-airports',
  'arrival-airports',
  'duration',
  'departure-time',
  'arrival-time',
];

function useRangeSliderDragState(committedMin: number, committedMax: number) {
  const [local, setLocal] = useState<[number, number]>([committedMin, committedMax]);
  useEffect(() => { setLocal([committedMin, committedMax]); }, [committedMin, committedMax]);
  return [local, setLocal] as const;
}

function getFilterBounds(flights: FilterableFlight[]) {
  let priceMin = 0;
  let priceMax = 50000;
  let outboundDurationMax = 24;
  let inboundDurationMax = 24;

  if (flights.length > 0) {
    const prices = flights.map((f) => f.price).filter((p) => p > 0);
    if (prices.length > 0) {
      priceMin = Math.floor(Math.min(...prices));
      priceMax = Math.ceil(Math.max(...prices));
      if (priceMax <= priceMin) priceMax = priceMin + 100;
    }

    for (const f of flights) {
      const out = parseLegDurationHours(f.legs[0]);
      if (out != null && out > outboundDurationMax) outboundDurationMax = Math.ceil(out * 2) / 2;
      if (f.legs[1] != null) {
        const inH = parseLegDurationHours(f.legs[1]);
        if (inH != null && inH > inboundDurationMax) inboundDurationMax = Math.ceil(inH * 2) / 2;
      }
    }
    outboundDurationMax = Math.max(24, outboundDurationMax);
    inboundDurationMax = Math.max(24, inboundDurationMax);
  }

  return { priceMin, priceMax, outboundDurationMax, inboundDurationMax };
}

function parseLegDurationHours(
  leg: { totalTimeDisplay?: string | null; duration?: string } | undefined
): number | null {
  if (!leg) return null;
  const text = leg.totalTimeDisplay ?? leg.duration;
  if (!text) return null;
  const hMatch = text.match(/(\d+)\s*h/);
  const mMatch = text.match(/(\d+)\s*m/);
  const hours = hMatch && hMatch[1] != null ? parseInt(hMatch[1], 10) : 0;
  const minutes = mMatch && mMatch[1] != null ? parseInt(mMatch[1], 10) : 0;
  return hours + minutes / 60;
}

function timeStrToMinutes(s: string | null | undefined): number {
  if (!s) return 0;
  const [h, m] = s.split(':').map(Number);
  return (h ?? 0) * 60 + (m ?? 0);
}

const tabsStyles = {
  list: { gap: 0, marginBottom: 12 },
  tab: { minHeight: 40, paddingTop: 0, paddingBottom: 0, flex: 1 },
} as const;

export interface FlightFiltersDialogProps {
  opened: boolean;
  onClose: () => void;
  filterState: FlightFilterState;
  onFilterChange: (next: FlightFilterState) => void;
  allFlights: FilterableFlight[];
  isRoundTrip: boolean;
  filteredFlightCount: number;
}

export function FlightFiltersDialog({
  opened,
  onClose,
  filterState,
  onFilterChange,
  allFlights,
  isRoundTrip,
  filteredFlightCount,
}: FlightFiltersDialogProps) {
  const bounds = useMemo(() => getFilterBounds(allFlights), [allFlights]);
  const airlines = useMemo(() => extractAirlinesFromFlights(allFlights), [allFlights]);
  const cabinClasses = useMemo(() => extractCabinClassesFromFlights(allFlights), [allFlights]);
  const departureAirports = useMemo(() => extractDepartureAirportsFromFlights(allFlights), [allFlights]);
  const arrivalAirports = useMemo(() => extractArrivalAirportsFromFlights(allFlights), [allFlights]);
  const returnDepartureAirports = useMemo(() => extractReturnDepartureAirportsFromFlights(allFlights), [allFlights]);
  const returnArrivalAirports = useMemo(() => extractReturnArrivalAirportsFromFlights(allFlights), [allFlights]);

  const update = (patch: Partial<FlightFilterState>) => {
    onFilterChange({ ...filterState, ...patch });
  };

  const handleClearAll = () => {
    onFilterChange(defaultFlightFilterState);
  };

  // --- Range slider local drag state ---
  // `onChange` updates local state for smooth visual feedback during drag.
  // `onChangeEnd` (fires on mouse/touch release) commits the value to Redux, triggering
  // filter re-computation once per gesture instead of on every pixel of movement.
  // Each `useEffect` syncs local state when Redux changes externally (e.g. "Clear all").

  const committedPriceMin = filterState.priceMin ?? bounds.priceMin;
  const committedPriceMax = filterState.priceMax ?? bounds.priceMax;
  const [priceValue, setLocalPriceValue] = useRangeSliderDragState(committedPriceMin, committedPriceMax);
  const handlePriceChange = (value: [number, number]) => { update({ priceMin: value[0], priceMax: value[1] }); };

  const committedOutboundDurMin = filterState.outboundDurationMin ?? 0;
  const committedOutboundDurMax = filterState.outboundDurationMax ?? bounds.outboundDurationMax;
  const [outboundDurationValue, setLocalOutboundDuration] = useRangeSliderDragState(committedOutboundDurMin, committedOutboundDurMax);
  const handleOutboundDurationChange = (value: [number, number]) => { update({ outboundDurationMin: value[0], outboundDurationMax: value[1] }); };

  const committedInboundDurMin = filterState.inboundDurationMin ?? 0;
  const committedInboundDurMax = filterState.inboundDurationMax ?? bounds.inboundDurationMax;
  const [inboundDurationValue, setLocalInboundDuration] = useRangeSliderDragState(committedInboundDurMin, committedInboundDurMax);
  const handleInboundDurationChange = (value: [number, number]) => { update({ inboundDurationMin: value[0], inboundDurationMax: value[1] }); };

  const committedDepTimeMin = filterState.departureTimeMin == null ? 0 : timeStrToMinutes(filterState.departureTimeMin);
  const committedDepTimeMax = filterState.departureTimeMax == null ? MINUTES_IN_DAY : timeStrToMinutes(filterState.departureTimeMax);
  const [departureTimeValue, setLocalDepartureTime] = useRangeSliderDragState(committedDepTimeMin, committedDepTimeMax);
  const handleDepartureTimeChange = ([minN, maxN]: [number, number]) => {
    update({ departureTimeMin: minN === 0 ? null : minutesToTime(minN), departureTimeMax: maxN === MINUTES_IN_DAY ? null : minutesToTime(maxN) });
  };

  const committedArrTimeMin = filterState.arrivalTimeMin == null ? 0 : timeStrToMinutes(filterState.arrivalTimeMin);
  const committedArrTimeMax = filterState.arrivalTimeMax == null ? MINUTES_IN_DAY : timeStrToMinutes(filterState.arrivalTimeMax);
  const [arrivalTimeValue, setLocalArrivalTime] = useRangeSliderDragState(committedArrTimeMin, committedArrTimeMax);
  const handleArrivalTimeChange = ([minN, maxN]: [number, number]) => {
    update({ arrivalTimeMin: minN === 0 ? null : minutesToTime(minN), arrivalTimeMax: maxN === MINUTES_IN_DAY ? null : minutesToTime(maxN) });
  };

  const committedRetDepTimeMin = filterState.returnDepartureTimeMin == null ? 0 : timeStrToMinutes(filterState.returnDepartureTimeMin);
  const committedRetDepTimeMax = filterState.returnDepartureTimeMax == null ? MINUTES_IN_DAY : timeStrToMinutes(filterState.returnDepartureTimeMax);
  const [returnDepartureTimeValue, setLocalReturnDepartureTime] = useRangeSliderDragState(committedRetDepTimeMin, committedRetDepTimeMax);
  const handleReturnDepartureTimeChange = ([minN, maxN]: [number, number]) => {
    update({ returnDepartureTimeMin: minN === 0 ? null : minutesToTime(minN), returnDepartureTimeMax: maxN === MINUTES_IN_DAY ? null : minutesToTime(maxN) });
  };

  const committedRetArrTimeMin = filterState.returnArrivalTimeMin == null ? 0 : timeStrToMinutes(filterState.returnArrivalTimeMin);
  const committedRetArrTimeMax = filterState.returnArrivalTimeMax == null ? MINUTES_IN_DAY : timeStrToMinutes(filterState.returnArrivalTimeMax);
  const [returnArrivalTimeValue, setLocalReturnArrivalTime] = useRangeSliderDragState(committedRetArrTimeMin, committedRetArrTimeMax);
  const handleReturnArrivalTimeChange = ([minN, maxN]: [number, number]) => {
    update({ returnArrivalTimeMin: minN === 0 ? null : minutesToTime(minN), returnArrivalTimeMax: maxN === MINUTES_IN_DAY ? null : minutesToTime(maxN) });
  };

  type ArrayFilterKey =
    | 'airlines'
    | 'cabinClasses'
    | 'departureAirports'
    | 'arrivalAirports'
    | 'returnDepartureAirports'
    | 'returnArrivalAirports';

  const toggleArrayFilter = (key: ArrayFilterKey, value: string) => {
    const current = filterState[key];
    const next = current.includes(value)
      ? current.filter((v) => v !== value)
      : [...current, value];
    update({ [key]: next });
  };

  const toggleAirline = (code: string) => toggleArrayFilter('airlines', code);
  const toggleCabin = (cabin: string) => toggleArrayFilter('cabinClasses', cabin);
  const toggleDepartureAirport = (code: string) => toggleArrayFilter('departureAirports', code);
  const toggleArrivalAirport = (code: string) => toggleArrayFilter('arrivalAirports', code);
  const toggleReturnDepartureAirport = (code: string) =>
    toggleArrayFilter('returnDepartureAirports', code);
  const toggleReturnArrivalAirport = (code: string) =>
    toggleArrayFilter('returnArrivalAirports', code);

  const [stopsTab, setStopsTab] = useState<string>('outbound');
  const [durationTab, setDurationTab] = useState<string>('outbound');
  const [departureTimeTab, setDepartureTimeTab] = useState<string>('outbound');
  const [arrivalTimeTab, setArrivalTimeTab] = useState<string>('outbound');
  const [departureAirportTab, setDepartureAirportTab] = useState<string>('outbound');
  const [arrivalAirportTab, setArrivalAirportTab] = useState<string>('outbound');

  const stopsOutboundContent = (
    <Stack gap={4}>
      <Checkbox
        label="Direct only"
        checked={filterState.directOnly}
        onChange={(e) => update({ directOnly: e.currentTarget.checked })}
      />
      <Checkbox
        label="1 stop"
        checked={filterState.stops1}
        onChange={(e) => update({ stops1: e.currentTarget.checked })}
      />
      <Checkbox
        label="2+ stops"
        checked={filterState.stops2Plus}
        onChange={(e) => update({ stops2Plus: e.currentTarget.checked })}
      />
    </Stack>
  );

  const stopsInboundContent = (
    <Stack gap={4}>
      <Checkbox
        label="Direct only"
        checked={filterState.returnDirectOnly}
        onChange={(e) => update({ returnDirectOnly: e.currentTarget.checked })}
      />
      <Checkbox
        label="1 stop"
        checked={filterState.returnStops1}
        onChange={(e) => update({ returnStops1: e.currentTarget.checked })}
      />
      <Checkbox
        label="2+ stops"
        checked={filterState.returnStops2Plus}
        onChange={(e) => update({ returnStops2Plus: e.currentTarget.checked })}
      />
    </Stack>
  );

  const durationOutboundContent = (
    <Box px={4}>
      <RangeSlider
        value={outboundDurationValue}
        onChange={setLocalOutboundDuration}
        onChangeEnd={handleOutboundDurationChange}
        min={0}
        max={bounds.outboundDurationMax}
        step={0.5}
        label={(v) => `${v.toFixed(1)}h`}
      />
      <Group justify="space-between" mt={8}>
        <Text size="sm">{outboundDurationValue[0].toFixed(1)}h</Text>
        <Text size="sm">{outboundDurationValue[1].toFixed(1)}h</Text>
      </Group>
    </Box>
  );

  const durationInboundContent = (
    <Box px={4}>
      <RangeSlider
        value={inboundDurationValue}
        onChange={setLocalInboundDuration}
        onChangeEnd={handleInboundDurationChange}
        min={0}
        max={bounds.inboundDurationMax}
        step={0.5}
        label={(v) => `${v.toFixed(1)}h`}
      />
      <Group justify="space-between" mt={8}>
        <Text size="sm">{inboundDurationValue[0].toFixed(1)}h</Text>
        <Text size="sm">{inboundDurationValue[1].toFixed(1)}h</Text>
      </Group>
    </Box>
  );

  const departureTimeOutboundContent = (
    <Box px={4}>
      <RangeSlider
        value={departureTimeValue}
        onChange={setLocalDepartureTime}
        onChangeEnd={handleDepartureTimeChange}
        min={0}
        max={MINUTES_IN_DAY}
        step={30}
        label={(v) => minutesToTime(v)}
      />
      <Group justify="space-between" mt={8}>
        <Text size="sm">{minutesToTime(departureTimeValue[0])}</Text>
        <Text size="sm">{minutesToTime(departureTimeValue[1])}</Text>
      </Group>
    </Box>
  );

  const departureTimeInboundContent = (
    <Box px={4}>
      <RangeSlider
        value={returnDepartureTimeValue}
        onChange={setLocalReturnDepartureTime}
        onChangeEnd={handleReturnDepartureTimeChange}
        min={0}
        max={MINUTES_IN_DAY}
        step={30}
        label={(v) => minutesToTime(v)}
      />
      <Group justify="space-between" mt={8}>
        <Text size="sm">{minutesToTime(returnDepartureTimeValue[0])}</Text>
        <Text size="sm">{minutesToTime(returnDepartureTimeValue[1])}</Text>
      </Group>
    </Box>
  );

  const arrivalTimeOutboundContent = (
    <Box px={4}>
      <RangeSlider
        value={arrivalTimeValue}
        onChange={setLocalArrivalTime}
        onChangeEnd={handleArrivalTimeChange}
        min={0}
        max={MINUTES_IN_DAY}
        step={30}
        label={(v) => minutesToTime(v)}
      />
      <Group justify="space-between" mt={8}>
        <Text size="sm">{minutesToTime(arrivalTimeValue[0])}</Text>
        <Text size="sm">{minutesToTime(arrivalTimeValue[1])}</Text>
      </Group>
    </Box>
  );

  const arrivalTimeInboundContent = (
    <Box px={4}>
      <RangeSlider
        value={returnArrivalTimeValue}
        onChange={setLocalReturnArrivalTime}
        onChangeEnd={handleReturnArrivalTimeChange}
        min={0}
        max={MINUTES_IN_DAY}
        step={30}
        label={(v) => minutesToTime(v)}
      />
      <Group justify="space-between" mt={8}>
        <Text size="sm">{minutesToTime(returnArrivalTimeValue[0])}</Text>
        <Text size="sm">{minutesToTime(returnArrivalTimeValue[1])}</Text>
      </Group>
    </Box>
  );

  const departureAirportsOutboundContent = (
    <Stack gap={4}>
      {departureAirports.length === 0 ? (
        <Text size="sm" c="dimmed" px={4}>
          No departure airports
        </Text>
      ) : (
        departureAirports.map(({ code, name }) => (
          <Checkbox
            key={code}
            label={`${name} (${code})`}
            checked={filterState.departureAirports.includes(code)}
            onChange={() => toggleDepartureAirport(code)}
          />
        ))
      )}
    </Stack>
  );

  const departureAirportsInboundContent = (
    <Stack gap={4}>
      {returnDepartureAirports.length === 0 ? (
        <Text size="sm" c="dimmed" px={4}>
          No departure airports
        </Text>
      ) : (
        returnDepartureAirports.map(({ code, name }) => (
          <Checkbox
            key={code}
            label={`${name} (${code})`}
            checked={filterState.returnDepartureAirports.includes(code)}
            onChange={() => toggleReturnDepartureAirport(code)}
          />
        ))
      )}
    </Stack>
  );

  const arrivalAirportsOutboundContent = (
    <Stack gap={4}>
      {arrivalAirports.length === 0 ? (
        <Text size="sm" c="dimmed" px={4}>
          No arrival airports
        </Text>
      ) : (
        arrivalAirports.map(({ code, name }) => (
          <Checkbox
            key={code}
            label={`${name} (${code})`}
            checked={filterState.arrivalAirports.includes(code)}
            onChange={() => toggleArrivalAirport(code)}
          />
        ))
      )}
    </Stack>
  );

  const arrivalAirportsInboundContent = (
    <Stack gap={4}>
      {returnArrivalAirports.length === 0 ? (
        <Text size="sm" c="dimmed" px={4}>
          No arrival airports
        </Text>
      ) : (
        returnArrivalAirports.map(({ code, name }) => (
          <Checkbox
            key={code}
            label={`${name} (${code})`}
            checked={filterState.returnArrivalAirports.includes(code)}
            onChange={() => toggleReturnArrivalAirport(code)}
          />
        ))
      )}
    </Stack>
  );

  const renderTabbed = (
    tab: string,
    setTab: (v: string) => void,
    outbound: React.ReactNode,
    inbound: React.ReactNode,
    ariaLabel: string
  ) => (
    <Tabs value={tab} onChange={(v) => v && setTab(v)} variant="default" styles={tabsStyles}>
      <Tabs.List grow aria-label={ariaLabel}>
        <Tabs.Tab value="outbound">Outbound</Tabs.Tab>
        <Tabs.Tab value="inbound">Inbound</Tabs.Tab>
      </Tabs.List>
      <Tabs.Panel value="outbound">{outbound}</Tabs.Panel>
      <Tabs.Panel value="inbound">{inbound}</Tabs.Panel>
    </Tabs>
  );

  const flightLabel = filteredFlightCount === 1 ? 'flight' : 'flights';

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      withCloseButton={false}
      padding={0}
      size="xl"
      radius="md"
      zIndex={zIndex.detailModal}
      styles={{
        content: {
          display: 'flex',
          flexDirection: 'column',
          height: '90dvh',
          maxHeight: '90dvh',
        },
        body: {
          flex: 1,
          minHeight: 0,
          display: 'flex',
          flexDirection: 'column',
          padding: 0,
          overflow: 'hidden',
        },
      }}
    >
      {/* Fixed header */}
      <Box
        style={{
          padding: '14px 16px',
          borderBottom: '1px solid var(--mantine-color-gray-2)',
          flexShrink: 0,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <Text fw={700} style={{ fontSize: 16, color: 'var(--mantine-color-navy-7)', letterSpacing: '-0.01em' }}>
          Filter flights
        </Text>
        <ActionIcon
          onClick={onClose}
          variant="subtle"
          color="gray"
          radius="xl"
          size={32}
          aria-label="Close filters"
        >
          <X size={18} />
        </ActionIcon>
      </Box>

      {/* Scrollable filter content */}
      <ScrollArea style={{ flex: 1, minHeight: 0 }}>
        <Box p="md">
          <Accordion multiple defaultValue={ACCORDION_ITEM_VALUES} variant="default">
            {/* Price */}
            <Accordion.Item value="price">
              <Accordion.Control>
                <Text fw={500}>Price</Text>
              </Accordion.Control>
              <Accordion.Panel>
                <Box px={4}>
                  <RangeSlider
                    value={priceValue}
                    onChange={setLocalPriceValue}
                    onChangeEnd={handlePriceChange}
                    min={bounds.priceMin}
                    max={bounds.priceMax}
                    step={Math.max(1, Math.floor((bounds.priceMax - bounds.priceMin) / 100))}
                    label={(v) => `$${v.toLocaleString()}`}
                  />
                  <Group justify="space-between" mt={8}>
                    <Text size="sm">${priceValue[0].toLocaleString()}</Text>
                    <Text size="sm">${priceValue[1].toLocaleString()}</Text>
                  </Group>
                </Box>
              </Accordion.Panel>
            </Accordion.Item>

            {/* Stops */}
            <Accordion.Item value="stops">
              <Accordion.Control>
                <Text fw={500}>Stops</Text>
              </Accordion.Control>
              <Accordion.Panel>
                {isRoundTrip
                  ? renderTabbed(
                      stopsTab,
                      setStopsTab,
                      stopsOutboundContent,
                      stopsInboundContent,
                      'Stops outbound or inbound'
                    )
                  : stopsOutboundContent}
              </Accordion.Panel>
            </Accordion.Item>

            {/* Airlines */}
            {airlines.length > 0 && (
              <Accordion.Item value="airlines">
                <Accordion.Control>
                  <Text fw={500}>Airlines</Text>
                </Accordion.Control>
                <Accordion.Panel>
                  <Stack gap={4}>
                    {airlines.map(({ code, name }) => (
                      <Checkbox
                        key={code}
                        label={name}
                        checked={filterState.airlines.includes(code)}
                        onChange={() => toggleAirline(code)}
                      />
                    ))}
                  </Stack>
                </Accordion.Panel>
              </Accordion.Item>
            )}

            {/* Cabin class */}
            {cabinClasses.length > 0 && (
              <Accordion.Item value="cabin">
                <Accordion.Control>
                  <Text fw={500}>Cabin class</Text>
                </Accordion.Control>
                <Accordion.Panel>
                  <Stack gap={4}>
                    {cabinClasses.map((cabin) => (
                      <Checkbox
                        key={cabin}
                        label={cabin}
                        checked={filterState.cabinClasses.includes(cabin)}
                        onChange={() => toggleCabin(cabin)}
                      />
                    ))}
                  </Stack>
                </Accordion.Panel>
              </Accordion.Item>
            )}

            {/* Departure airports */}
            {(departureAirports.length > 0 ||
              (isRoundTrip && returnDepartureAirports.length > 0)) && (
              <Accordion.Item value="departure-airports">
                <Accordion.Control>
                  <Text fw={500}>Departure airports</Text>
                </Accordion.Control>
                <Accordion.Panel>
                  {isRoundTrip
                    ? renderTabbed(
                        departureAirportTab,
                        setDepartureAirportTab,
                        departureAirportsOutboundContent,
                        departureAirportsInboundContent,
                        'Departure airports outbound or inbound'
                      )
                    : departureAirportsOutboundContent}
                </Accordion.Panel>
              </Accordion.Item>
            )}

            {/* Arrival airports */}
            {(arrivalAirports.length > 0 || (isRoundTrip && returnArrivalAirports.length > 0)) && (
              <Accordion.Item value="arrival-airports">
                <Accordion.Control>
                  <Text fw={500}>Arrival airports</Text>
                </Accordion.Control>
                <Accordion.Panel>
                  {isRoundTrip
                    ? renderTabbed(
                        arrivalAirportTab,
                        setArrivalAirportTab,
                        arrivalAirportsOutboundContent,
                        arrivalAirportsInboundContent,
                        'Arrival airports outbound or inbound'
                      )
                    : arrivalAirportsOutboundContent}
                </Accordion.Panel>
              </Accordion.Item>
            )}

            {/* Duration */}
            <Accordion.Item value="duration">
              <Accordion.Control>
                <Text fw={500}>Duration</Text>
              </Accordion.Control>
              <Accordion.Panel>
                {isRoundTrip
                  ? renderTabbed(
                      durationTab,
                      setDurationTab,
                      durationOutboundContent,
                      durationInboundContent,
                      'Duration outbound or inbound'
                    )
                  : durationOutboundContent}
              </Accordion.Panel>
            </Accordion.Item>

            {/* Departure time */}
            <Accordion.Item value="departure-time">
              <Accordion.Control>
                <Text fw={500}>Departure time</Text>
              </Accordion.Control>
              <Accordion.Panel>
                {isRoundTrip
                  ? renderTabbed(
                      departureTimeTab,
                      setDepartureTimeTab,
                      departureTimeOutboundContent,
                      departureTimeInboundContent,
                      'Departure time outbound or inbound'
                    )
                  : departureTimeOutboundContent}
              </Accordion.Panel>
            </Accordion.Item>

            {/* Arrival time */}
            <Accordion.Item value="arrival-time">
              <Accordion.Control>
                <Text fw={500}>Arrival time</Text>
              </Accordion.Control>
              <Accordion.Panel>
                {isRoundTrip
                  ? renderTabbed(
                      arrivalTimeTab,
                      setArrivalTimeTab,
                      arrivalTimeOutboundContent,
                      arrivalTimeInboundContent,
                      'Arrival time outbound or inbound'
                    )
                  : arrivalTimeOutboundContent}
              </Accordion.Panel>
            </Accordion.Item>
          </Accordion>
        </Box>
      </ScrollArea>

      {/* Fixed footer */}
      <Box
        style={{
          padding: '12px 16px',
          borderTop: '1px solid var(--mantine-color-gray-2)',
          flexShrink: 0,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <Button variant="subtle" color="gray" onClick={handleClearAll}>
          Clear all
        </Button>
        <Button onClick={onClose} style={{ backgroundColor: 'var(--mantine-color-navy-7)' }}>
          Show {filteredFlightCount} {flightLabel}
        </Button>
      </Box>
    </Modal>
  );
}

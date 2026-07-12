import { useState, useMemo, useEffect } from 'react';
import {
  Combobox,
  Group,
  Loader,
  Stack,
  Text,
  TextInput,
  useCombobox,
  type TextInputProps,
} from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import { useSearchAirportsQuery } from '@/api/flightsApi';
import { buildAirportAutocompleteOptions } from '@/features/flights/utils/airportAutocompleteOptions';
import type { AirportOption } from '@/types/flights';

export type { AirportOption };

interface AirportAutocompleteProps {
  value: string;
  onChange: (value: string, airport?: AirportOption) => void;
  placeholder?: string;
  label?: string;
  /** Rendered inside `TextInput.leftSection` (e.g. plane icon for "From"). */
  startAdornment?: React.ReactNode;
  error?: boolean;
  helperText?: string;
  fullWidth?: boolean;
  /** MUI's `size="small" | "medium"`. Mapped to Mantine's `size` (`xs` / `sm`). */
  size?: 'small' | 'medium';
}

const SIZE_MAP: Record<NonNullable<AirportAutocompleteProps['size']>, TextInputProps['size']> = {
  small: 'xs',
  medium: 'sm',
};

const INPUT_STYLES = {
  input: {
    backgroundColor: 'var(--mantine-color-gray-0)',
    borderRadius: 'var(--mantine-radius-md)',
  },
} as const;

/**
 * Each option is keyed by a unique synthetic value (city options can share an
 * IATA-less placeholder, so we encode the airport identity into the value
 * string and look up the AirportOption from the map at submit-time).
 */
function optionKey(o: AirportOption): string {
  return o.isCityOption
    ? `city:${o.city}:${o.country}`
    : `iata:${o.iata}`;
}

export function AirportAutocomplete({
  value,
  onChange,
  placeholder = 'City or airport',
  label,
  startAdornment,
  error,
  helperText,
  fullWidth = true,
  size = 'medium',
}: AirportAutocompleteProps) {
  const [inputValue, setInputValue] = useState(value);
  const combobox = useCombobox({
    onDropdownClose: () => combobox.resetSelectedOption(),
  });

  // Sync inputValue with value prop when it changes externally (e.g. parent
  // resets after form submit, sets via swap-airports).
  useEffect(() => {
    if (value !== inputValue) {
      setInputValue(value);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  // Debounce the query (not the visible input) so each keystroke doesn't fire
  // its own request. 250ms is short enough to feel responsive while collapsing
  // typical typing bursts ("Lond" → "Londo" → "London") into one request.
  const [debouncedQuery] = useDebouncedValue(inputValue.trim(), 250);

  // Dual gating: `shouldSearch` (debounced) controls when we actually fire a
  // network request, while `inputReady` (live input) controls dropdown-open UX
  // so click/focus reacts immediately on the first 2 typed chars without
  // waiting for the 250ms debounce. The pair also drives the loader: we show
  // it while the input is ready but the debounce/network hasn't resolved, so
  // stale results from the previous query don't flash during fast typing.
  const shouldSearch = debouncedQuery.length >= 2;
  const inputReady = inputValue.trim().length >= 2;
  const debouncePending = inputReady && inputValue.trim() !== debouncedQuery;
  const { data: airports = [], isFetching } = useSearchAirportsQuery(
    { query: debouncedQuery, limit: 50 },
    { skip: !shouldSearch }
  );

  const options = useMemo(
    () => buildAirportAutocompleteOptions(airports),
    [airports]
  );

  // Map from synthetic key → AirportOption for O(1) lookup on submit.
  const optionByKey = useMemo(() => {
    const map = new Map<string, AirportOption>();
    options.forEach((o) => map.set(optionKey(o), o));
    return map;
  }, [options]);

  const handleOptionSubmit = (key: string) => {
    const airport = optionByKey.get(key);
    if (!airport) return;
    const displayValue = airport.isCityOption ? airport.city : airport.iata;
    setInputValue(displayValue);
    onChange(displayValue, airport);
    combobox.closeDropdown();
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const next = e.currentTarget.value;
    setInputValue(next);
    onChange(next, undefined);
    combobox.openDropdown();
    combobox.updateSelectedOptionIndex();
  };

  const showLoader = debouncePending || (isFetching && shouldSearch);
  const showEmptyMessage =
    shouldSearch && !isFetching && !debouncePending && options.length === 0;

  return (
    <Combobox
      store={combobox}
      withinPortal
      zIndex={1400}
      onOptionSubmit={handleOptionSubmit}
    >
      <Combobox.Target>
        <TextInput
          value={inputValue}
          onChange={handleInputChange}
          // Don't open the dropdown if there's nothing to show — empty
          // <Combobox.Options /> renders as a small empty floating box otherwise.
          onClick={() => {
            if (inputReady) combobox.openDropdown();
          }}
          onFocus={() => {
            if (inputReady) combobox.openDropdown();
          }}
          onBlur={() => combobox.closeDropdown()}
          label={label}
          placeholder={placeholder}
          error={error ? helperText || true : undefined}
          description={!error && helperText ? helperText : undefined}
          leftSection={startAdornment}
          rightSection={showLoader ? <Loader size="xs" /> : null}
          size={SIZE_MAP[size]}
          styles={INPUT_STYLES}
          w={fullWidth ? '100%' : 'auto'}
          role="combobox"
        />
      </Combobox.Target>
      <Combobox.Dropdown>
        <Combobox.Options mah={400} style={{ overflowY: 'auto' }}>
          {showEmptyMessage ? (
            <Combobox.Empty>No airports found</Combobox.Empty>
          ) : (
            options.map((option) => {
              const key = optionKey(option);
              return (
                <Combobox.Option key={key} value={key}>
                  <AirportOptionRow option={option} />
                </Combobox.Option>
              );
            })
          )}
        </Combobox.Options>
      </Combobox.Dropdown>
    </Combobox>
  );
}

function AirportOptionRow({ option }: { option: AirportOption }) {
  const locationText = option.state
    ? `${option.state}, ${option.country}`
    : option.country;
  return (
    <Group gap="sm" wrap="nowrap" w="100%">
      <Text component="span" size="lg" miw={24} ta="center">
        {option.isCityOption ? '📍' : '✈️'}
      </Text>
      <Stack gap={2} style={{ flex: 1, minWidth: 0 }}>
        <Group gap="xs" align="baseline" wrap="wrap">
          <Text size="sm" fw={500}>
            {option.name}
          </Text>
          {!option.isCityOption && option.iata && (
            <Text size="sm" c="dimmed">
              ({option.iata})
            </Text>
          )}
        </Group>
        <Text size="xs" c="dimmed">
          {locationText}
        </Text>
      </Stack>
    </Group>
  );
}

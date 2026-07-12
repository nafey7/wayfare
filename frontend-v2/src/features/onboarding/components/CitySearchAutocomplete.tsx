import { useEffect, useMemo, useState } from 'react';
import { Autocomplete, type AutocompleteProps } from '@mantine/core';
import { useDebounce } from '@/hooks/useDebounce';
import {
  searchCitiesOpenMeteo,
  type CitySearchOption,
} from '@/features/onboarding/openMeteoGeocoding';

export type { CitySearchOption } from '@/features/onboarding/openMeteoGeocoding';

export interface CitySearchAutocompleteProps {
  label: string;
  placeholder?: string;
  value: CitySearchOption | null;
  onChange: (next: CitySearchOption | null) => void;
  disabled?: boolean;
  /** When set, search results are limited to this country (ISO2), e.g. after country pick on onboarding. */
  filterCountryCode?: string;
}

const DEBOUNCE_MS = 350;

/**
 * Mantine Autocomplete that loads city · country options from Open-Meteo as the user types.
 * Each query is sent to a third party from the client; see `openMeteoGeocoding.ts` (OPEN_METEO_GEO).
 */
export function CitySearchAutocomplete({
  label,
  placeholder = 'Start typing a city',
  value,
  onChange,
  disabled = false,
  filterCountryCode,
}: CitySearchAutocompleteProps) {
  const [inputValue, setInputValue] = useState(value?.label ?? '');
  const [options, setOptions] = useState<CitySearchOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const debouncedQuery = useDebounce(inputValue, DEBOUNCE_MS);

  useEffect(() => {
    setInputValue(value?.label ?? '');
  }, [value?.label]);

  useEffect(() => {
    const q = debouncedQuery.trim();
    if (q.length < 2) {
      setOptions([]);
      setLoading(false);
      setError(null);
      return;
    }

    const ac = new AbortController();
    setLoading(true);
    setError(null);
    void searchCitiesOpenMeteo(q, ac.signal, filterCountryCode)
      .then((next) => {
        if (ac.signal.aborted) return;
        setOptions(next);
      })
      .catch((e: unknown) => {
        if (ac.signal.aborted) return;
        setError(e instanceof Error ? e.message : 'Search failed');
        setOptions([]);
      })
      .finally(() => {
        if (!ac.signal.aborted) setLoading(false);
      });
    return () => ac.abort();
  }, [debouncedQuery, filterCountryCode]);

  const optionsWithValue = useMemo(() => {
    if (!value) return options;
    if (options.some((o) => o.value === value.value)) return options;
    return [value, ...options];
  }, [options, value]);

  const data: AutocompleteProps['data'] = useMemo(
    () => optionsWithValue.map((o) => ({ value: o.value, label: o.label })),
    [optionsWithValue]
  );

  const noOptionsText =
    inputValue.trim().length < 2
      ? 'Type at least 2 characters'
      : loading
        ? 'Searching…'
        : 'No cities found';

  return (
    <Autocomplete
      disabled={disabled}
      label={label}
      placeholder={placeholder}
      value={inputValue}
      onChange={(v) => {
        setInputValue(v);
        if (!v) {
          onChange(null);
          setError(null);
        }
      }}
      onOptionSubmit={(selectedValue) => {
        const match = optionsWithValue.find((o) => o.value === selectedValue) ?? null;
        onChange(match);
        if (match) setInputValue(match.label);
        setError(null);
      }}
      data={data}
      filter={({ options: items }) => items}
      error={error}
      // Mantine v7 Autocomplete dropdown stays empty when no options match;
      // reflect that hint inline via description until we add a custom Combobox.
      description={inputValue.trim().length > 0 && data.length === 0 ? noOptionsText : undefined}
    />
  );
}

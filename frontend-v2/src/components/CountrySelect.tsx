import { useId } from 'react';
import { Select } from '@mantine/core';
import { countries } from '@/data';

export type CountrySelectVariant = 'country' | 'phone';

export interface CountrySelectProps {
  value: string;
  onChange: (value: string) => void;
  /** 'country' = value is ISO country code (e.g. US). 'phone' = value is dial code (e.g. 1, 44). Default 'country'. */
  variant?: CountrySelectVariant;
  label?: string;
  error?: boolean;
  required?: boolean;
  fullWidth?: boolean;
  size?: 'small' | 'medium';
  id?: string;
  /** When false, hides the phone/calling code in the dropdown options (e.g. for nationality / country of issue). Default true. Ignored when variant='phone'. */
  showPhoneCode?: boolean;
  sx?: object;
}

export function CountrySelect({
  value,
  onChange,
  variant = 'country',
  label = 'Choose a country',
  error = false,
  required = false,
  fullWidth = false,
  size = 'small',
  id,
  showPhoneCode = true,
  sx,
}: CountrySelectProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const isPhone = variant === 'phone';

  // Mantine Select rejects duplicate option values, but multiple countries
  // share dial codes (+1 US/CA, +44 UK/crown deps, +61 AU/CC/CX, …). Always
  // key options by ISO code (unique) and translate at the boundary, so phone
  // variant still emits/accepts dial codes from callers.
  const data = countries.map((c) => ({
    value: c.code,
    label: isPhone
      ? `${c.code} +${c.phone}`
      : `${c.label} (${c.code})${showPhoneCode ? ` +${c.phone}` : ''}`,
  }));

  const selectedCode = isPhone
    ? (countries.find((c) => c.phone === value)?.code ?? null)
    : value || null;

  const handleChange = (v: string | null) => {
    if (!v) {
      onChange('');
      return;
    }
    if (isPhone) {
      onChange(countries.find((c) => c.code === v)?.phone ?? '');
    } else {
      onChange(v);
    }
  };

  const mantineSize = size === 'medium' ? 'md' : 'sm';
  const widthStyle =
    isPhone && !fullWidth ? { width: 140 } : fullWidth ? { width: '100%' } : undefined;

  return (
    <Select
      id={inputId}
      data={data}
      value={selectedCode}
      onChange={handleChange}
      label={label}
      error={error}
      required={required}
      size={mantineSize}
      searchable
      autoCorrect="off"
      autoComplete="new-password"
      style={{ ...(widthStyle ?? {}), ...((sx as React.CSSProperties) ?? {}) }}
    />
  );
}

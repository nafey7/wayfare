import { Box, Group, UnstyledButton } from '@mantine/core';
import { LANDING_TOKENS } from '@/features/landing/landingTokens';
import type { PreferenceOption } from '@/features/profile/types/preferences';
import { SectionHeader } from '../shared';

const CHIP_NAVY = '#171B63';
const CHIP_LINE = '#E4E6F5';
const CHIP_TEXT = '#636e9d';
const CHIP_HOVER_BG = '#F3F5FE';

/**
 * Shared chip styles used by preference / detail sections. Plain CSS object,
 * spread into `style` props.
 */
export const chipBaseStyle: React.CSSProperties = {
  height: 36,
  borderRadius: 50,
  paddingLeft: 14,
  paddingRight: 14,
  paddingTop: 7,
  paddingBottom: 7,
  minHeight: 0,
  margin: 0,
  fontSize: 13,
  fontWeight: 500,
  lineHeight: 1.43,
  letterSpacing: 0.1,
  fontFamily: LANDING_TOKENS.fontFamily.display,
  display: 'inline-flex',
  alignItems: 'center',
  cursor: 'pointer',
  border: 'none',
  background: 'transparent',
  transition: 'all 120ms',
};

export { SectionHeader } from '../shared';

export function RadioField({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: PreferenceOption<string>[];
  value: string | null;
  onChange: (v: string) => void;
}) {
  return (
    <Box style={{ display: 'flex', flexDirection: 'column', gap: 8, width: '100%' }}>
      <Box>
        <SectionHeader label={label} variant="small" />
      </Box>
      <Group gap={12} wrap="wrap">
        {options.map((opt) => {
          const selected = value === opt.value;
          return (
            <UnstyledButton
              key={opt.id}
              onClick={() => onChange(selected ? '' : opt.value)}
              style={{
                ...chipBaseStyle,
                ...(selected
                  ? {
                      backgroundColor: CHIP_NAVY,
                      color: 'white',
                      border: `1px solid ${CHIP_NAVY}`,
                      fontWeight: 600,
                    }
                  : {
                      border: `1px solid ${CHIP_LINE}`,
                      color: CHIP_TEXT,
                      backgroundColor: 'white',
                    }),
              }}
              onMouseEnter={(e) => {
                if (!selected) {
                  (e.currentTarget as HTMLElement).style.backgroundColor = CHIP_HOVER_BG;
                  (e.currentTarget as HTMLElement).style.borderColor = CHIP_NAVY;
                }
              }}
              onMouseLeave={(e) => {
                if (!selected) {
                  (e.currentTarget as HTMLElement).style.backgroundColor = 'white';
                  (e.currentTarget as HTMLElement).style.borderColor = CHIP_LINE;
                }
              }}
            >
              {opt.label}
            </UnstyledButton>
          );
        })}
      </Group>
    </Box>
  );
}

export function ChipSection({
  label,
  options,
  selectedValues,
  onToggle,
}: {
  label: string;
  options: PreferenceOption<string>[];
  selectedValues: Set<string>;
  onToggle: (value: string) => void;
}) {
  return (
    <Box style={{ display: 'flex', flexDirection: 'column', gap: 8, width: '100%' }}>
      <Box>
        <SectionHeader label={label} variant="small" />
      </Box>
      <Group gap={12} wrap="wrap">
        {options.map((opt) => {
          const selected = selectedValues.has(opt.value);
          return (
            <UnstyledButton
              key={opt.id}
              onClick={() => onToggle(opt.value)}
              style={{
                ...chipBaseStyle,
                ...(selected
                  ? {
                      backgroundColor: CHIP_NAVY,
                      color: 'white',
                      border: `1px solid ${CHIP_NAVY}`,
                      fontWeight: 600,
                    }
                  : {
                      border: `1px solid ${CHIP_LINE}`,
                      color: CHIP_TEXT,
                      backgroundColor: 'white',
                    }),
              }}
              onMouseEnter={(e) => {
                if (!selected) {
                  (e.currentTarget as HTMLElement).style.backgroundColor = CHIP_HOVER_BG;
                  (e.currentTarget as HTMLElement).style.borderColor = CHIP_NAVY;
                }
              }}
              onMouseLeave={(e) => {
                if (!selected) {
                  (e.currentTarget as HTMLElement).style.backgroundColor = 'white';
                  (e.currentTarget as HTMLElement).style.borderColor = CHIP_LINE;
                }
              }}
            >
              {opt.label}
            </UnstyledButton>
          );
        })}
      </Group>
    </Box>
  );
}

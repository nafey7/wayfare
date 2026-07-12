import { Group, Text } from '@mantine/core';
import { LANDING_TOKENS } from '@/features/landing/landingTokens';

const VARIANT_STYLES = {
  small: {
    fontSize: 13,
    fontWeight: 500,
    lineHeight: 1.25,
    letterSpacing: 0.1,
  },
  default: {
    fontSize: 16,
    fontWeight: 600,
    lineHeight: 1.25,
    letterSpacing: 0.1,
  },
  large: {
    fontSize: 18,
    fontWeight: 700,
    lineHeight: 25 / 18,
    letterSpacing: 0.15,
  },
  main: {
    fontSize: 22,
    fontWeight: 700,
    lineHeight: 1.27,
    letterSpacing: 0,
  },
} as const;

export interface SectionHeaderProps {
  label: string;
  variant?: keyof typeof VARIANT_STYLES;
  action?: React.ReactNode;
  px?: number;
}

/** Shared section header used across profile components. */
export function SectionHeader({
  label,
  variant = 'default',
  action,
  px,
}: SectionHeaderProps) {
  const baseStyle: React.CSSProperties = {
    ...VARIANT_STYLES[variant],
    color: LANDING_TOKENS.textColor,
    margin: 0,
    display: 'block',
    paddingBottom: variant === 'small' ? 0 : 10,
    fontFamily: LANDING_TOKENS.fontFamily.display,
    ...(px != null && { paddingLeft: px * 8, paddingRight: px * 8 }),
  };

  if (action) {
    return (
      <Group justify="space-between" align="center" pb={10}>
        <Text component="span" style={baseStyle}>
          {label}
        </Text>
        {action}
      </Group>
    );
  }

  return (
    <Text component="span" style={baseStyle}>
      {label}
    </Text>
  );
}

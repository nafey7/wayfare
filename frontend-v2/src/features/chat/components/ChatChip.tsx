import { UnstyledButton } from '@mantine/core';
import { Lightbulb } from 'lucide-react';
import type { CSSProperties, ReactNode } from 'react';

export type ChatChipVariant = 'active' | 'selected' | 'signIn';

export interface ChatChipProps {
  label: string;
  variant?: ChatChipVariant;
  onClick?: () => void;
}

const BASE: CSSProperties = {
  padding: '6px 14px',
  borderRadius: 9999,
  fontSize: 14,
  fontWeight: 500,
  display: 'inline-flex',
  alignItems: 'center',
  gap: 6,
  lineHeight: 1.35,
  transition: 'all 120ms ease',
};

const ACTIVE: CSSProperties = {
  ...BASE,
  background: 'transparent',
  color: 'var(--mantine-color-navy-5)',
  border: '1px solid var(--mantine-color-navy-1)',
  cursor: 'pointer',
};

const SELECTED: CSSProperties = {
  ...BASE,
  background: 'transparent',
  color: 'var(--mantine-color-navy-3)',
  border: '1px dashed var(--mantine-color-navy-2)',
  cursor: 'default',
};

/**
 * Single chat suggestion chip. Three variants cover every state in the
 * chat welcome flow:
 *
 *  - `active` (default): tappable hint chip, subtle design — `navy[1]` border + `navy[5]` text
 *  - `selected`: post-click state — dashed border + `navy[3]` text, not interactive
 *  - `signIn`: same treatment as `active` + lucide Lightbulb icon.
 *     Used in the guest state to nudge sign-in without a saturated CTA.
 */
export function ChatChip({
  label,
  variant = 'active',
  onClick,
}: ChatChipProps) {
  const style = variant === 'selected' ? SELECTED : ACTIVE;
  const isDisabled = variant === 'selected';

  let leadingIcon: ReactNode = null;
  if (variant === 'signIn') {
    leadingIcon = <Lightbulb size={13} strokeWidth={2.2} />;
  }

  return (
    <UnstyledButton
      onClick={isDisabled ? undefined : onClick}
      disabled={isDisabled}
      style={style}
      aria-disabled={isDisabled}
    >
      {leadingIcon}
      {label}
    </UnstyledButton>
  );
}

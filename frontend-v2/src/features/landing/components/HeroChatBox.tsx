import { useCallback, useRef, useState } from 'react';
import { Box, Text } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { SendHorizonal } from 'lucide-react';

import { NAV_NAVY_DEEP as NAVY_DEEP } from '@/theme/navTokens';

import { NAVY, NAVY_SOFT, LAVENDER, LAVENDER_SOFT } from '../landingColors';

export interface HeroChatBoxDomIds {
  input?: string;
  sendButton?: string;
  root?: string;
}

export interface HeroChatBoxProps {
  onSubmit: (value: string) => void;
  placeholder?: string;
  helperText?: string;
  /** Size variant — `hero` is prominent (default), `compact` is slightly smaller. */
  variant?: 'hero' | 'compact';
  domIds?: HeroChatBoxDomIds;
  ariaLabel?: string;
}

/**
 * Prominent chat input used on the public landing page (hero + closing section).
 *
 * Visually larger than `NavbarChatSearch`. The auth / public-chat / login-modal
 * routing logic lives in `useLandingPageController.handleSearchSubmit`, which is
 * passed in via `onSubmit`.
 */
export function HeroChatBox({
  onSubmit,
  placeholder = 'Where do you want to go?',
  helperText = 'Voya AI plans flights, hotels, and a day-by-day itinerary — just describe it.',
  variant = 'hero',
  domIds,
  ariaLabel = 'Chat with Voya AI',
}: HeroChatBoxProps) {
  const isMdUp = useMediaQuery('(min-width: 48em)');
  const [value, setValue] = useState('');
  const [focused, setFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const isHero = variant === 'hero';
  const inputFontSize = isHero ? (isMdUp ? 18 : 15) : (isMdUp ? 16 : 14);
  const padInline = isHero ? (isMdUp ? 28 : 18) : (isMdUp ? 20 : 14);
  const padBlock = isHero ? (isMdUp ? 10 : 8) : 6;
  const buttonSize = isHero ? (isMdUp ? 52 : 44) : (isMdUp ? 44 : 38);
  const iconSize = isHero ? 22 : 18;

  const handleSubmit = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed) {
      inputRef.current?.focus();
      return;
    }
    onSubmit(trimmed);
  }, [onSubmit, value]);

  const borderColor = focused ? LAVENDER : LAVENDER_SOFT;
  const bgColor = 'white';
  const shadow = focused
    ? '0 10px 30px rgba(23,27,99,.16)'
    : isHero
      ? '0 8px 24px rgba(23,27,99,.10)'
      : '0 4px 14px rgba(23,27,99,.08)';

  return (
    <Box
      id={domIds?.root}
      style={{
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'stretch',
        gap: isHero ? 10 : 8,
      }}
    >
      <Box
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          gap: isHero ? 12 : 8,
          backgroundColor: bgColor,
          border: `1.5px solid ${borderColor}`,
          borderRadius: 9999,
          paddingLeft: padInline,
          paddingRight: 6,
          paddingTop: padBlock,
          paddingBottom: padBlock,
          boxShadow: shadow,
          transition: 'border-color 150ms, box-shadow 200ms, transform 150ms',
          transform: focused ? 'translateY(-1px)' : 'translateY(0)',
        }}
      >
        <input
          ref={inputRef}
          id={domIds?.input}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              handleSubmit();
            }
          }}
          placeholder={placeholder}
          aria-label={ariaLabel}
          style={{
            flex: 1,
            minWidth: 0,
            border: 'none',
            outline: 'none',
            background: 'transparent',
            color: NAVY,
            fontSize: inputFontSize,
            fontWeight: 500,
            lineHeight: 1.4,
            paddingBlock: 6,
            fontFamily: 'inherit',
          }}
        />
        <Box
          component="button"
          type="button"
          id={domIds?.sendButton}
          onClick={handleSubmit}
          aria-label="Send to Voya AI"
          style={{
            width: buttonSize,
            height: buttonSize,
            borderRadius: '50%',
            backgroundColor: NAVY,
            color: 'white',
            flexShrink: 0,
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: 'none',
            cursor: 'pointer',
            transition: 'background 150ms, transform 150ms',
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLElement).style.backgroundColor = NAVY_DEEP;
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLElement).style.backgroundColor = NAVY;
          }}
        >
          <SendHorizonal size={iconSize} strokeWidth={2.2} />
        </Box>
      </Box>
      {helperText && (
        <Text
          component="p"
          style={{
            fontSize: isHero ? 13 : 12,
            color: NAVY_SOFT,
            textAlign: 'center',
            lineHeight: 1.5,
            margin: 0,
            paddingInline: 8,
          }}
        >
          {helperText}
        </Text>
      )}
    </Box>
  );
}

import { Box, Stack, Text } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { Sparkles } from 'lucide-react';

import { NAVY, NAVY_SOFT, LAVENDER, MIST_HERO } from '../landingColors';
import { HeroChatBox } from './HeroChatBox';

export interface ClosingChatSectionDomIds {
  section?: string;
  heading?: string;
  chatInput?: string;
  chatSendButton?: string;
}

export interface ClosingChatSectionProps {
  onSearchSubmit: (value: string) => void;
  title?: string;
  subtitle?: string;
  eyebrow?: string;
  domIds?: ClosingChatSectionDomIds;
}

/**
 * Closing CTA section for the public landing page — a prominent chat input on
 * a mist background, designed to recapture intent after scrolling.
 */
export function ClosingChatSection({
  onSearchSubmit,
  title = 'Ready when you are.',
  subtitle = 'Tell Voya AI where you want to go — get flights, hotels and a full itinerary in minutes.',
  eyebrow = 'Start planning',
  domIds,
}: ClosingChatSectionProps) {
  const isMdUp = useMediaQuery('(min-width: 48em)');

  return (
    <Box
      id={domIds?.section}
      component="section"
      {...(domIds?.heading ? { 'aria-labelledby': domIds.heading } : {})}
      style={{
        position: 'relative',
        backgroundColor: MIST_HERO,
        paddingBlock: isMdUp ? 96 : 64,
        paddingInline: isMdUp ? 32 : 16,
        overflow: 'hidden',
      }}
    >
      {/* Decorative glow */}
      <Box
        aria-hidden
        style={{
          position: 'absolute',
          top: -120,
          left: '50%',
          transform: 'translateX(-50%)',
          width: 540,
          height: 540,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(154,162,197,0.35) 0%, rgba(234,238,251,0) 65%)',
          pointerEvents: 'none',
        }}
      />

      <Stack
        align="center"
        gap={isMdUp ? 24 : 18}
        style={{
          position: 'relative',
          maxWidth: 720,
          marginInline: 'auto',
          textAlign: 'center',
        }}
      >
        {eyebrow && (
          <Box
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              paddingInline: 14,
              paddingBlock: 6,
              borderRadius: 100,
              backgroundColor: 'white',
              border: `1px solid ${LAVENDER}`,
            }}
          >
            <Sparkles size={14} color={NAVY} />
            <Text
              component="span"
              style={{
                fontSize: 12,
                fontWeight: 700,
                letterSpacing: '0.08em',
                color: NAVY,
                textTransform: 'uppercase',
              }}
            >
              {eyebrow}
            </Text>
          </Box>
        )}

        <Text
          id={domIds?.heading}
          component="h2"
          style={{
            fontSize: isMdUp ? 44 : 28,
            fontWeight: 900,
            color: NAVY,
            letterSpacing: '-.025em',
            lineHeight: 1.1,
            margin: 0,
          }}
        >
          {title}
        </Text>

        <Text
          style={{
            fontSize: isMdUp ? 17 : 14,
            fontWeight: 400,
            lineHeight: 1.55,
            color: NAVY_SOFT,
            maxWidth: 560,
            margin: 0,
          }}
        >
          {subtitle}
        </Text>

        <Box style={{ width: '100%', maxWidth: 600, marginTop: isMdUp ? 8 : 4 }}>
          <HeroChatBox
            onSubmit={onSearchSubmit}
            variant="hero"
            placeholder="Try: 5 days in Lisbon next month, budget-friendly"
            helperText="Press Enter to send — Voya AI takes it from there."
            {...(domIds?.chatInput || domIds?.chatSendButton
              ? {
                  domIds: {
                    ...(domIds.chatInput ? { input: domIds.chatInput } : {}),
                    ...(domIds.chatSendButton ? { sendButton: domIds.chatSendButton } : {}),
                  },
                }
              : {})}
          />
        </Box>
      </Stack>
    </Box>
  );
}

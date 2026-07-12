import { Box, Stack, Text, Button } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { ArrowRight } from 'lucide-react';
import { NAVY, SLATE, LINE } from '../landingColors';

export interface EditorialCardDomIds {
  section?: string;
  heading?: string;
  cta?: string;
}

export interface EditorialCardProps {
  eyebrow?: string;
  title: string;
  body: string;
  meta?: string[];
  ctaLabel?: string;
  onCtaClick?: () => void;
  onClick?: () => void;
  imageUrl?: string;
  /** Text overlaid on the gradient fallback when no imageUrl. Defaults to the last word of title. */
  imageLabel?: string;
  /** Stable marketing ids (only wired on `/`). */
  domIds?: EditorialCardDomIds;
}

export function EditorialCard({
  eyebrow = 'Voya picks · this week',
  title,
  body,
  meta,
  ctaLabel = 'See the trip',
  onCtaClick,
  onClick,
  imageUrl,
  imageLabel,
  domIds,
}: EditorialCardProps) {
  const resolvedImageLabel = imageLabel ?? title.split(' ').pop()?.toUpperCase() ?? '';
  const handleCardClick = onClick ?? onCtaClick;
  const isMdUp = useMediaQuery('(min-width: 48em)');

  return (
    <Box
      id={domIds?.section}
      component="section"
      style={{
        backgroundColor: 'white',
        paddingBlock: isMdUp ? 56 : 32,
        paddingInline: isMdUp ? 32 : 16,
      }}
    >
      <Box
        onClick={handleCardClick}
        style={{
          maxWidth: 1120,
          marginInline: 'auto',
          display: 'grid',
          gridTemplateColumns: isMdUp ? '1.1fr 1fr' : '1fr',
          borderRadius: isMdUp ? 24 : 16,
          overflow: 'hidden',
          backgroundColor: '#FAF7F2',
          border: `1px solid ${LINE}`,
          cursor: handleCardClick ? 'pointer' : 'default',
        }}
      >
        {/* Left: image / gradient */}
        <Box
          style={{
            minHeight: isMdUp ? 460 : 200,
            backgroundImage: imageUrl
              ? `url(${imageUrl})`
              : 'linear-gradient(135deg, #F4D9C0 0%, #D9A678 35%, #B07A4A 65%, #6E4624 100%)',
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            position: 'relative',
          }}
        >
          {!imageUrl && resolvedImageLabel && (
            <Box
              style={{
                position: 'absolute',
                bottom: 24,
                left: 28,
                fontSize: 28,
                fontWeight: 900,
                color: 'white',
                letterSpacing: '.25em',
                opacity: 0.85,
                textShadow: '0 2px 12px rgba(0,0,0,.4)',
              }}
            >
              {resolvedImageLabel}
            </Box>
          )}
        </Box>

        {/* Right: copy */}
        <Stack
          gap={isMdUp ? 18 : 14}
          style={{
            padding: isMdUp ? 48 : 22,
            justifyContent: 'center',
          }}
        >
          <Text style={{
            fontSize: 12,
            fontWeight: 800,
            color: SLATE,
            textTransform: 'uppercase',
            letterSpacing: '.14em',
          }}>
            {eyebrow}
          </Text>

          <Text
            id={domIds?.heading}
            component="h2"
            style={{
              fontSize: isMdUp ? 36 : 28,
              fontWeight: 900,
              color: NAVY,
              lineHeight: 1.1,
              letterSpacing: '-.025em',
              margin: 0,
            }}
          >
            {title}
          </Text>

          <Text style={{ fontSize: 15, color: NAVY, lineHeight: 1.6 }}>
            {body}
          </Text>

          {meta && meta.length > 0 && (
            <Box style={{ display: 'flex', flexWrap: 'wrap', gap: 0, fontSize: 12, color: SLATE }}>
              {meta.map((m, i) => (
                <Box component="span" key={i}>
                  {i > 0 && <Box component="span" style={{ marginInline: 6 }}>·</Box>}
                  {m}
                </Box>
              ))}
            </Box>
          )}

          <Button
            id={domIds?.cta}
            onClick={(e) => { e.stopPropagation(); (onCtaClick ?? onClick)?.(); }}
            rightSection={<ArrowRight size={16} />}
            style={{
              alignSelf: 'flex-start',
              marginTop: 8,
              backgroundColor: NAVY,
              color: 'white',
              borderRadius: 999,
              paddingInline: 26,
              paddingBlock: 12,
              fontSize: 14,
              fontWeight: 700,
              boxShadow: 'none',
              border: 'none',
            }}
          >
            {ctaLabel}
          </Button>
        </Stack>
      </Box>
    </Box>
  );
}

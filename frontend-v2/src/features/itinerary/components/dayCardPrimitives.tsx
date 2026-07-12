import { useState } from 'react';
import { Box } from '@mantine/core';
import { AuthenticatedImage } from './AuthenticatedImage';
import { DAY_GRADIENTS, DAY_ACCENTS } from '../constants/dayColors';
import { ChevronIcon, StarIcon, ArrowRightIcon } from './itineraryIcons';
import { usePlacesImage } from '../hooks/usePlacesImage';
import {
  C_NAVY, C_BORDER, C_NAVY_MID, C_NAVY_LIGHT, C_LABEL,
  C_ROW_HOVER,
  C_CHIP_OVERLAY, C_SHADOW_CARD, C_SHADOW_HOVER, C_SHADOW_ACTIVE,
  C_SHADOW_BTN, C_SHADOW_CARD_HV, C_SHADOW_BTN_EX,
} from '../constants/itineraryColors';

// Re-export icons so consumers can import everything from one place.
export { ChevronIcon, StarIcon, ArrowRightIcon };

// ─── Chip ─────────────────────────────────────────────────────────────────────

export function Chip({ children, solid = false }: { children: React.ReactNode; solid?: boolean }) {
  return (
    <Box
      style={{
        fontSize: 11,
        color: C_LABEL,
        padding: '2px 8px',
        border: solid ? '1px solid transparent' : `1px solid ${C_BORDER}`,
        background: solid ? C_BORDER : 'transparent',
        borderRadius: 9999,
        whiteSpace: 'nowrap',
        lineHeight: 1.5,
      }}
    >
      {children}
    </Box>
  );
}

// ─── Day colors ───────────────────────────────────────────────────────────────

export function computeDayColors(dayNumber: number): { gradient: string; accent: string } {
  const idx = dayNumber - 1;
  return {
    gradient: DAY_GRADIENTS[idx % DAY_GRADIENTS.length] ?? DAY_GRADIENTS[0]!,
    accent: DAY_ACCENTS[idx % DAY_ACCENTS.length] ?? DAY_ACCENTS[0]!,
  };
}

// ─── Card container style ─────────────────────────────────────────────────────

export function dayCardContainerStyle(
  isExpanded: boolean,
  isHovered: boolean,
  isSkipped = false,
): React.CSSProperties {
  return {
    background: 'white',
    borderRadius: 16,
    overflow: 'hidden',
    border: isExpanded
      ? `2px solid ${C_NAVY}`
      : isHovered ? `2px solid ${C_NAVY_LIGHT}` : '2px solid transparent',
    boxShadow: isExpanded
      ? `0 2px 8px ${C_SHADOW_ACTIVE}`
      : isHovered ? `0 16px 36px ${C_SHADOW_CARD_HV}` : `0 1px 3px ${C_SHADOW_CARD}`,
    transition: 'box-shadow 180ms ease, border-color 180ms ease, transform 180ms ease',
    transform: isHovered && !isExpanded ? 'translateY(-4px) scale(1.01)' : 'translateY(0) scale(1)',
    opacity: isSkipped ? 0.55 : 1,
  };
}

// ─── Photo block ──────────────────────────────────────────────────────────────

export interface PhotoBlockProps {
  height: number;
  imageUrl?: string;
  gradient: string;
  dayChipText: string;
  accent: string;
  isExpanded: boolean;
  onToggle?: () => void;
  /** When true, shows ArrowRightIcon instead of ChevronIcon for the expand button. */
  isMobile?: boolean;
  alt: string;
  fallback?: React.ReactNode;
  unavailableLabel?: string;
}

export function PhotoBlock({
  height, imageUrl, gradient, dayChipText, accent,
  isExpanded, onToggle, isMobile = false, alt, fallback, unavailableLabel,
}: PhotoBlockProps) {
  // Lazy-load a hero image for the day card when enrichment didn't supply one.
  // Uses the day title (alt) as the Places search query — "Westminster & the River",
  // "Asakusa Temples & Old Tokyo" etc. are specific enough for good matches.
  const { ref: photoRef, objectUrl: lazyObjectUrl } = usePlacesImage({
    place: alt,
    disabled: !!imageUrl, // skip if enrichment already provided a URL
  });

  return (
    <Box
      ref={photoRef as React.RefObject<HTMLDivElement>}
      style={{
        position: 'relative', width: '100%', height, minHeight: height,
        flexShrink: 0, overflow: 'hidden', background: gradient,
      }}
    >
      {imageUrl && (
        <AuthenticatedImage
          src={imageUrl}
          alt={alt}
          sx={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
          fallback={fallback}
          unavailableLabel={unavailableLabel}
        />
      )}
      {!imageUrl && lazyObjectUrl && (
        <img
          src={lazyObjectUrl}
          alt={alt}
          style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block', transition: 'opacity 300ms' }}
        />
      )}

      {/* TL day chip */}
      <Box
        style={{
          position: 'absolute', top: 12, left: 12, zIndex: 3,
          background: C_CHIP_OVERLAY, color: 'white',
          fontSize: 11, fontWeight: 600, letterSpacing: '-0.01em',
          padding: '5px 10px', borderRadius: 9999,
          backdropFilter: 'blur(6px)',
          display: 'inline-flex', alignItems: 'center', gap: 6,
          pointerEvents: 'none',
        }}
      >
        <Box style={{ width: 6, height: 6, borderRadius: '50%', background: accent }} />
        {dayChipText}
      </Box>

      {/* TR toggle button */}
      {onToggle && (
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); onToggle(); }}
          aria-label={isExpanded ? 'Collapse day' : 'Expand day'}
          style={{
            position: 'absolute', top: 10, right: 10, zIndex: 3,
            width: 32, height: 32, borderRadius: '50%',
            background: isExpanded ? 'white' : C_NAVY,
            boxShadow: isExpanded ? `0 4px 12px ${C_SHADOW_BTN}` : `0 4px 12px ${C_SHADOW_BTN_EX}`,
            border: isExpanded ? `1px solid ${C_BORDER}` : 'none',
            cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'background 120ms, transform 120ms',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.transform = 'scale(1.05)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.transform = 'scale(1)'; }}
        >
          {!isExpanded && isMobile
            ? <ArrowRightIcon />
            : <ChevronIcon direction={isExpanded ? 'up' : 'down'} color={isExpanded ? C_NAVY : '#fff'} size={14} strokeWidth={2.4} />
          }
        </button>
      )}
    </Box>
  );
}

// ─── Timeline row ─────────────────────────────────────────────────────────────

export interface TimelineRowItem {
  title: string;
  description: string;
  imageUrl?: string;
  /** Pre-formatted time range, e.g. "9:00 – 11:00". */
  timeLabel?: string;
  duration?: string;
  cost?: string;
  rating?: number;
  reviewCount?: number;
}

export function TimelineRow({
  item, gradient, accent, isSelected, onClick,
}: {
  item: TimelineRowItem;
  gradient: string;
  accent: string;
  isSelected: boolean;
  onClick?: () => void;
}) {
  const [isHovered, setIsHovered] = useState(false);
  const hasDuration = !!item.duration;
  const hasCost = !!item.cost;
  const hasRating = item.rating !== undefined;

  // Lazy-load image from Google Places when the enrichment pipeline didn't
  // supply one (imageUrl is empty). The Places query uses item.title which
  // maps to the activity's location field (e.g. "Westminster Abbey").
  const { ref: placesRef, objectUrl: lazyObjectUrl } = usePlacesImage({
    place: item.title,
    disabled: !!item.imageUrl, // skip if enrichment already provided a URL
  });

  return (
    <Box
      onClick={onClick ? (e) => { e.stopPropagation(); onClick(); } : undefined}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 10,
        padding: '6px 4px 6px 0',
        borderRadius: 8,
        background: isSelected ? C_BORDER : isHovered ? C_ROW_HOVER : 'transparent',
        boxShadow: isHovered && !isSelected ? `0 2px 8px ${C_SHADOW_HOVER}` : 'none',
        cursor: onClick ? 'pointer' : 'default',
        transition: 'background 120ms, box-shadow 120ms',
      }}
    >
      {/* Timeline dot */}
      <Box
        style={{
          width: 9, height: 9, borderRadius: '50%', flexShrink: 0,
          marginTop: 18,
          background: isSelected ? accent : C_BORDER,
          boxShadow: isSelected ? `0 0 0 2px white, 0 0 0 3.5px ${accent}` : '0 0 0 2px white',
          position: 'relative', zIndex: 1,
        }}
      />

      {/* Thumbnail — gradient while loading; usePlacesImage fires the Places
          API call when this element enters the viewport. */}
      <Box
        ref={placesRef as React.RefObject<HTMLDivElement>}
        style={{ width: 48, height: 48, borderRadius: 8, flexShrink: 0, overflow: 'hidden', background: gradient }}
      >
        {item.imageUrl && (
          <AuthenticatedImage
            src={item.imageUrl}
            alt={item.title}
            sx={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
          />
        )}
        {!item.imageUrl && lazyObjectUrl && (
          <img
            src={lazyObjectUrl}
            alt={item.title}
            style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block', transition: 'opacity 300ms' }}
          />
        )}
      </Box>

      {/* Content */}
      <Box style={{ flex: 1, minWidth: 0, paddingTop: 2, display: 'flex', flexDirection: 'column', gap: 1 }}>
        {item.timeLabel && (
          <Box style={{ fontSize: 10, fontWeight: 600, color: C_LABEL, letterSpacing: '0.02em' }}>
            {item.timeLabel}
          </Box>
        )}
        <Box style={{ fontSize: 13, fontWeight: 600, color: C_NAVY, lineHeight: 1.3, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {item.title}
        </Box>
        <Box style={{ fontSize: 12, color: C_NAVY_MID, lineHeight: 1.35, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {item.description}
        </Box>
        {(hasDuration || hasCost || hasRating) && (
          <Box style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap', marginTop: 4, fontSize: 11, color: C_LABEL }}>
            {hasDuration && <span>{item.duration}</span>}
            {hasCost && (
              <><span style={{ color: C_NAVY_LIGHT }}>·</span><span>{item.cost}</span></>
            )}
            {hasRating && (
              <>
                {(hasDuration || hasCost) && <span style={{ color: C_NAVY_LIGHT }}>·</span>}
                <Box style={{ display: 'inline-flex', alignItems: 'center', gap: 2 }}>
                  <StarIcon />
                  <span>{item.rating}</span>
                  {item.reviewCount !== undefined && (
                    <span>({item.reviewCount.toLocaleString()})</span>
                  )}
                </Box>
              </>
            )}
          </Box>
        )}
      </Box>
    </Box>
  );
}

import { useState } from 'react';
import { Group, UnstyledButton, Box } from '@mantine/core';

// ── Types ─────────────────────────────────────────────────────────────────────

export type HotelSortKey = 'best' | 'cheapest' | 'top-reviews';
export type StarFilter = '3plus' | '4plus' | '5only' | null;

export interface HotelSortFilterBarProps {
  sortValues?: { best: string; cheapest: string; 'top-reviews': string };
  defaultSort?: HotelSortKey;
  defaultStars?: StarFilter;
  onOpenFiltersPanel?: () => void;
  onSortChange?: (key: HotelSortKey) => void;
  onStarsChange?: (stars: StarFilter) => void;
}

// ── Icons ─────────────────────────────────────────────────────────────────────

const BASE_SVG = {
  viewBox: '0 0 24 24',
  fill: 'none',
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
};

function IconSparkle({ size = 12, stroke = '#636e9d' }: { size?: number; stroke?: string }) {
  return (
    <svg {...BASE_SVG} width={size} height={size} stroke={stroke} strokeWidth={1.75}>
      <path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.582a.5.5 0 0 1 0 .962L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z" />
    </svg>
  );
}

function IconDollar({ size = 12, stroke = '#636e9d' }: { size?: number; stroke?: string }) {
  return (
    <svg {...BASE_SVG} width={size} height={size} stroke={stroke} strokeWidth={1.75}>
      <path d="M12 2v20" />
      <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
    </svg>
  );
}

function IconStar5({ size = 12, stroke = '#636e9d' }: { size?: number; stroke?: string }) {
  return (
    <svg {...BASE_SVG} width={size} height={size} stroke={stroke} strokeWidth={1.75}>
      <path d="m12 2 3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
    </svg>
  );
}

function IconDots({ size = 14, stroke = '#636e9d' }: { size?: number; stroke?: string }) {
  return (
    <svg {...BASE_SVG} width={size} height={size} stroke={stroke} strokeWidth={1.75}>
      <circle cx="5" cy="12" r="1" />
      <circle cx="12" cy="12" r="1" />
      <circle cx="19" cy="12" r="1" />
    </svg>
  );
}

function IconCheck({ size = 11, stroke = '#2c3ea8' }: { size?: number; stroke?: string }) {
  return (
    <svg {...BASE_SVG} width={size} height={size} stroke={stroke} strokeWidth={2.2}>
      <path d="M20 6 9 17l-5-5" />
    </svg>
  );
}

function IconChevron({ size = 11, stroke = '#636e9d' }: { size?: number; stroke?: string }) {
  return (
    <svg {...BASE_SVG} width={size} height={size} stroke={stroke} strokeWidth={2}>
      <path d="m6 9 6 6 6-6" />
    </svg>
  );
}

function IconFunnel({ size = 15, stroke = '#2A2F5F' }: { size?: number; stroke?: string }) {
  return (
    <svg {...BASE_SVG} width={size} height={size} stroke={stroke} strokeWidth={1.75}>
      <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
    </svg>
  );
}

// ── Sort tab definitions ──────────────────────────────────────────────────────

const SORT_TABS: { id: HotelSortKey; label: string; Icon: typeof IconSparkle }[] = [
  { id: 'best',        label: 'Best',        Icon: IconSparkle },
  { id: 'cheapest',    label: 'Cheapest',    Icon: IconDollar  },
  { id: 'top-reviews', label: 'Top reviews', Icon: IconStar5   },
];

const STAR_LABEL: Record<NonNullable<StarFilter>, string> = {
  '3plus': 'Stars: 3★+',
  '4plus': 'Stars: 4★+',
  '5only': 'Stars: 5★ only',
};

// ── Component ─────────────────────────────────────────────────────────────────

export function HotelSortFilterBar({
  sortValues = { best: '—', cheapest: '—', 'top-reviews': '—' },
  defaultSort = 'best',
  defaultStars = null,
  onOpenFiltersPanel,
  onSortChange,
  onStarsChange,
}: HotelSortFilterBarProps) {
  const [sort, setSort] = useState<HotelSortKey>(defaultSort);
  const [starsFilter, setStarsFilter] = useState<StarFilter>(defaultStars);

  const activeFilterCount = starsFilter ? 1 : 0;
  const hasFilters = activeFilterCount > 0;

  return (
    <Group
      px={16}
      py={10}
      gap={6}
      wrap="nowrap"
      style={{
        borderBottom: '1px solid #E4E6F5',
        background: 'white',
        overflowX: 'auto',
        scrollbarWidth: 'none',
      }}
    >
      {/* ── Sort pills ───────────────────────────────────────────────────────── */}
      {SORT_TABS.map(({ id, label, Icon }) => {
        const active = sort === id;
        return (
          <UnstyledButton
            key={id}
            onClick={() => { setSort(id); onSortChange?.(id); }}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '5px 12px 5px 10px',
              background: active ? '#5C6494' : 'white',
              border: `1px solid ${active ? '#5C6494' : '#d4d8ea'}`,
              borderRadius: 9999,
              color: active ? 'white' : '#2A2F5F',
              fontSize: 12,
              fontWeight: active ? 600 : 500,
              whiteSpace: 'nowrap',
              flexShrink: 0,
              transition: 'all 120ms ease',
            }}
          >
            <Icon size={12} stroke={active ? 'white' : '#636e9d'} />
            {label}
            <span style={{ color: active ? 'rgba(255,255,255,0.55)' : '#9aa2c5', fontWeight: 400, fontSize: 11 }}>
              · {sortValues[id]}
            </span>
          </UnstyledButton>
        );
      })}

      {/* ··· overflow — stub, not yet wired */}
      <UnstyledButton
        aria-label="More sort options"
        style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 28, height: 28, background: 'white', border: '1px solid #d4d8ea', borderRadius: '50%', flexShrink: 0 }}
      >
        <IconDots size={14} stroke="#636e9d" />
      </UnstyledButton>

      {/* Separator */}
      <Box style={{ width: 1, height: 16, background: '#E4E6F5', flexShrink: 0 }} />

      {/* ── Stars filter chip ────────────────────────────────────────────────── */}
      {/* v1 single-toggle: only toggles '4plus' on/off; '3plus' and '5only' are defined but unreachable via the UI */}
      <UnstyledButton
        onClick={() => { const next: StarFilter = starsFilter ? null : '4plus'; setStarsFilter(next); onStarsChange?.(next); }}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 4,
          padding: '5px 8px 5px 10px',
          background: starsFilter ? '#5C6494' : 'white',
          border: `1px solid ${starsFilter ? '#5C6494' : '#d4d8ea'}`,
          borderRadius: 9999,
          color: starsFilter ? 'white' : '#2A2F5F',
          fontSize: 12,
          fontWeight: starsFilter ? 600 : 500,
          whiteSpace: 'nowrap',
          flexShrink: 0,
          transition: 'all 120ms ease',
        }}
      >
        {starsFilter && <IconCheck size={11} stroke="white" />}
        {starsFilter ? STAR_LABEL[starsFilter] : 'Stars'}
        <IconChevron size={11} stroke={starsFilter ? 'rgba(255,255,255,0.55)' : '#636e9d'} />
      </UnstyledButton>

      {/* Price chip — stub, not yet wired */}
      <UnstyledButton style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '5px 8px 5px 10px', background: 'white', border: '1px solid #d4d8ea', borderRadius: 9999, color: '#2A2F5F', fontSize: 12, fontWeight: 500, whiteSpace: 'nowrap', flexShrink: 0 }}>
        Price <IconChevron size={11} stroke="#636e9d" />
      </UnstyledButton>

      {/* Distance chip — stub, not yet wired */}
      <UnstyledButton style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '5px 8px 5px 10px', background: 'white', border: '1px solid #d4d8ea', borderRadius: 9999, color: '#2A2F5F', fontSize: 12, fontWeight: 500, whiteSpace: 'nowrap', flexShrink: 0 }}>
        Distance <IconChevron size={11} stroke="#636e9d" />
      </UnstyledButton>

      {/* ── All Filters ───────────────────────────────────────────────────────── */}
      <UnstyledButton
        aria-label="All filters"
        onClick={onOpenFiltersPanel}
        style={{
          marginLeft: 'auto',
          display: 'inline-flex',
          alignItems: 'center',
          gap: 4,
          height: 32,
          padding: hasFilters ? '0 10px' : '0',
          width: hasFilters ? 'auto' : 32,
          justifyContent: 'center',
          background: hasFilters ? '#5C6494' : 'white',
          border: `1px solid ${hasFilters ? '#5C6494' : '#d4d8ea'}`,
          borderRadius: hasFilters ? 9999 : '50%',
          flexShrink: 0,
          transition: 'all 120ms ease',
        }}
      >
        <IconFunnel size={15} stroke={hasFilters ? 'white' : '#2A2F5F'} />
        {hasFilters && (
          <span style={{ background: 'rgba(255,255,255,0.85)', color: '#2A2F5F', borderRadius: 9999, padding: '1px 6px', fontSize: 10, lineHeight: 1.4 }}>
            {activeFilterCount}
          </span>
        )}
      </UnstyledButton>
    </Group>
  );
}

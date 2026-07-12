import { useState } from 'react';
import { Group, UnstyledButton, Box } from '@mantine/core';

// ── Types ─────────────────────────────────────────────────────────────────────

export type ItinerarySortKey = 'balanced' | 'relaxed' | 'adventurous';
export type CategoryFilter = 'sightseeing' | 'food' | 'outdoor' | 'culture' | null;

export interface ItinerarySortFilterBarProps {
  defaultSort?: ItinerarySortKey;
  defaultCategory?: CategoryFilter;
  onOpenFiltersPanel?: () => void;
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

function IconSun({ size = 12, stroke = '#636e9d' }: { size?: number; stroke?: string }) {
  return (
    <svg {...BASE_SVG} width={size} height={size} stroke={stroke} strokeWidth={1.75}>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2" /><path d="M12 20v2" />
      <path d="m4.93 4.93 1.41 1.41" /><path d="m17.66 17.66 1.41 1.41" />
      <path d="M2 12h2" /><path d="M20 12h2" />
      <path d="m6.34 17.66-1.41 1.41" /><path d="m19.07 4.93-1.41 1.41" />
    </svg>
  );
}

function IconBolt({ size = 12, stroke = '#636e9d' }: { size?: number; stroke?: string }) {
  return (
    <svg {...BASE_SVG} width={size} height={size} stroke={stroke} strokeWidth={1.75}>
      <path d="m13 2-3 7h7l-3 7" />
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

// ── Sort tab definitions ───────────────────────────────────────────────────────

const SORT_TABS: { id: ItinerarySortKey; label: string; Icon: typeof IconSparkle }[] = [
  { id: 'balanced',    label: 'Balanced',    Icon: IconSparkle },
  { id: 'relaxed',     label: 'Relaxed',     Icon: IconSun     },
  { id: 'adventurous', label: 'Adventurous', Icon: IconBolt    },
];

const CATEGORY_LABEL: Record<NonNullable<CategoryFilter>, string> = {
  sightseeing: 'Type: Sightseeing',
  food:        'Type: Food & Drink',
  outdoor:     'Type: Outdoor',
  culture:     'Type: Culture',
};

// ── Component ─────────────────────────────────────────────────────────────────

export function ItinerarySortFilterBar({
  defaultSort = 'balanced',
  defaultCategory = null,
  onOpenFiltersPanel,
}: ItinerarySortFilterBarProps) {
  const [sort, setSort] = useState<ItinerarySortKey>(defaultSort);
  const [category, setCategory] = useState<CategoryFilter>(defaultCategory);

  const activeFilterCount = category ? 1 : 0;
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
            onClick={() => setSort(id)}
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
          </UnstyledButton>
        );
      })}

      {/* ··· more sort options */}
      <UnstyledButton
        aria-label="More sort options"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: 28,
          height: 28,
          padding: 0,
          background: 'white',
          border: '1px solid #d4d8ea',
          borderRadius: '50%',
          flexShrink: 0,
        }}
      >
        <IconDots size={14} stroke="#636e9d" />
      </UnstyledButton>

      {/* Separator */}
      <Box style={{ width: 1, height: 16, background: '#E4E6F5', flexShrink: 0 }} />

      {/* ── Filter chips ─────────────────────────────────────────────────────── */}

      {/* Placeholder: opens a category picker once implemented; sets sightseeing when none active, clears when any active */}
      <UnstyledButton
        onClick={() => setCategory(category === null ? 'sightseeing' : null)}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 4,
          padding: '5px 8px 5px 10px',
          background: category ? '#5C6494' : 'white',
          border: `1px solid ${category ? '#5C6494' : '#d4d8ea'}`,
          borderRadius: 9999,
          color: category ? 'white' : '#2A2F5F',
          fontSize: 12,
          fontWeight: category ? 600 : 500,
          whiteSpace: 'nowrap',
          flexShrink: 0,
          transition: 'all 120ms ease',
        }}
      >
        {category && <IconCheck size={11} stroke="white" />}
        {category ? CATEGORY_LABEL[category] : 'Type'}
        <IconChevron size={11} stroke={category ? 'rgba(255,255,255,0.55)' : '#636e9d'} />
      </UnstyledButton>

      <UnstyledButton
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 4,
          padding: '5px 8px 5px 10px',
          background: 'white',
          border: '1px solid #d4d8ea',
          borderRadius: 9999,
          color: '#2A2F5F',
          fontSize: 12,
          fontWeight: 500,
          whiteSpace: 'nowrap',
          flexShrink: 0,
        }}
      >
        Days
        <IconChevron size={11} stroke="#636e9d" />
      </UnstyledButton>

      <UnstyledButton
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 4,
          padding: '5px 8px 5px 10px',
          background: 'white',
          border: '1px solid #d4d8ea',
          borderRadius: 9999,
          color: '#2A2F5F',
          fontSize: 12,
          fontWeight: 500,
          whiteSpace: 'nowrap',
          flexShrink: 0,
        }}
      >
        Budget
        <IconChevron size={11} stroke="#636e9d" />
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
          <span
            style={{
              background: 'rgba(255,255,255,0.85)',
              color: '#2A2F5F',
              borderRadius: 9999,
              padding: '1px 6px',
              fontSize: 10,
              lineHeight: 1.4,
            }}
          >
            {activeFilterCount}
          </span>
        )}
      </UnstyledButton>
    </Group>
  );
}

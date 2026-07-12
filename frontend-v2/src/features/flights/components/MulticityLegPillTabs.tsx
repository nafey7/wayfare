import { Text, UnstyledButton } from '@mantine/core';

const PILL = 999;
const INNER = 10;

function formatLegTabDate(iso: string | undefined): string {
  if (!iso?.trim()) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/** Minimal row for leg pills (chat + search). */
export interface MulticityLegTabRow {
  legIndex?: number;
  origin: string;
  destination: string;
  departureDate: string;
}

export interface MulticityLegPillTabsProps {
  legs: MulticityLegTabRow[];
  value: number;
  onChange: (index: number) => void;
}

/**
 * Pill segmented control for switching multi-city search legs.
 */
export function MulticityLegPillTabs({ legs, value, onChange }: MulticityLegPillTabsProps) {
  const n = legs.length;

  return (
    <div
      role="tablist"
      aria-label="Multi-city legs"
      style={{
        display: 'flex',
        flexDirection: 'row',
        flexWrap: 'nowrap',
        gap: 2,
        marginBottom: 16,
        width: '100%',
        overflowX: 'auto',
        paddingBottom: 2,
        scrollbarWidth: 'thin',
      }}
    >
      {legs.map((leg, i) => {
        const idx = leg.legIndex ?? i;
        const isActive = value === i;
        const datePart = formatLegTabDate(leg.departureDate);
        const routeText = `${leg.origin} to ${leg.destination}`;

        return (
          <UnstyledButton
            key={`${idx}-${leg.origin}-${leg.destination}`}
            role="tab"
            aria-selected={isActive}
            tabIndex={isActive ? 0 : -1}
            onClick={() => onChange(i)}
            style={{
              flex: '1 1 0',
              minWidth: 148,
              padding: '10px 12px',
              cursor: 'pointer',
              fontFamily: 'inherit',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: isActive
                ? 'var(--mantine-color-navy-7)'
                : 'var(--mantine-color-gray-2)',
              color: isActive ? 'white' : 'var(--mantine-color-black)',
              borderTopLeftRadius: i === 0 ? PILL : INNER,
              borderBottomLeftRadius: i === 0 ? PILL : INNER,
              borderTopRightRadius: i === n - 1 ? PILL : INNER,
              borderBottomRightRadius: i === n - 1 ? PILL : INNER,
              transition: 'background-color 150ms, color 150ms',
            }}
          >
            <Text
              component="span"
              size="sm"
              fw={700}
              c="inherit"
              ta="center"
              style={{
                lineHeight: 1.35,
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexWrap: 'wrap',
                columnGap: 10,
                rowGap: 2,
              }}
            >
              <span>{routeText}</span>
              {datePart ? <span>{datePart}</span> : null}
            </Text>
          </UnstyledButton>
        );
      })}
    </div>
  );
}

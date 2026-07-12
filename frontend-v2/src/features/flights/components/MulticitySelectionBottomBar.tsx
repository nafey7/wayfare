import { Alert, Badge, Box, Button, Group, Text } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { Plane } from 'lucide-react';
import type { MulticityLegSelection } from '@/store/slices/flightBookingSlice';
import type { MulticityLegSearchResultCamel } from '@/types/flightBackend';
import { zIndex } from '@/theme';
import { formatCurrency, parseFareFromRevalidateResponse } from '../utils/flightUtils';
import {
  aggregateMulticityFare,
  getSortedMulticityLegSelections,
  isMulticitySelectionFull,
} from '../utils/multicityPricing';

export interface MulticitySelectionBottomBarProps {
  /** Full leg list from search (matching metadata for selected cards). */
  allLegs: MulticityLegSearchResultCamel[];
  selectedLegs: Record<number, MulticityLegSelection>;
  onReviewBook: () => void;
}

function countSelected(
  legs: MulticityLegSearchResultCamel[],
  selected: Record<number, MulticityLegSelection>
): number {
  let n = 0;
  for (let i = 0; i < legs.length; i++) {
    const idx = legs[i]!.legIndex ?? i;
    if (selected[idx]) n++;
  }
  return n;
}

function legMetaForSelection(
  allLegs: MulticityLegSearchResultCamel[],
  sel: MulticityLegSelection
): MulticityLegSearchResultCamel | undefined {
  return allLegs.find((l, i) => (l.legIndex ?? i) === sel.legIndex);
}

const PRIMARY_COLOR = 'var(--mantine-primary-color-filled)';
const PRIMARY_DARK = 'var(--mantine-primary-color-filled-hover)';
const INFO_BORDER = 'rgba(34, 139, 230, 0.35)'; // ≈ MUI alpha(info.main, 0.35)
const SUCCESS_BORDER = 'rgba(43, 138, 62, 0.45)';
const SUCCESS_BG = 'rgba(64, 192, 87, 0.18)';
const SUCCESS_DOT = 'var(--mantine-color-green-7)';
const PRIMARY_CHIP_BG = 'var(--mantine-primary-color-light)';
const INFO_DARK = 'var(--mantine-color-blue-9)';

/**
 * Sticky summary bar for multi-city flight search (only used on `/flights/search`):
 * selection progress, selected-leg summaries, review CTA.
 * Positioned with `sticky` so it stays within the content panel scroll area, not the full viewport.
 */
export function MulticitySelectionBottomBar({
  allLegs,
  selectedLegs,
  onReviewBook,
}: MulticitySelectionBottomBarProps) {
  const isMobile = useMediaQuery('(max-width: 47.99em)');
  const total = allLegs.length;
  const selectedCount = countSelected(allLegs, selectedLegs);
  const allLegsSelected = total >= 2 && isMulticitySelectionFull(selectedLegs, total);
  const successfulSelections = getSortedMulticityLegSelections(selectedLegs);
  const mcFareAgg =
    successfulSelections.length > 0 ? aggregateMulticityFare(selectedLegs) : null;
  const mixedCurrencyBlock = Boolean(mcFareAgg?.hasMixedCurrencies);

  return (
    <Box
      component="aside"
      aria-label="Multi-city flight selection summary"
      style={{
        position: 'sticky',
        bottom: 0,
        zIndex: zIndex.stickyFooter,
        width: '100%',
        maxWidth: '100%',
        boxSizing: 'border-box',
        overflowX: 'hidden',
        flexShrink: 0,
        marginTop: 'auto',
        alignSelf: 'stretch',
        backgroundColor: 'var(--mantine-color-body)',
        borderTop: `1px solid ${INFO_BORDER}`,
        borderBottom: `1px solid ${INFO_BORDER}`,
        boxShadow: 'var(--mantine-shadow-lg)',
        padding: '12px 16px',
        paddingBottom: 'calc(12px + env(safe-area-inset-bottom, 0px))',
      }}
    >
      {mixedCurrencyBlock && (
        <Alert color="yellow" mb="sm" py={6}>
          Legs use different currencies — adjust selection so all fares share one currency before
          review.
        </Alert>
      )}
      <Box
        style={{
          display: 'flex',
          flexDirection: isMobile ? 'column' : 'row',
          alignItems: isMobile ? 'stretch' : 'center',
          flexWrap: 'wrap',
          gap: 'var(--mantine-spacing-sm)',
          width: '100%',
          minWidth: 0,
          overflow: 'hidden',
        }}
      >
        <Group gap="sm" align="center" wrap="nowrap" style={{ flexShrink: 0 }}>
          <div
            aria-live="polite"
            style={{
              width: 40,
              height: 40,
              borderRadius: '50%',
              backgroundColor: PRIMARY_COLOR,
              color: 'white',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 700,
              fontSize: '0.875rem',
              flexShrink: 0,
            }}
          >
            {selectedCount}/{total}
          </div>
          <Box style={{ minWidth: 0 }}>
            <Text size="sm" fw={700}>
              {selectedCount} of {total} legs selected
            </Text>
            <Text size="xs" c="dimmed" display="block">
              {allLegsSelected
                ? 'All legs selected — you can review and book.'
                : 'You can continue with any selection; unselected legs stay unbooked.'}
            </Text>
          </Box>
        </Group>

        {successfulSelections.length > 0 && (
          <Box
            style={{
              flex: isMobile ? undefined : 1,
              width: isMobile ? '100%' : undefined,
              minWidth: 0,
              display: 'flex',
              alignItems: 'stretch',
              gap: 8,
              overflowX: 'auto',
              paddingTop: 4,
              paddingBottom: 4,
              scrollbarWidth: 'thin',
            }}
          >
            {successfulSelections.map((sel) => {
              const meta = legMetaForSelection(allLegs, sel);
              const route = meta
                ? `${meta.origin} → ${meta.destination}`
                : `Leg ${sel.legIndex + 1}`;
              const fare = parseFareFromRevalidateResponse(sel.revalidateResponse);
              const priceLabel =
                fare && fare.amount != null ? formatCurrency(fare.amount, fare.currency) : null;

              return (
                <Box
                  key={sel.legIndex}
                  style={{
                    flex: '0 0 auto',
                    minWidth: isMobile ? 160 : 200,
                    maxWidth: isMobile ? 240 : 280,
                    padding: '8px 12px',
                    borderRadius: 8,
                    border: `1px solid ${SUCCESS_BORDER}`,
                    backgroundColor: SUCCESS_BG,
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 8,
                  }}
                >
                  <div
                    aria-hidden
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      backgroundColor: SUCCESS_DOT,
                      marginTop: 6,
                      flexShrink: 0,
                    }}
                  />
                  <div
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: '50%',
                      backgroundColor: PRIMARY_COLOR,
                      color: 'white',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    <Plane size={18} />
                  </div>
                  <Box style={{ minWidth: 0 }}>
                    <Group gap={4} align="center" wrap="wrap">
                      <Text component="span" size="sm" fw={700}>
                        Flight {sel.legIndex + 1}
                      </Text>
                      <Badge
                        size="xs"
                        style={{
                          backgroundColor: PRIMARY_CHIP_BG,
                          color: PRIMARY_DARK,
                        }}
                      >
                        Selected
                      </Badge>
                    </Group>
                    <Text
                      size="xs"
                      display="block"
                      mt={2}
                      style={{ color: INFO_DARK, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}
                    >
                      {route}
                      {priceLabel ? ` · ${priceLabel}` : ''}
                    </Text>
                  </Box>
                </Box>
              );
            })}
          </Box>
        )}

        <Button
          size="md"
          disabled={selectedCount === 0 || mixedCurrencyBlock}
          onClick={onReviewBook}
          radius={999}
          fw={600}
          px="md"
          fullWidth={isMobile}
          style={isMobile ? undefined : { flexShrink: 0, marginLeft: 'auto' }}
        >
          Review and book
        </Button>
      </Box>
    </Box>
  );
}

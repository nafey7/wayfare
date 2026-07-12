import {
  ActionIcon,
  Box,
  Button,
  Checkbox,
  Group,
  Modal,
  Stack,
} from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { isPastDate } from '@/utils/dateValidation';
import { showErrorToast } from '@/utils/toast';
import {
  format,
  addMonths,
  subMonths,
  startOfMonth,
  endOfMonth,
  eachDayOfInterval,
  startOfWeek,
  endOfWeek,
  isSameMonth,
  isSameDay,
  isWithinInterval,
  isBefore,
  addDays,
  differenceInDays,
} from 'date-fns';

export interface DatesDialogProps {
  open: boolean;
  onClose: () => void;
  /** Initial start date (e.g. from itinerary). */
  initialStartDate?: Date | null;
  /** Initial end date (e.g. from itinerary). */
  initialEndDate?: Date | null;
  /** Called when user confirms with "Update". */
  onUpdate?: (startDate: Date | null, endDate: Date | null, undecided: boolean) => void;
  /**
   * When set, renders content only (no Modal frame). The parent is expected to
   * provide the framing (e.g. a Mantine `Popover.Dropdown`). Otherwise the
   * dialog renders as a centered Mantine `Modal`.
   *
   * Kept as `anchorEl` for backward compatibility with the legacy MUI Popover
   * API; the value is no longer used for positioning.
   */
  anchorEl?: HTMLElement | null;
  /** Heading above the calendars (flights vs hotels). */
  dialogTitle?: string;
  /**
   * When set, uses this value instead of `useMediaQuery('(min-width: 900px)')`.
   * Prefer passing this in tests instead of mocking `@mantine/hooks`.
   */
  mdUp?: boolean;
}

// ── Colours (match FlightNavSearchBar / HotelNavSearchBar) ───────────────────
const NAVY = '#171B63';
const SLATE = '#636e9d';
const LINE = '#E4E6F5';

const DAY_HEADERS = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];

function getCalendarDays(month: Date): Date[] {
  const start = startOfWeek(startOfMonth(month), { weekStartsOn: 0 });
  const end = endOfWeek(endOfMonth(month), { weekStartsOn: 0 });
  return eachDayOfInterval({ start, end });
}

function isInRange(day: Date, start: Date | null, end: Date | null): boolean {
  if (!start || !end) return false;
  const [a, b] = start <= end ? [start, end] : [end, start];
  return isWithinInterval(day, { start: a, end: b });
}

function isStartDay(day: Date, start: Date | null): boolean {
  if (!start) return false;
  return isSameDay(day, start);
}

function isEndDay(day: Date, end: Date | null): boolean {
  if (!end) return false;
  return isSameDay(day, end);
}

/**
 * When (dates) dialog – date range picker with two months on md+, single month on
 * narrow viewports, "I haven't decided" checkbox, Cancel/Apply.
 *
 * Renders as a centered Mantine `Modal` by default; when `anchorEl` is truthy the
 * parent is expected to wrap us in a Mantine `Popover.Dropdown`, so we render the
 * content panel directly without a Modal frame.
 */
export function DatesDialog({
  open,
  onClose,
  anchorEl,
  initialStartDate = null,
  initialEndDate = null,
  onUpdate,
  dialogTitle = 'When are you flying?',
  mdUp: mdUpProp,
}: DatesDialogProps) {
  const breakpointMdUp = useMediaQuery('(min-width: 900px)') ?? false;
  const isMdUp = mdUpProp ?? breakpointMdUp;
  const isPanel = Boolean(anchorEl);

  const defaultStart = useMemo(() => {
    if (initialStartDate) return initialStartDate;
    const t = new Date();
    return new Date(t.getFullYear(), t.getMonth(), 10);
  }, [initialStartDate]);
  const defaultEnd = useMemo(
    () => initialEndDate ?? addDays(defaultStart, 4),
    [initialEndDate, defaultStart]
  );

  const [leftMonth, setLeftMonth] = useState<Date>(() => startOfMonth(defaultStart));
  const [startDate, setStartDate] = useState<Date | null>(defaultStart);
  const [endDate, setEndDate] = useState<Date | null>(defaultEnd);
  const [undecided, setUndecided] = useState(false);

  /**
   * Reset selection on open (matches MUI's `TransitionProps.onEntered` behavior).
   * Note: also re-runs if `defaultStart`/`defaultEnd` change while the dialog is
   * open — would discard in-progress selection. No caller does this today; if a
   * future caller mutates initial dates while the dialog is open, scope this
   * with a `useRef` previous-open tracker.
   */
  useEffect(() => {
    if (open) {
      setStartDate(defaultStart);
      setEndDate(defaultEnd);
      setUndecided(false);
      setLeftMonth(startOfMonth(defaultStart));
    }
  }, [open, defaultStart, defaultEnd]);

  const handleDayClick = useCallback(
    (day: Date) => {
      if (undecided) return;
      if (isPastDate(day)) {
        showErrorToast('Selected date cannot be in the past.');
        return;
      }
      if (!startDate || endDate) {
        setStartDate(day);
        setEndDate(null);
        return;
      }
      if (isBefore(day, startDate)) {
        setStartDate(day);
        setEndDate(startDate);
      } else {
        setEndDate(day);
      }
    },
    [startDate, endDate, undecided]
  );

  const handleUpdate = useCallback(() => {
    onUpdate?.(startDate, endDate, undecided);
    onClose();
  }, [startDate, endDate, undecided, onUpdate, onClose]);

  const displayMonths = isMdUp ? [leftMonth, addMonths(leftMonth, 1)] : [leftMonth];
  const summaryText = undecided
    ? 'Dates not set'
    : startDate && endDate
      ? `${format(startDate, 'MMM d')}-${format(endDate, 'MMM d')} • ${differenceInDays(endDate, startDate) + 1} days`
      : startDate
        ? `${format(startDate, 'MMM d')} – select end`
        : 'Select dates';

  const CELL_SIZE = 30;
  const CELL_GAP = 2;

  const gridStyle: React.CSSProperties = isMdUp
    ? {
        display: 'grid',
        gridTemplateColumns: `repeat(7, ${CELL_SIZE}px)`,
        gap: CELL_GAP,
      }
    : {
        display: 'grid',
        gridTemplateColumns: 'repeat(7, minmax(0, 1fr))',
        gap: CELL_GAP,
        width: '100%',
        maxWidth: 320,
      };
  const dayCellStyle: React.CSSProperties = isMdUp
    ? { width: CELL_SIZE, height: CELL_SIZE }
    : { width: '100%', minHeight: 36, aspectRatio: '1', maxHeight: 44 };

  const content = (
    <Stack gap={0} p={16}>
      <Group justify="space-between" align="center" gap="xs" mb={12} wrap="wrap">
        <span
          style={{
            fontSize: 13,
            fontWeight: 700,
            color: NAVY,
            fontFamily: 'inherit',
          }}
        >
          {dialogTitle}
        </span>
        <span
          style={{
            fontSize: 11,
            color: SLATE,
            fontFamily: 'inherit',
          }}
        >
          {summaryText}
        </span>
      </Group>

      <Stack
        gap={isMdUp ? 'md' : 'sm'}
        align="center"
        mb={12}
        style={{
          width: '100%',
          flexDirection: isMdUp ? 'row' : 'column',
          justifyContent: 'center',
        }}
      >
        {displayMonths.map((month, idx) => (
          <Stack
            key={month.getTime()}
            data-testid="dates-dialog-calendar"
            align="center"
            gap={6}
            style={{ width: '100%', maxWidth: isMdUp ? undefined : 320 }}
          >
            <Group gap={4} justify="center" align="center">
              {isMdUp ? (
                <>
                  {idx === 0 ? (
                    <ActionIcon
                      size="sm"
                      aria-label="Previous month"
                      onClick={() => setLeftMonth((m) => subMonths(m, 1))}
                      variant="subtle"
                      color="dark"
                    >
                      <ChevronLeft size={14} />
                    </ActionIcon>
                  ) : (
                    <Box style={{ width: 28 }} />
                  )}
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      color: NAVY,
                      textTransform: 'uppercase',
                      letterSpacing: '.06em',
                      minWidth: 72,
                      textAlign: 'center',
                      fontFamily: 'inherit',
                    }}
                  >
                    {format(month, 'MMMM yyyy')}
                  </span>
                  {idx === 1 ? (
                    <ActionIcon
                      size="sm"
                      aria-label="Next month"
                      onClick={() => setLeftMonth((m) => addMonths(m, 1))}
                      variant="subtle"
                      color="dark"
                    >
                      <ChevronRight size={14} />
                    </ActionIcon>
                  ) : (
                    <Box style={{ width: 28 }} />
                  )}
                </>
              ) : (
                <>
                  <ActionIcon
                    size="sm"
                    aria-label="Previous month"
                    onClick={() => setLeftMonth((m) => subMonths(m, 1))}
                    variant="subtle"
                    color="dark"
                  >
                    <ChevronLeft size={14} />
                  </ActionIcon>
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      color: NAVY,
                      textTransform: 'uppercase',
                      letterSpacing: '.06em',
                      minWidth: 72,
                      textAlign: 'center',
                      fontFamily: 'inherit',
                    }}
                  >
                    {format(month, 'MMMM yyyy')}
                  </span>
                  <ActionIcon
                    size="sm"
                    aria-label="Next month"
                    onClick={() => setLeftMonth((m) => addMonths(m, 1))}
                    variant="subtle"
                    color="dark"
                  >
                    <ChevronRight size={14} />
                  </ActionIcon>
                </>
              )}
            </Group>
            <Box style={{ ...gridStyle, marginBottom: 2 }}>
              {DAY_HEADERS.map((d, i) => (
                <Box key={`day-header-${i}`} style={{ display: 'flex', justifyContent: 'center' }}>
                  <span
                    style={{
                      fontSize: 10,
                      fontWeight: 700,
                      color: SLATE,
                      textTransform: 'uppercase',
                      fontFamily: 'inherit',
                    }}
                  >
                    {d}
                  </span>
                </Box>
              ))}
            </Box>
            <Box style={gridStyle}>
              {getCalendarDays(month).map((day) => {
                const inRange = isInRange(day, startDate, endDate);
                const isStart = isStartDay(day, startDate);
                const isEnd = isEndDay(day, endDate);
                const isCurrentMonth = isSameMonth(day, month);
                const isSelected = isStart || isEnd;
                const isPast = isPastDate(day);

                const bg = isSelected ? NAVY : inRange ? LINE : 'transparent';
                const color = isSelected
                  ? 'white'
                  : isCurrentMonth
                    ? NAVY
                    : SLATE;

                return (
                  <Box
                    key={day.getTime()}
                    onClick={() => isCurrentMonth && handleDayClick(day)}
                    style={{
                      ...dayCellStyle,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      borderRadius: '50%',
                      backgroundColor: bg,
                      color,
                      cursor: isPast ? 'not-allowed' : isCurrentMonth && !undecided ? 'pointer' : 'default',
                      opacity: isCurrentMonth ? (isPast ? 0.35 : 1) : 0.4,
                    }}
                  >
                    <span
                      style={{
                        fontSize: 12,
                        fontWeight: isSelected ? 700 : 400,
                        color: 'inherit',
                        fontFamily: 'inherit',
                      }}
                    >
                      {format(day, 'd')}
                    </span>
                  </Box>
                );
              })}
            </Box>
          </Stack>
        ))}
      </Stack>

      <Checkbox
        checked={undecided}
        onChange={(e) => setUndecided(e.currentTarget.checked)}
        label="I haven't decided the dates yet"
        mb={12}
        size="xs"
        styles={{ label: { fontSize: 12, color: SLATE, fontFamily: 'inherit' } }}
      />

      <Group justify="flex-end" gap="xs">
        <Button
          variant="subtle"
          size="xs"
          onClick={onClose}
          tt="none"
          fw={500}
          color="dark.8"
        >
          Cancel
        </Button>
        <Button
          size="xs"
          radius="xl"
          style={{ backgroundColor: NAVY, color: 'white' }}
          onClick={handleUpdate}
          tt="none"
          fw={600}
          px="lg"
        >
          Apply
        </Button>
      </Group>
    </Stack>
  );

  if (isPanel) {
    return open ? content : null;
  }

  return (
    <Modal
      opened={open}
      onClose={onClose}
      withCloseButton={false}
      centered
      radius="md"
      size={isMdUp ? 'lg' : 'md'}
      padding={0}
      shadow="md"
    >
      {content}
    </Modal>
  );
}

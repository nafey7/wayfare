import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { format, parseISO } from 'date-fns';
import { Button, Group, Popover, Stack, TextInput } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { MapPin } from 'lucide-react';
import { DatesDialog } from '@/features/itinerary/components';
import { RoomConfigurator } from './RoomConfigurator';
import { HotelMultistaySegmentForm } from './HotelMultistaySegmentForm';
import { useAppDispatch, useAppSelector } from '@/store';
import {
  selectHotelSearchFormParams,
  selectHotelTripType,
  selectMultistaySegments,
  setSearchFormParams,
  setTripType,
  setMultistaySegments,
  updateMultistaySegment,
  triggerSearchFromChips,
} from '@/store/slices/hotelBookingSlice';
import type {
  HotelSearchFormParams,
  HotelTripType,
  HotelMultistaySegment,
  RoomOccupancy,
} from '@/types/hotels';
import { buildHotelSearchRequestFromFormParams } from '../utils/buildHotelSearchRequest';
import { getContentDomain, getContentRoutePrefix } from '@/features/routing';

import {
  NAV_NAVY as NAVY,
  NAV_LINE as LINE,
  NAV_MIST_CARD as MIST,
  NAV_SLATE as SLATE,
  NAV_INACTIVE as PLACEHOLDER_COLOR,
} from '@/theme/navTokens';

const TRIP_TYPE_LABELS: Record<HotelTripType, string> = {
  single: 'Single stay',
  'multi-stay': 'Multi-stay',
};

type FieldId = 'destination' | 'triptype' | 'dates' | 'guests';

const LABEL_STYLE: React.CSSProperties = {
  fontSize: 10,
  fontWeight: 700,
  color: SLATE,
  textTransform: 'uppercase',
  letterSpacing: '.06em',
  marginBottom: 2,
  fontFamily: 'inherit',
};

const DIVIDER: React.ReactElement = (
  <div
    style={{
      width: 1,
      alignSelf: 'stretch',
      background: LINE,
      margin: '6px 0',
      flexShrink: 0,
    }}
  />
);

const POPOVER_PROPS = {
  position: 'bottom' as const,
  shadow: 'md' as const,
  radius: 'md' as const,
  withinPortal: true,
  zIndex: 1200,
  closeOnClickOutside: true,
};

function formatHotelStayDates(checkin?: string | null, checkout?: string | null): string {
  const hasIn = !!checkin?.trim();
  const hasOut = !!checkout?.trim();
  if (!hasIn && !hasOut) return 'Add dates';
  try {
    const fmt = (d: Date) => d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    if (hasIn && !hasOut) {
      const d1 = parseISO(checkin!.trim());
      return Number.isNaN(d1.getTime()) ? 'Add dates' : fmt(d1);
    }
    if (!hasIn && hasOut) {
      const d2 = parseISO(checkout!.trim());
      return Number.isNaN(d2.getTime()) ? 'Add dates' : fmt(d2);
    }
    const d1 = parseISO(checkin!.trim());
    const d2 = parseISO(checkout!.trim());
    if (Number.isNaN(d1.getTime()) || Number.isNaN(d2.getTime())) return 'Add dates';
    return d1.getMonth() === d2.getMonth()
      ? `${fmt(d1)} – ${d2.getDate()}`
      : `${fmt(d1)} – ${fmt(d2)}`;
  } catch {
    return 'Add dates';
  }
}

export function HotelNavSearchBar() {
  const isMobile = useMediaQuery('(max-width: 768px)');
  const location = useLocation();
  const navigate = useNavigate();
  const domain = getContentDomain(location.pathname);
  const routePrefix = getContentRoutePrefix(location.pathname);
  const strippedPath = location.pathname.startsWith('/public/chat')
    ? location.pathname.slice('/public/chat'.length)
    : location.pathname;

  const dispatch = useAppDispatch();
  const searchFormParams = useAppSelector(selectHotelSearchFormParams);
  const tripType = useAppSelector(selectHotelTripType);
  const multistaySegments = useAppSelector(selectMultistaySegments);

  const isInBookingFlow =
    domain === 'hotels' && !strippedPath.startsWith('/hotels/search');

  const triggerSearch = () => {
    dispatch(triggerSearchFromChips());
    if (isInBookingFlow) navigate(`${routePrefix}/hotels/search`);
  };

  const checkinDate = useMemo(() => {
    const s = searchFormParams.checkin?.trim();
    if (!s) return null;
    const d = parseISO(s);
    return Number.isNaN(d.getTime()) ? null : d;
  }, [searchFormParams.checkin]);

  const checkoutDate = useMemo(() => {
    const s = searchFormParams.checkout?.trim();
    if (!s) return null;
    const d = parseISO(s);
    return Number.isNaN(d.getTime()) ? null : d;
  }, [searchFormParams.checkout]);

  const rooms = useMemo(
    () => searchFormParams.rooms ?? [{ roomNo: 1, adult: 1, child: 0, childAge: [0] }],
    [searchFormParams.rooms],
  );

  const [datesOpen, setDatesOpen] = useState(false);
  const [roomsOpen, setRoomsOpen] = useState(false);
  // Local room state while the popover is open — committed on close to avoid
  // firing a search on every counter increment (mirrors TravellersSelector pattern)
  const [localRooms, setLocalRooms] = useState<RoomOccupancy[]>(rooms);
  const [tripTypeOpen, setTripTypeOpen] = useState(false);
  const [destinationOpen, setDestinationOpen] = useState(false);
  const [multistayFormOpen, setMultistayFormOpen] = useState(false);
  const [hoveredField, setHoveredField] = useState<FieldId | null>(null);

  const canRunSearch = useMemo(
    () => buildHotelSearchRequestFromFormParams(searchFormParams) != null,
    [searchFormParams],
  );

  // Display summary based on local (in-flight) rooms when popover is open.
  // When Redux `rooms` is null and the popover is closed, show the placeholder
  // instead of the seeded `[1×1-adult]` default.
  const isGuestsUnset = !roomsOpen && searchFormParams.rooms == null;
  const displayRooms = roomsOpen ? localRooms : rooms;
  const totalAdults = displayRooms.reduce((sum, r) => sum + (r.adult ?? 0), 0);
  const totalChildren = displayRooms.reduce((sum, r) => sum + (r.child ?? 0), 0);
  const guestsSummary = isGuestsUnset
    ? 'Guests'
    : displayRooms.length === 1 && totalChildren === 0
      ? `${totalAdults} Adult${totalAdults !== 1 ? 's' : ''}`
      : `${displayRooms.length} room${displayRooms.length !== 1 ? 's' : ''}, ${totalAdults} adult${totalAdults !== 1 ? 's' : ''}, ${totalChildren} child${totalChildren !== 1 ? 'ren' : ''}`;

  const multistaySummary = multistaySegments.some((s) => s.destination.trim())
    ? multistaySegments
        .filter((s) => s.destination.trim())
        .map((s) => s.destination.trim())
        .join(' → ')
    : 'Add destinations';

  const destinationLabel =
    tripType === 'multi-stay'
      ? multistaySummary
      : searchFormParams.destination?.trim() || 'Add destination';
  const destinationIsEmpty =
    tripType === 'multi-stay'
      ? !multistaySegments.some((s) => s.destination.trim())
      : !searchFormParams.destination?.trim();

  const multistayDateRange = useMemo(() => {
    if (tripType !== 'multi-stay') return null;
    const withDates = multistaySegments.filter((s) => s.checkin?.trim() || s.checkout?.trim());
    if (withDates.length === 0) return null;
    const checkin = withDates[0]?.checkin ?? null;
    const checkout = withDates[withDates.length - 1]?.checkout ?? null;
    return { checkin, checkout };
  }, [tripType, multistaySegments]);

  const datesLabel =
    tripType === 'multi-stay'
      ? formatHotelStayDates(multistayDateRange?.checkin, multistayDateRange?.checkout)
      : formatHotelStayDates(searchFormParams.checkin, searchFormParams.checkout);
  const datesIsEmpty =
    tripType === 'multi-stay'
      ? !multistayDateRange?.checkin && !multistayDateRange?.checkout
      : !searchFormParams.checkin && !searchFormParams.checkout;

  const setFormAndSearch = (patch: Partial<HotelSearchFormParams>) => {
    const next = { ...searchFormParams, ...patch };
    dispatch(setSearchFormParams(next));
    if (buildHotelSearchRequestFromFormParams(next)) triggerSearch();
  };

  // Keep local rooms in sync when Redux state changes from outside the popover
  useEffect(() => {
    if (!roomsOpen) setLocalRooms(rooms);
  }, [rooms, roomsOpen]);

  const handleRoomsChange = (nextRooms: RoomOccupancy[]) => {
    // Only update local state while the popover is open; commit + search on close
    setLocalRooms(nextRooms);
  };

  const handleRoomsClose = () => {
    setRoomsOpen(false);
    const next = { ...searchFormParams, rooms: localRooms };
    dispatch(setSearchFormParams(next));
    if (buildHotelSearchRequestFromFormParams(next)) triggerSearch();
  };

  const handleDestinationConfirm = () => {
    setDestinationOpen(false);
    if (canRunSearch) triggerSearch();
  };

  const handleAddMultistaySegment = useCallback(() => {
    const lastSeg = multistaySegments[multistaySegments.length - 1];
    const base = lastSeg?.checkout ? new Date(lastSeg.checkout) : new Date();
    base.setDate(base.getDate() + 1);
    const checkout = new Date(base);
    checkout.setDate(checkout.getDate() + 2);
    const newSeg: HotelMultistaySegment = {
      destination: '',
      checkin: base.toISOString().slice(0, 10),
      checkout: checkout.toISOString().slice(0, 10),
      rooms: [{ roomNo: 1, adult: 2, child: 0, childAge: [0] }],
    };
    dispatch(setMultistaySegments([...multistaySegments, newSeg]));
  }, [multistaySegments, dispatch]);

  const handleRemoveMultistaySegment = useCallback(
    (index: number) => {
      dispatch(setMultistaySegments(multistaySegments.filter((_, i) => i !== index)));
    },
    [multistaySegments, dispatch],
  );

  const handleMultistaySegmentChange = useCallback(
    (index: number, field: keyof HotelMultistaySegment, value: string) => {
      dispatch(updateMultistaySegment({ index, segment: { [field]: value } }));
    },
    [dispatch],
  );

  const handleMultistayApply = () => {
    setMultistayFormOpen(false);
    triggerSearch();
  };

  // ── Field button style ────────────────────────────────────────────────────
  const fieldStyle = (id: FieldId, isOpen: boolean): React.CSSProperties => {
    const hovered = hoveredField === id;
    return {
      flex: 1,
      minWidth: 0,
      display: 'flex',
      flexDirection: 'column',
      padding: isMobile ? '6px 8px' : '8px 18px',
      background: 'white',
      boxShadow: isOpen
        ? 'inset 0 0 0 2px #171B63'
        : hovered
          ? 'inset 0 0 0 1.5px #c8cce0'
          : 'none',
      borderRadius: isOpen || hovered ? 9999 : 0,
      border: 'none',
      cursor: 'pointer',
      textAlign: 'left',
      transition: 'box-shadow 120ms',
      fontFamily: 'inherit',
    };
  };

  const valueStyle = (isEmpty: boolean): React.CSSProperties => ({
    fontSize: isMobile ? 11 : 13,
    fontWeight: isEmpty ? 400 : 600,
    color: isEmpty ? PLACEHOLDER_COLOR : NAVY,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    fontFamily: 'inherit',
  });

  return (
    <div style={{ width: '100%' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'stretch',
            border: `1px solid ${LINE}`,
            borderRadius: 9999,
            background: 'white',
            boxShadow: '0 1px 6px rgba(23,27,99,.06)',
            overflow: 'hidden',
            padding: isMobile ? 4 : 6,
            minWidth: isMobile ? 0 : 'max-content',
            width: isMobile ? '100%' : undefined,
          }}
        >
          {/* ── Destination ───────────────────────────────────────────────────── */}
          {tripType === 'multi-stay' ? (
            <Popover
              opened={multistayFormOpen}
              onClose={() => setMultistayFormOpen(false)}
              {...POPOVER_PROPS}
            >
              <Popover.Target>
                <button
                  type="button"
                  style={fieldStyle('destination', multistayFormOpen)}
                  onMouseEnter={() => setHoveredField('destination')}
                  onMouseLeave={() => setHoveredField(null)}
                  onClick={() => {
                    if (isInBookingFlow) {
                      navigate(`${routePrefix}/hotels/search`);
                      return;
                    }
                    setMultistayFormOpen((p) => !p);
                  }}
                >
                  <span style={{ ...LABEL_STYLE, display: isMobile ? 'none' : undefined }}>Where</span>
                  <span style={valueStyle(destinationIsEmpty)}>{destinationLabel}</span>
                </button>
              </Popover.Target>
              <Popover.Dropdown style={{ padding: 16, width: isMobile ? 'calc(100vw - 24px)' : 520, maxWidth: 'calc(100vw - 24px)' }}>
                <Stack gap="md">
                  <HotelMultistaySegmentForm
                    segments={multistaySegments}
                    onChange={handleMultistaySegmentChange}
                    onAddSegment={handleAddMultistaySegment}
                    onRemoveSegment={handleRemoveMultistaySegment}
                  />
                  <Group justify="flex-end" gap="xs">
                    <Button variant="subtle" color="gray" onClick={() => setMultistayFormOpen(false)}>
                      Cancel
                    </Button>
                    <Button
                      style={{ backgroundColor: NAVY, color: 'white' }}
                      onClick={handleMultistayApply}
                    >
                      Search
                    </Button>
                  </Group>
                </Stack>
              </Popover.Dropdown>
            </Popover>
          ) : (
            <Popover
              opened={destinationOpen}
              onClose={() => setDestinationOpen(false)}
              {...POPOVER_PROPS}
            >
              <Popover.Target>
                <button
                  type="button"
                  style={fieldStyle('destination', destinationOpen)}
                  onMouseEnter={() => setHoveredField('destination')}
                  onMouseLeave={() => setHoveredField(null)}
                  onClick={() => setDestinationOpen((p) => !p)}
                >
                  <span style={{ ...LABEL_STYLE, display: isMobile ? 'none' : undefined }}>Where</span>
                  <span style={valueStyle(destinationIsEmpty)}>{destinationLabel}</span>
                </button>
              </Popover.Target>
              <Popover.Dropdown style={{ padding: 16, minWidth: 280 }}>
                <Stack gap="sm">
                  <TextInput
                    placeholder="City or destination"
                    value={searchFormParams.destination ?? ''}
                    onChange={(e) =>
                      dispatch(
                        setSearchFormParams({
                          ...searchFormParams,
                          destination: e.currentTarget.value,
                        }),
                      )
                    }
                    size="sm"
                    data-autofocus
                    leftSection={<MapPin size={16} color="var(--mantine-color-navy-7)" />}
                    label="Destination"
                  />
                  <Button
                    size="xs"
                    radius="xl"
                    style={{ backgroundColor: NAVY, color: 'white', alignSelf: 'flex-end' }}
                    onClick={handleDestinationConfirm}
                  >
                    {canRunSearch ? 'Search' : 'Close'}
                  </Button>
                </Stack>
              </Popover.Dropdown>
            </Popover>
          )}

          {DIVIDER}

          {/* ── Stay type ─────────────────────────────────────────────────────── */}
          <Popover
            opened={tripTypeOpen}
            onClose={() => setTripTypeOpen(false)}
            {...POPOVER_PROPS}
          >
            <Popover.Target>
              <button
                type="button"
                style={fieldStyle('triptype', tripTypeOpen)}
                onMouseEnter={() => setHoveredField('triptype')}
                onMouseLeave={() => setHoveredField(null)}
                onClick={() => setTripTypeOpen((p) => !p)}
              >
                <span style={{ ...LABEL_STYLE, display: isMobile ? 'none' : undefined }}>Stay type</span>
                <span style={valueStyle(!tripType)}>{tripType ? TRIP_TYPE_LABELS[tripType] : 'Stay type'}</span>
              </button>
            </Popover.Target>
            <Popover.Dropdown style={{ padding: 8, minWidth: 160 }}>
              {(['single', 'multi-stay'] as HotelTripType[]).map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => {
                    dispatch(setTripType(t));
                    setTripTypeOpen(false);
                    triggerSearch();
                  }}
                  style={{
                    display: 'block',
                    width: '100%',
                    textAlign: 'left',
                    padding: '8px 12px',
                    borderRadius: 8,
                    border: 'none',
                    background: tripType === t ? MIST : 'white',
                    color: NAVY,
                    fontSize: 13,
                    fontWeight: tripType === t ? 600 : 400,
                    cursor: 'pointer',
                    fontFamily: 'inherit',
                  }}
                >
                  {TRIP_TYPE_LABELS[t]}
                </button>
              ))}
            </Popover.Dropdown>
          </Popover>

          {DIVIDER}

          {/* ── Dates ─────────────────────────────────────────────────────────── */}
          <Popover
            opened={tripType !== 'multi-stay' && datesOpen}
            onClose={() => setDatesOpen(false)}
            {...POPOVER_PROPS}
          >
            <Popover.Target>
              <button
                type="button"
                style={fieldStyle('dates', tripType === 'multi-stay' ? multistayFormOpen : datesOpen)}
                onMouseEnter={() => setHoveredField('dates')}
                onMouseLeave={() => setHoveredField(null)}
                onClick={() => {
                  if (tripType === 'multi-stay') {
                    if (isInBookingFlow) {
                      navigate(`${routePrefix}/hotels/search`);
                      return;
                    }
                    setMultistayFormOpen((p) => !p);
                  } else {
                    setDatesOpen((o) => !o);
                  }
                }}
              >
                <span style={{ ...LABEL_STYLE, display: isMobile ? 'none' : undefined }}>Dates</span>
                <span style={valueStyle(datesIsEmpty)}>{datesLabel}</span>
              </button>
            </Popover.Target>
            <Popover.Dropdown p={0}>
              <DatesDialog
                open={datesOpen}
                anchorEl={datesOpen ? document.body : null}
                onClose={() => setDatesOpen(false)}
                initialStartDate={checkinDate}
                initialEndDate={checkoutDate}
                dialogTitle="When are you staying?"
                onUpdate={(startDate, endDate, undecided) => {
                  if (undecided) {
                    setFormAndSearch({ checkin: null, checkout: null });
                  } else {
                    setFormAndSearch({
                      checkin: startDate ? format(startDate, 'yyyy-MM-dd') : null,
                      checkout: endDate ? format(endDate, 'yyyy-MM-dd') : null,
                    });
                  }
                }}
              />
            </Popover.Dropdown>
          </Popover>

          {DIVIDER}

          {/* ── Guests ────────────────────────────────────────────────────────── */}
          <Popover
            opened={roomsOpen}
            onClose={handleRoomsClose}
            width={320}
            {...POPOVER_PROPS}
          >
            <Popover.Target>
              <button
                type="button"
                style={fieldStyle('guests', roomsOpen)}
                onMouseEnter={() => setHoveredField('guests')}
                onMouseLeave={() => setHoveredField(null)}
                onClick={() => {
                  if (!roomsOpen) setLocalRooms(rooms); // seed local state on open
                  setRoomsOpen((o) => !o);
                }}
              >
                <span style={{ ...LABEL_STYLE, display: isMobile ? 'none' : undefined }}>Guests</span>
                <span style={valueStyle(isGuestsUnset)}>{guestsSummary}</span>
              </button>
            </Popover.Target>
            <Popover.Dropdown p="md">
              <RoomConfigurator rooms={localRooms} onChange={handleRoomsChange} showRoomCount />
            </Popover.Dropdown>
          </Popover>
        </div>
    </div>
  );
}

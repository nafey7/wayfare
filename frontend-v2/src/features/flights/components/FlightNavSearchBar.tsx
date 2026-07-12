import { useState, useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Popover, Stack, Button } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { ArrowLeftRight, PlaneTakeoff, PlaneLanding } from 'lucide-react';
import { TravellersSelector, TravellersData } from './TravellersSelector';
import { AirportAutocomplete } from './AirportAutocomplete';
import { CabinClassDialog } from './dialogs/CabinClassDialog';
import { TripTypeDialog } from './dialogs/TripTypeDialog';
import { MulticityRouteEditor } from './MulticityRouteEditor';
import { DatesDialog } from '@/features/itinerary/components';
import {
  formatFlightDates,
  formatMulticityChipDatesFromIso,
  formatPassengerCountsDisplay,
  getTripTypeLabel,
} from '../utils/flightUtils';
import {
  routeEndpointDisplayLabel,
  multicityChainEndpointLabel,
} from '../utils/flightSearchBarLabels';
import { buildMulticityTripChain } from '../utils/multicityPricing';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import {
  selectSearchFormParams,
  setTripType,
  setDate,
  setReturnDate,
  setTravellers,
  setFrom,
  setTo,
  swapAirports,
  triggerSearchFromChips,
  type SerializableAirportOption,
} from '@/store/slices/flightBookingSlice';
import { getContentDomain, getContentRoutePrefix } from '@/features/routing';

import {
  NAV_NAVY as NAVY,
  NAV_LINE as LINE,
  NAV_SLATE as SLATE,
  NAV_INACTIVE as PLACEHOLDER_COLOR,
} from '@/theme/navTokens';

const POPOVER_FRAME_PROPS = {
  position: 'bottom' as const,
  shadow: 'md' as const,
  radius: 'md' as const,
  withinPortal: true,
  zIndex: 1200,
  closeOnClickOutside: true,
};

type FieldId = 'route' | 'dates' | 'travellers' | 'triptype' | 'cabin';

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

export function FlightNavSearchBar() {
  const isMobile = useMediaQuery('(max-width: 768px)');
  const location = useLocation();
  const navigate = useNavigate();
  const domain = getContentDomain(location.pathname);
  const routePrefix = getContentRoutePrefix(location.pathname);
  const strippedPath = location.pathname.startsWith('/public/chat')
    ? location.pathname.slice('/public/chat'.length)
    : location.pathname;

  const dispatch = useAppDispatch();
  const searchFormParams = useAppSelector(selectSearchFormParams);

  const isInBookingFlow =
    domain === 'flights' && !strippedPath.startsWith('/flights/search');

  const dispatchSearchTrigger = () => {
    dispatch(triggerSearchFromChips());
    if (isInBookingFlow) navigate(`${routePrefix}/flights/search`);
  };

  const tripType = searchFormParams.tripType;
  const travellers = searchFormParams.travellers;

  const originDisplay = routeEndpointDisplayLabel(
    searchFormParams.fromAirport,
    searchFormParams.from,
    'Origin',
  );
  const destDisplay = routeEndpointDisplayLabel(
    searchFormParams.toAirport,
    searchFormParams.to,
    'Destination',
  );

  const routeLabel = useMemo(() => {
    if (tripType === 'multi-city') {
      const segs = searchFormParams.segments ?? [];
      if (!segs.length) return 'Multi-city route';
      const legs = segs.map((s, i) => ({
        legIndex: i,
        origin: multicityChainEndpointLabel(s.fromAirport, s.from ?? ''),
        destination: multicityChainEndpointLabel(s.toAirport, s.to ?? ''),
      }));
      return buildMulticityTripChain(legs) || 'Multi-city route';
    }
    return `${originDisplay} → ${destDisplay}`;
  }, [tripType, searchFormParams.segments, originDisplay, destDisplay]);

  const date = useMemo(
    () => (searchFormParams.date ? new Date(searchFormParams.date) : null),
    [searchFormParams.date],
  );
  const returnDate = useMemo(
    () => (searchFormParams.returnDate ? new Date(searchFormParams.returnDate) : null),
    [searchFormParams.returnDate],
  );

  const [routeOpen, setRouteOpen] = useState(false);
  const [datesOpen, setDatesOpen] = useState(false);
  const [travellersOpen, setTravellersOpen] = useState(false);
  const [cabinClassOpen, setCabinClassOpen] = useState(false);
  const [tripTypeOpen, setTripTypeOpen] = useState(false);
  const [hoveredField, setHoveredField] = useState<FieldId | null>(null);

  const datesLabel =
    tripType === 'multi-city'
      ? formatMulticityChipDatesFromIso(searchFormParams.segments?.map((s) => s.date))
      : formatFlightDates(date, returnDate, tripType);

  const handleDatesClick = () => {
    if (tripType === 'multi-city') {
      if (isInBookingFlow) navigate(`${routePrefix}/flights/search`);
      else setRouteOpen(true);
      return;
    }
    setDatesOpen((prev) => !prev);
  };

  const routeIsEmpty =
    tripType === 'multi-city'
      ? !searchFormParams.segments?.some(
          (s) => s.from || s.fromAirport || s.to || s.toAirport,
        )
      : !searchFormParams.from &&
        !searchFormParams.fromAirport &&
        !searchFormParams.to &&
        !searchFormParams.toAirport;
  const datesIsEmpty =
    tripType === 'multi-city'
      ? !searchFormParams.segments?.some((s) => s.date)
      : !searchFormParams.date;

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
        {/* ── Route ─────────────────────────────────────────────────────────── */}
        {tripType === 'multi-city' ? (
          <Popover
            opened={routeOpen}
            onClose={() => setRouteOpen(false)}
            {...POPOVER_FRAME_PROPS}
          >
            <Popover.Target>
              <button
                type="button"
                style={fieldStyle('route', routeOpen)}
                onMouseEnter={() => setHoveredField('route')}
                onMouseLeave={() => setHoveredField(null)}
                onClick={() => {
                  if (isInBookingFlow) {
                    navigate(`${routePrefix}/flights/search`);
                    return;
                  }
                  setRouteOpen((p) => !p);
                }}
              >
                <span style={{ ...LABEL_STYLE, display: isMobile ? 'none' : undefined }}>Route</span>
                <span style={valueStyle(routeIsEmpty)}>{routeLabel}</span>
              </button>
            </Popover.Target>
            <Popover.Dropdown
              style={{
                padding: 16,
                width: isMobile ? 'calc(100vw - 24px)' : 640,
                maxWidth: 'calc(100vw - 24px)',
              }}
            >
              <MulticityRouteEditor
                doneLabel="Search"
                onDone={() => {
                  setRouteOpen(false);
                  dispatchSearchTrigger();
                }}
              />
            </Popover.Dropdown>
          </Popover>
        ) : (
          <Popover
            opened={routeOpen}
            onClose={() => setRouteOpen(false)}
            {...POPOVER_FRAME_PROPS}
          >
            <Popover.Target>
              <button
                type="button"
                style={fieldStyle('route', routeOpen)}
                onMouseEnter={() => setHoveredField('route')}
                onMouseLeave={() => setHoveredField(null)}
                onClick={() => setRouteOpen((p) => !p)}
              >
                <span style={{ ...LABEL_STYLE, display: isMobile ? 'none' : undefined }}>Route</span>
                <span style={valueStyle(routeIsEmpty)}>{routeLabel}</span>
              </button>
            </Popover.Target>
            <Popover.Dropdown style={{ padding: 16, minWidth: 300 }}>
              <Stack gap="sm">
                <AirportAutocomplete
                  value={searchFormParams.from}
                  onChange={(value, airport) =>
                    dispatch(setFrom({ value, airport: airport as SerializableAirportOption | undefined }))
                  }
                  placeholder="Origin city or airport"
                  label="From"
                  size="small"
                  startAdornment={<PlaneTakeoff size={16} color={SLATE} />}
                />
                <div style={{ display: 'flex', justifyContent: 'center' }}>
                  <button
                    type="button"
                    onClick={() => dispatch(swapAirports())}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 4,
                      background: 'none',
                      border: `1px solid ${LINE}`,
                      borderRadius: 9999,
                      cursor: 'pointer',
                      padding: '4px 12px',
                      fontSize: 12,
                      color: SLATE,
                      fontFamily: 'inherit',
                    }}
                  >
                    <ArrowLeftRight size={13} />
                    Swap
                  </button>
                </div>
                <AirportAutocomplete
                  value={searchFormParams.to}
                  onChange={(value, airport) =>
                    dispatch(setTo({ value, airport: airport as SerializableAirportOption | undefined }))
                  }
                  placeholder="Destination city or airport"
                  label="To"
                  size="small"
                  startAdornment={<PlaneLanding size={16} color={SLATE} />}
                />
                <Button
                  size="xs"
                  radius="xl"
                  style={{ backgroundColor: NAVY, color: 'white', alignSelf: 'flex-end' }}
                  onClick={() => {
                    dispatchSearchTrigger();
                    setRouteOpen(false);
                  }}
                >
                  Search
                </Button>
              </Stack>
            </Popover.Dropdown>
          </Popover>
        )}

        {DIVIDER}

        {/* ── Dates ─────────────────────────────────────────────────────────── */}
        <Popover opened={datesOpen} onClose={() => setDatesOpen(false)} {...POPOVER_FRAME_PROPS}>
          <Popover.Target>
            <button
              type="button"
              style={fieldStyle('dates', datesOpen)}
              onMouseEnter={() => setHoveredField('dates')}
              onMouseLeave={() => setHoveredField(null)}
              onClick={handleDatesClick}
            >
              <span style={{ ...LABEL_STYLE, display: isMobile ? 'none' : undefined }}>Dates</span>
              <span style={valueStyle(datesIsEmpty)}>{datesLabel}</span>
            </button>
          </Popover.Target>
          <Popover.Dropdown p={0}>
            <DatesDialog
              open={datesOpen}
              anchorEl={datesOpen ? document.body : null}
              initialStartDate={date}
              initialEndDate={returnDate}
              onClose={() => setDatesOpen(false)}
              onUpdate={(newDate, newReturnDate, undecided) => {
                if (undecided) {
                  dispatch(setDate(null));
                  dispatch(setReturnDate(null));
                } else {
                  dispatch(setDate(newDate ? newDate.toISOString() : null));
                  dispatch(setReturnDate(newReturnDate ? newReturnDate.toISOString() : null));
                }
                dispatchSearchTrigger();
                setDatesOpen(false);
              }}
            />
          </Popover.Dropdown>
        </Popover>

        {DIVIDER}

        {/* ── Travellers ────────────────────────────────────────────────────── */}
        <Popover
          opened={travellersOpen}
          onClose={() => setTravellersOpen(false)}
          {...POPOVER_FRAME_PROPS}
        >
          <Popover.Target>
            <button
              type="button"
              style={fieldStyle('travellers', travellersOpen)}
              onMouseEnter={() => setHoveredField('travellers')}
              onMouseLeave={() => setHoveredField(null)}
              onClick={() => setTravellersOpen((p) => !p)}
            >
              <span style={{ ...LABEL_STYLE, display: isMobile ? 'none' : undefined }}>Travellers</span>
              <span style={valueStyle(travellers.adults == null)}>
                {travellers.adults == null
                  ? 'Travellers'
                  : formatPassengerCountsDisplay(
                      travellers.adults,
                      travellers.children ?? 0,
                      travellers.infants ?? 0,
                    )}
              </span>
            </button>
          </Popover.Target>
          <Popover.Dropdown style={{ padding: 16 }}>
            <TravellersSelector
              value={travellers}
              onChange={(data: TravellersData) => {
                dispatch(setTravellers(data));
                dispatchSearchTrigger();
              }}
              onClose={() => setTravellersOpen(false)}
            />
          </Popover.Dropdown>
        </Popover>

        {DIVIDER}

        {/* ── Trip type ─────────────────────────────────────────────────────── */}
        <Popover
          opened={tripTypeOpen}
          onClose={() => setTripTypeOpen(false)}
          {...POPOVER_FRAME_PROPS}
        >
          <Popover.Target>
            <button
              type="button"
              style={fieldStyle('triptype', tripTypeOpen)}
              onMouseEnter={() => setHoveredField('triptype')}
              onMouseLeave={() => setHoveredField(null)}
              onClick={() => setTripTypeOpen((p) => !p)}
            >
              <span style={{ ...LABEL_STYLE, display: isMobile ? 'none' : undefined }}>Trip type</span>
              <span style={valueStyle(!tripType)}>{getTripTypeLabel(tripType)}</span>
            </button>
          </Popover.Target>
          <Popover.Dropdown style={{ padding: 8 }}>
            <TripTypeDialog
              value={tripType}
              onUpdate={(newTripType) => {
                dispatch(setTripType(newTripType));
                setTripTypeOpen(false);
                if (newTripType === 'multi-city') {
                  if (isInBookingFlow) navigate(`${routePrefix}/flights/search`);
                  else setRouteOpen(true);
                } else {
                  dispatchSearchTrigger();
                }
              }}
            />
          </Popover.Dropdown>
        </Popover>

        {DIVIDER}

        {/* ── Cabin ─────────────────────────────────────────────────────────── */}
        <Popover
          opened={cabinClassOpen}
          onClose={() => setCabinClassOpen(false)}
          {...POPOVER_FRAME_PROPS}
        >
          <Popover.Target>
            <button
              type="button"
              style={fieldStyle('cabin', cabinClassOpen)}
              onMouseEnter={() => setHoveredField('cabin')}
              onMouseLeave={() => setHoveredField(null)}
              onClick={() => setCabinClassOpen((p) => !p)}
            >
              <span style={{ ...LABEL_STYLE, display: isMobile ? 'none' : undefined }}>Cabin</span>
              <span style={valueStyle(!travellers.cabinClass)}>{travellers.cabinClass ?? 'Cabin'}</span>
            </button>
          </Popover.Target>
          <Popover.Dropdown style={{ padding: 8 }}>
            <CabinClassDialog
              value={travellers.cabinClass}
              onUpdate={(cabinClass) => {
                dispatch(setTravellers({ ...travellers, cabinClass }));
                setCabinClassOpen(false);
                dispatchSearchTrigger();
              }}
            />
          </Popover.Dropdown>
        </Popover>
      </div>
    </div>
  );
}

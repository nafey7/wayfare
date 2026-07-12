import {
  Alert,
  Box,
  Card,
  Divider,
  Group,
  Radio,
  Select,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Title,
  UnstyledButton,
} from '@mantine/core';
import { Edit, User } from 'lucide-react';
import type { HotelGuestDetails } from '@/types/hotels';
import type { StoredPassenger } from '@/types/passengers';
import { HOTEL_REVIEW_BOOKING_TOKENS } from '../utils/hotelReviewBookingTokens';
import { isGuestSlotComplete } from '../utils/guestSlotComplete';
import { formatIsoDobForDisplay } from '../utils/dateOfBirthDisplay';

const {
  base: BASE,
  textMain: TEXT_MAIN,
  textMuted: TEXT_MUTED,
  borderLight: BORDER_LIGHT,
  amber: AMBER,
  highlightBg: HIGHLIGHT_BG,
  shadowSelected: SHADOW_SELECTED,
  nationalityMuted: NATIONALITY_MUTED,
  amberText: AMBER_TEXT,
} = HOTEL_REVIEW_BOOKING_TOKENS;

const ADULT_TITLES: { value: HotelGuestDetails['title']; label: string }[] = [
  { value: 'Mr', label: 'Mr' },
  { value: 'Mrs', label: 'Mrs' },
  { value: 'Miss', label: 'Miss' },
];

const CHILD_TITLES: { value: HotelGuestDetails['title']; label: string }[] = [
  { value: 'Master', label: 'Master' },
  { value: 'Miss', label: 'Miss' },
];

function slotKey(roomNumber: number, localIndex: number): string {
  return `${roomNumber}-${localIndex}`;
}

function filterPassengersForSlot(savedPassengers: StoredPassenger[], slot: GuestSlot): StoredPassenger[] {
  return savedPassengers.filter((s) => {
    const t = s.typeHotel ?? s.type ?? 'adult';
    return (slot.isChild && t === 'child') || (!slot.isChild && t === 'adult');
  });
}

export interface GuestSlot {
  isChild: boolean;
  age?: number;
  label: string;
}

export interface GuestFormProps {
  roomNumber: number;
  /** Global index of the first guest in this room (for Redux-style maps). */
  globalSlotStartIndex: number;
  savedPassengerByGuestIndex: Record<number, string | 'manual'>;
  onSavedPassengerModeChange: (globalIndex: number, value: string | 'manual') => void;
  slots: GuestSlot[];
  guests: HotelGuestDetails[];
  onChange: (
    index: number,
    field: keyof Pick<HotelGuestDetails, 'title' | 'firstName' | 'lastName' | 'age'>,
    value: string | number
  ) => void;
  touched: boolean;
  isLeadGuest?: boolean;
  savedPassengers?: StoredPassenger[];
  onSelectSaved?: (
    localIndex: number,
    passenger: { title: string; firstName: string; lastName: string; dateOfBirth: string }
  ) => void;
  /** Open full profile editor (saved passenger). */
  onEditPassenger?: (passengerId: string) => void;
}

function radioCardStyle(selected: boolean, incomplete: boolean): React.CSSProperties {
  const borderColor = incomplete ? AMBER : selected ? BASE : BORDER_LIGHT;
  const borderWidth = selected || incomplete ? 2 : 1;
  return {
    border: `${borderWidth}px solid ${borderColor}`,
    borderRadius: 12,
    padding: '12px 24px',
    backgroundColor: selected ? HIGHLIGHT_BG : 'var(--mantine-color-body)',
    boxShadow: selected ? SHADOW_SELECTED : 'none',
    width: '100%',
    cursor: 'pointer',
    display: 'flex',
    flexDirection: 'row',
    flexWrap: 'nowrap',
    alignItems: 'flex-start',
    gap: 12,
  };
}

/**
 * Per-room guest block: saved passengers as radio cards plus "Enter manually"; title / first / last when manual is selected (or when there are no saved passengers).
 */
export function GuestForm({
  roomNumber,
  globalSlotStartIndex,
  savedPassengerByGuestIndex,
  onSavedPassengerModeChange,
  slots,
  guests,
  onChange,
  touched,
  isLeadGuest = false,
  savedPassengers = [],
  onSelectSaved,
  onEditPassenger,
}: GuestFormProps) {
  return (
    <Card mb="md" p="lg" radius="md" withBorder>
      {/* Room header */}
      <Group align="center" gap="xs" mb="sm">
        <User size={20} color="var(--mantine-color-navy-7)" />
        <Title order={6} fw={600}>
          {`Room ${roomNumber}`}
        </Title>
      </Group>
      <Divider mb="sm" />

      {slots.map((slot, index) => {
        const g = guests[index];
        const localKey = slotKey(roomNumber, index);
        const globalIndex = globalSlotStartIndex + index;
        const isLead = isLeadGuest && index === 0 && !slot.isChild;
        const slotLabel = `${slot.label}${isLead ? ' (Lead Guest)' : ''}${slot.isChild && slot.age != null ? ` (Age: ${slot.age})` : ''}`;
        const filteredSaved = filterPassengersForSlot(savedPassengers, slot);
        const mode = savedPassengerByGuestIndex[globalIndex];
        const radioGroupValue = mode ?? '';
        const hasSavedOptions = filteredSaved.length > 0;
        const showManual = !hasSavedOptions || mode === 'manual';
        const complete = isGuestSlotComplete(g, slot, touched);

        return (
          <Box
            key={localKey}
            mb={index < slots.length - 1 ? 'md' : 0}
            p="sm"
            style={{
              borderRadius: 8,
              backgroundColor: 'var(--mantine-color-gray-0)',
              border: '1px solid var(--mantine-color-gray-2)',
            }}
          >
            {/* Slot title */}
            <Group align="center" gap="xs" mb="sm">
              <User size={20} color={BASE} />
              <Text
                component="span"
                style={{
                  fontSize: 18,
                  fontWeight: 700,
                  lineHeight: '24px',
                  color: TEXT_MAIN,
                  margin: 0,
                  display: 'block',
                }}
              >
                {slotLabel}
              </Text>
            </Group>

            {/* Saved passengers — radio cards */}
            {hasSavedOptions && onSelectSaved ? (
              <Radio.Group
                value={radioGroupValue}
                onChange={(passengerId) => {
                  if (passengerId === 'manual') {
                    onSavedPassengerModeChange(globalIndex, 'manual');
                    return;
                  }
                  onSavedPassengerModeChange(globalIndex, passengerId);
                  const p = filteredSaved.find((s) => s.id === passengerId);
                  if (!p) return;
                  const titleForSlot = slot.isChild ? (p.hotelTitle ?? p.title) : p.title;
                  onSelectSaved(index, {
                    title: titleForSlot,
                    firstName: p.firstName,
                    lastName: p.lastName,
                    dateOfBirth: p.dateOfBirth,
                  });
                }}
              >
                <Stack gap="sm" mb={showManual ? 'sm' : 0}>
                  {filteredSaved.map((p) => {
                    const selected = radioGroupValue === p.id;
                    const titleLine = `${p.firstName} ${p.lastName}`.trim() || 'Saved passenger';
                    const nationality = p.nationality?.trim() || '—';
                    const incompleteCard = selected && touched && !complete;

                    return (
                      <Box
                        key={p.id}
                        style={radioCardStyle(selected, incompleteCard)}
                        onClick={() => {
                          onSavedPassengerModeChange(globalIndex, p.id);
                          const titleForSlot = slot.isChild ? (p.hotelTitle ?? p.title) : p.title;
                          onSelectSaved?.(index, {
                            title: titleForSlot,
                            firstName: p.firstName,
                            lastName: p.lastName,
                            dateOfBirth: p.dateOfBirth,
                          });
                        }}
                      >
                        <Radio value={p.id} size="sm" mt={3} aria-label={titleLine} />
                        <Stack gap={12} style={{ flex: 1, minWidth: 0 }}>
                          <Group justify="space-between" align="flex-start" gap="xs" style={{ minWidth: 0 }}>
                            <Text
                              component="span"
                              style={{
                                fontSize: 18,
                                fontWeight: 700,
                                lineHeight: '25px',
                                color: TEXT_MAIN,
                                flex: '1 1 auto',
                                minWidth: 0,
                              }}
                            >
                              {titleLine}
                            </Text>
                            {onEditPassenger ? (
                              <UnstyledButton
                                onClick={(e) => {
                                  e.preventDefault();
                                  e.stopPropagation();
                                  onEditPassenger(p.id);
                                }}
                                style={{
                                  height: 32,
                                  flexShrink: 0,
                                  borderRadius: 8,
                                  backgroundColor: incompleteCard
                                    ? 'rgba(245, 158, 11, 0.25)'
                                    : 'rgba(107, 114, 183, 0.1)',
                                  fontWeight: 600,
                                  fontSize: 14,
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: 4,
                                  padding: '0 12px',
                                }}
                              >
                                <Edit size={18} />
                                {incompleteCard ? 'Complete' : 'Edit'}
                              </UnstyledButton>
                            ) : null}
                          </Group>
                          <Text
                            component="span"
                            style={{
                              fontSize: 14,
                              fontWeight: 400,
                              lineHeight: '18px',
                              color: TEXT_MUTED,
                              margin: 0,
                              display: 'block',
                            }}
                          >
                            DOB: {formatIsoDobForDisplay(p.dateOfBirth)}
                          </Text>
                          <Text
                            component="span"
                            style={{
                              fontSize: 14,
                              fontWeight: 400,
                              lineHeight: '18px',
                              color: TEXT_MUTED,
                              margin: 0,
                              display: 'block',
                            }}
                          >
                            Nationality:{' '}
                            <span style={{ color: NATIONALITY_MUTED, fontSize: 'inherit', fontWeight: 400 }}>
                              {nationality}
                            </span>
                          </Text>

                          {incompleteCard ? (
                            <Alert
                              color="yellow"
                              styles={{
                                root: {
                                  padding: '4px 8px',
                                  borderRadius: 8,
                                  border: `1px solid ${AMBER}`,
                                  backgroundColor: 'var(--mantine-color-body)',
                                },
                              }}
                            >
                              <Text
                                component="span"
                                style={{
                                  fontSize: 13,
                                  fontWeight: 600,
                                  lineHeight: '16px',
                                  color: AMBER_TEXT,
                                  margin: 0,
                                }}
                              >
                                Missing information
                              </Text>
                            </Alert>
                          ) : null}
                        </Stack>
                      </Box>
                    );
                  })}

                  <Box
                    style={radioCardStyle(
                      radioGroupValue === 'manual',
                      radioGroupValue === 'manual' && touched && !complete
                    )}
                    onClick={() => onSavedPassengerModeChange(globalIndex, 'manual')}
                  >
                    <Radio value="manual" size="sm" mt={3} aria-label="Enter manually" />
                    <Stack gap="xs" style={{ flex: 1, minWidth: 0 }}>
                      <Text
                        component="span"
                        style={{
                          fontSize: 18,
                          fontWeight: 700,
                          lineHeight: '25px',
                          color: TEXT_MAIN,
                          margin: 0,
                          display: 'block',
                        }}
                      >
                        Enter manually
                      </Text>
                      <Text
                        component="span"
                        style={{
                          fontSize: 14,
                          fontWeight: 400,
                          lineHeight: '18px',
                          color: TEXT_MUTED,
                          margin: 0,
                          display: 'block',
                        }}
                      >
                        Type title and name for this guest
                      </Text>
                      {radioGroupValue === 'manual' && touched && !complete ? (
                        <Alert
                          color="yellow"
                          styles={{
                            root: {
                              padding: '4px 8px',
                              borderRadius: 8,
                              border: `1px solid ${AMBER}`,
                              backgroundColor: 'var(--mantine-color-body)',
                            },
                          }}
                        >
                          <Text
                            component="span"
                            style={{
                              fontSize: 13,
                              fontWeight: 600,
                              lineHeight: '16px',
                              color: AMBER_TEXT,
                              margin: 0,
                            }}
                          >
                            Missing information
                          </Text>
                        </Alert>
                      ) : null}
                    </Stack>
                  </Box>
                </Stack>
              </Radio.Group>
            ) : null}

            {/* Manual title / first / last (and age for children) */}
            {showManual ? (
              <Box>
                <Divider mb="sm" />
                <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md">
                  <Select
                    label="Title"
                    value={g?.title ?? ''}
                    onChange={(value) => onChange(index, 'title', value ?? '')}
                    data={(slot.isChild ? CHILD_TITLES : ADULT_TITLES).map((opt) => ({
                      value: opt.value,
                      label: opt.label,
                    }))}
                    size="sm"
                    required
                    error={touched && !(g?.title ?? '')}
                    allowDeselect={false}
                    style={{ maxWidth: 100 }}
                  />
                  <TextInput
                    label="First name"
                    value={g?.firstName ?? ''}
                    onChange={(e) => onChange(index, 'firstName', e.currentTarget.value)}
                    size="sm"
                    required
                    error={touched && !(g?.firstName ?? '').trim()}
                  />
                  <TextInput
                    label="Last name"
                    value={g?.lastName ?? ''}
                    onChange={(e) => onChange(index, 'lastName', e.currentTarget.value)}
                    size="sm"
                    required
                    error={touched && !(g?.lastName ?? '').trim()}
                  />
                  {slot.isChild ? (
                    <TextInput
                      label="Age"
                      type="number"
                      min={0}
                      max={17}
                      value={String(g?.age ?? slot.age ?? '')}
                      onChange={(e) => {
                        const v = e.currentTarget.value;
                        onChange(index, 'age', v === '' ? 0 : parseInt(v, 10) || 0);
                      }}
                      size="sm"
                      required
                      error={touched && (g?.age == null || g?.age < 0 || g?.age > 17)}
                      style={{ gridColumn: '1 / -1' }}
                    />
                  ) : null}
                </SimpleGrid>
              </Box>
            ) : null}
          </Box>
        );
      })}
    </Card>
  );
}

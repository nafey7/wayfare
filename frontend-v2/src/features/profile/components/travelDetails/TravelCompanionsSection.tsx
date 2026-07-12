import { useState } from 'react';
import { Box, Divider, Stack, Text, UnstyledButton } from '@mantine/core';
import { ChevronRight, PlusCircle } from 'lucide-react';
import { NAVY, MUTED, LINE, MIST } from '../../profileTokens';

const AVATAR_COLORS = [
  'linear-gradient(135deg, #9AA2C5, #9AA2C5)',
  'linear-gradient(135deg, #FFB74D, #F57C00)',
  'linear-gradient(135deg, #81C784, #388E3C)',
  'linear-gradient(135deg, #64B5F6, #1565C0)',
  'linear-gradient(135deg, #F48FB1, #C2185B)',
];

function getInitials(fullName: string): string {
  const trimmed = fullName.trim();
  if (!trimmed || trimmed === '—') return '?';
  const parts = trimmed.split(/\s+/);
  if (parts.length >= 2 && parts[0] && parts[parts.length - 1]) {
    return `${parts[0][0]}${parts[parts.length - 1]![0]}`.toUpperCase();
  }
  return trimmed.slice(0, 2).toUpperCase();
}

function passportExpiryStatus(
  expiry: string | null | undefined
): 'ok' | 'soon' | 'expired' | null {
  if (!expiry || expiry === '—') return null;
  const exp = new Date(expiry);
  if (isNaN(exp.getTime())) return null;
  const now = new Date();
  const monthsLeft = (exp.getTime() - now.getTime()) / (1000 * 60 * 60 * 24 * 30);
  if (exp < now) return 'expired';
  if (monthsLeft < 6) return 'soon';
  return 'ok';
}

function formatExpiryShort(expiry: string | null | undefined): string | null {
  if (!expiry || expiry === '—') return null;
  const d = new Date(expiry);
  if (isNaN(d.getTime())) return null;
  return d.toLocaleDateString('en-GB', { month: 'short', year: 'numeric' });
}

function passengerTypeLabel(type?: string | null): string {
  if (type === 'child') return 'Child';
  if (type === 'infant') return 'Infant';
  return 'Adult';
}

function ExpiryChip({ status }: { status: 'ok' | 'soon' | 'expired' }) {
  if (status === 'ok') {
    return (
      <Box
        style={{
          background: '#E8EAFC',
          color: NAVY,
          fontWeight: 700,
          fontSize: 11,
          height: 24,
          borderRadius: 12,
          padding: '0 8px',
          display: 'inline-flex',
          alignItems: 'center',
          whiteSpace: 'nowrap',
          flexShrink: 0,
        }}
      >
        Complete
      </Box>
    );
  }
  return (
    <Box
      style={{
        border: '1.5px solid #D0D4EC',
        color: '#9AA2C5',
        fontSize: 11,
        height: 24,
        borderRadius: 12,
        padding: '0 8px',
        display: 'inline-flex',
        alignItems: 'center',
        background: 'transparent',
        whiteSpace: 'nowrap',
        flexShrink: 0,
      }}
    >
      {status === 'expired' ? '! Expired' : '! Expires soon'}
    </Box>
  );
}

export interface TravelCompanionData {
  id?: string;
  fullLegalName: string;
  dateOfBirth: string;
  nationality: string;
  hasPassport: boolean;
  type?: 'adult' | 'child' | 'infant' | null;
  passportExpiry?: string | null;
}

export interface TravelCompanionsSectionProps {
  companions?: TravelCompanionData[];
  onAdd?: () => void;
  onEdit?: (passengerId: string) => void;
}

function CompanionRow({
  companion,
  index,
  onEdit,
}: {
  companion: TravelCompanionData;
  index: number;
  onEdit?: (passengerId: string) => void;
}) {
  const [hovered, setHovered] = useState(false);
  const expStatus = passportExpiryStatus(companion.passportExpiry);
  const expiryShort = formatExpiryShort(companion.passportExpiry);
  const avatarBg = AVATAR_COLORS[index % AVATAR_COLORS.length];
  const initials = getInitials(companion.fullLegalName);
  const typeLabel = passengerTypeLabel(companion.type);
  const subtitleParts = [typeLabel];
  if (expiryShort) subtitleParts.push(`Passport expires ${expiryShort}`);

  return (
    <UnstyledButton
      onClick={() => companion.id && onEdit?.(companion.id)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 16,
        padding: '12px 20px',
        cursor: 'pointer',
        transition: 'background 120ms',
        backgroundColor: hovered ? MIST : 'transparent',
        width: '100%',
      }}
    >
      <Box
        style={{
          width: 40,
          height: 40,
          borderRadius: '50%',
          background: avatarBg,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          color: 'white',
          fontSize: 14,
          fontWeight: 700,
        }}
      >
        {initials}
      </Box>
      <Box style={{ flex: 1, minWidth: 0 }}>
        <Text style={{ fontSize: 14, fontWeight: 600, color: NAVY, margin: 0 }}>
          {companion.fullLegalName}
        </Text>
        <Text style={{ fontSize: 12, color: MUTED, marginTop: 2, margin: 0 }}>
          {subtitleParts.join(' · ')}
        </Text>
      </Box>
      {expStatus && <ExpiryChip status={expStatus} />}
      <ChevronRight size={20} color="#9AA2C5" style={{ flexShrink: 0 }} />
    </UnstyledButton>
  );
}

function AddCompanionButton({ onAdd }: { onAdd?: () => void }) {
  const [hovered, setHovered] = useState(false);

  return (
    <UnstyledButton
      onClick={onAdd}
      disabled={!onAdd}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
        background: hovered ? MIST : 'white',
        borderRadius: 14,
        border: `1.5px dashed ${hovered ? NAVY : LINE}`,
        padding: '12px 20px',
        cursor: onAdd ? 'pointer' : 'default',
        color: hovered ? NAVY : MUTED,
        fontSize: 14,
        fontWeight: 600,
        transition: 'all 120ms',
        width: '100%',
      }}
    >
      <PlusCircle size={20} />
      Add companion
    </UnstyledButton>
  );
}

export function TravelCompanionsSection({
  companions = [],
  onAdd,
  onEdit,
}: TravelCompanionsSectionProps) {
  return (
    <Stack gap="md" style={{ width: '100%' }}>
      <Box>
        <Text style={{ fontSize: 22, fontWeight: 900, color: NAVY, marginBottom: 4 }}>
          Travel companions
        </Text>
        <Text style={{ fontSize: 13, color: MUTED, lineHeight: 1.6 }}>
          Save companions' details so Voya can include them in bookings automatically.
        </Text>
      </Box>

      {companions.length > 0 && (
        <Box
          style={{
            background: 'white',
            borderRadius: 14,
            border: `1px solid ${LINE}`,
            overflow: 'hidden',
          }}
        >
          {companions.map((companion, i) => (
            <Box key={companion.id ?? i}>
              {i > 0 && (
                <Divider style={{ marginLeft: 20, marginRight: 20, borderColor: LINE }} />
              )}
              <CompanionRow companion={companion} index={i} onEdit={onEdit} />
            </Box>
          ))}
        </Box>
      )}

      <AddCompanionButton onAdd={onAdd} />
    </Stack>
  );
}

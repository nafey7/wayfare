import {
  ActionIcon,
  Box,
  Button,
  Group,
  SegmentedControl,
  Stack,
  Text,
  TextInput,
  UnstyledButton,
} from '@mantine/core';
import { Hotel as HotelIcon, Pencil, PlaneTakeoff, PlusCircle, Trash } from 'lucide-react';
import { LANDING_TOKENS } from '@/features/landing/landingTokens';
import { useState } from 'react';
import { SectionHeader } from '../../shared';

const overlineStyle: React.CSSProperties = {
  fontSize: 12,
  fontWeight: 600,
  lineHeight: '16px',
  letterSpacing: 0.1,
  color: LANDING_TOKENS.textHighlight,
  margin: 0,
  display: 'block',
  fontFamily: LANDING_TOKENS.fontFamily.display,
};

const overlineCapsStyle: React.CSSProperties = {
  ...overlineStyle,
  letterSpacing: 1.1,
  textTransform: 'uppercase',
};

const valueStyle: React.CSSProperties = {
  fontSize: 16,
  fontWeight: 600,
  lineHeight: '20px',
  color: LANDING_TOKENS.textColor,
  margin: 0,
  display: 'block',
  fontFamily: LANDING_TOKENS.fontFamily.display,
};

export interface LoyaltyProgram {
  id: string;
  type: 'airline' | 'hotel';
  providerName: string;
  programName: string;
  memberNumber: string;
}

interface ProgramCardProps {
  program: LoyaltyProgram;
  onEdit?: (program: LoyaltyProgram) => void;
  onDelete?: (program: LoyaltyProgram) => void;
}

function ProgramCard({ program, onEdit, onDelete }: ProgramCardProps) {
  const Icon = program.type === 'airline' ? PlaneTakeoff : HotelIcon;
  return (
    <Group
      justify="space-between"
      align="center"
      style={{
        paddingLeft: 17,
        paddingRight: 17,
        paddingTop: 13,
        paddingBottom: 13,
        backgroundColor: 'white',
        border: '1px solid #e5e7eb',
        borderRadius: 14,
      }}
    >
      <Group gap={36} align="center">
        <Box
          style={{
            width: 36,
            height: 36,
            borderRadius: 8,
            backgroundColor: LANDING_TOKENS.baseLight,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Icon size={18} color={LANDING_TOKENS.textColor} />
        </Box>
        <Box>
          <Text component="span" style={overlineStyle}>
            {program.providerName}
          </Text>
          <Text component="span" style={{ ...valueStyle, marginTop: 2 }}>
            {program.programName}
          </Text>
        </Box>
        <Box>
          <Text component="span" style={overlineCapsStyle}>
            Member No.
          </Text>
          <Text component="span" style={{ ...valueStyle, marginTop: 2 }}>
            {program.memberNumber}
          </Text>
        </Box>
      </Group>
      <Group gap="xs">
        {onEdit && (
          <ActionIcon
            size={36}
            radius={8}
            variant="filled"
            onClick={() => onEdit(program)}
            aria-label="Edit"
            style={{ backgroundColor: LANDING_TOKENS.baseLight, color: LANDING_TOKENS.textColor }}
          >
            <Pencil size={18} />
          </ActionIcon>
        )}
        {onDelete && (
          <ActionIcon
            size={36}
            radius={8}
            variant="filled"
            onClick={() => onDelete(program)}
            aria-label="Delete"
            style={{ backgroundColor: LANDING_TOKENS.baseLight, color: LANDING_TOKENS.textColor }}
          >
            <Trash size={18} />
          </ActionIcon>
        )}
      </Group>
    </Group>
  );
}

const DEFAULT_AIRLINES: LoyaltyProgram[] = [
  { id: '1', type: 'airline', providerName: 'British Airways', programName: 'Executive Club', memberNumber: 'BA•••• 5523' },
  { id: '2', type: 'airline', providerName: 'Delta Air Lines', programName: 'SkyMiles', memberNumber: 'UA•••• 4821' },
  { id: '3', type: 'airline', providerName: 'United Airlines', programName: 'MileagePlus', memberNumber: 'AA•••• 7392' },
];

const DEFAULT_HOTELS: LoyaltyProgram[] = [
  { id: '4', type: 'hotel', providerName: 'Marriott', programName: 'Bonvoy', memberNumber: 'MA•••• 9047' },
  { id: '5', type: 'hotel', providerName: 'Hilton', programName: 'Honors', memberNumber: 'HH•••• 3318' },
];

export interface FrequentFlyerSectionProps {
  airlinePrograms?: LoyaltyProgram[];
  hotelPrograms?: LoyaltyProgram[];
}

/**
 * Frequent Flyer section — loyalty program details within Travel details.
 */
export function FrequentFlyerSection({
  airlinePrograms = DEFAULT_AIRLINES,
  hotelPrograms = DEFAULT_HOTELS,
}: FrequentFlyerSectionProps) {
  const [formExpanded, setFormExpanded] = useState(false);
  const [type, setType] = useState<'airline' | 'hotel'>('airline');
  const [airlineName, setAirlineName] = useState('');
  const [programName, setProgramName] = useState('');
  const [memberNumber, setMemberNumber] = useState('');
  const [pointsLabel, setPointsLabel] = useState('');

  const canSave =
    airlineName.trim().length > 0 &&
    programName.trim().length > 0 &&
    memberNumber.trim().length > 0 &&
    pointsLabel.trim().length > 0;

  return (
    <Stack gap={31} style={{ width: '100%' }}>
      <Stack gap="sm">
        <SectionHeader label={`Airlines Programs (${airlinePrograms.length})`} variant="large" px={2} />
        <Stack gap="sm">
          {airlinePrograms.map((p) => (
            <ProgramCard key={p.id} program={p} onEdit={() => {}} onDelete={() => {}} />
          ))}
        </Stack>
      </Stack>

      <Stack gap="sm">
        <SectionHeader label={`Hotel Programs (${hotelPrograms.length})`} variant="large" px={2} />
        <Stack gap="sm">
          {hotelPrograms.map((p) => (
            <ProgramCard key={p.id} program={p} onEdit={() => {}} onDelete={() => {}} />
          ))}
        </Stack>
      </Stack>

      {!formExpanded ? (
        <UnstyledButton
          onClick={() => setFormExpanded(true)}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '100%',
            paddingLeft: 17,
            paddingRight: 17,
            paddingTop: 18,
            paddingBottom: 18,
            backgroundColor: 'white',
            border: '1px solid #e5e7eb',
            borderRadius: 14,
            cursor: 'pointer',
            textAlign: 'center',
          }}
        >
          <PlusCircle size={24} color={LANDING_TOKENS.baseColor} style={{ marginRight: 16 }} />
          <Text
            component="span"
            style={{
              fontSize: 16,
              fontWeight: 600,
              lineHeight: '20px',
              color: LANDING_TOKENS.baseColor,
              fontFamily: LANDING_TOKENS.fontFamily.display,
            }}
          >
            Add Loyalty Program
          </Text>
        </UnstyledButton>
      ) : (
        <Box
          style={{
            backgroundColor: LANDING_TOKENS.baseColor10,
            border: '1px solid #e5e7eb',
            borderRadius: 14,
            paddingTop: 21,
            paddingLeft: 21,
            paddingRight: 21,
            paddingBottom: 1,
            display: 'flex',
            flexDirection: 'column',
            gap: 16,
          }}
        >
          <Text
            component="span"
            style={{
              fontSize: 11,
              fontWeight: 400,
              lineHeight: '16.5px',
              letterSpacing: 0.55,
              color: '#6b7280',
              textTransform: 'uppercase',
              margin: 0,
              display: 'block',
              fontFamily: LANDING_TOKENS.fontFamily.display,
            }}
          >
            Type
          </Text>

          <SegmentedControl
            value={type}
            onChange={(v) => setType(v as 'airline' | 'hotel')}
            data={[
              {
                value: 'airline',
                label: (
                  <Group gap={6} align="center" wrap="nowrap">
                    <PlaneTakeoff size={18} />
                    Airline
                  </Group>
                ),
              },
              {
                value: 'hotel',
                label: (
                  <Group gap={6} align="center" wrap="nowrap">
                    <HotelIcon size={18} />
                    Hotel
                  </Group>
                ),
              },
            ]}
            color="brand.6"
            style={{ width: '100%', maxWidth: 295, height: 48 }}
            styles={{ root: { borderRadius: 20 } }}
          />

          <Group align="flex-start" gap={0} style={{ width: '100%', flexWrap: 'wrap' }}>
            <Box style={{ flex: 1, minWidth: 220, paddingLeft: 16, paddingRight: 16, paddingTop: 14, paddingBottom: 16 }}>
              <Text
                component="span"
                style={{
                  fontSize: 16,
                  fontWeight: 600,
                  lineHeight: '20px',
                  color: LANDING_TOKENS.textColor,
                  margin: 0,
                  display: 'block',
                  paddingBottom: 4,
                  fontFamily: LANDING_TOKENS.fontFamily.display,
                }}
              >
                {type === 'airline' ? 'Airline Name' : 'Hotel Name'}
              </Text>
              <TextInput
                placeholder={type === 'airline' ? 'e.g. Avianca' : 'e.g. Marriott'}
                value={airlineName}
                onChange={(e) => setAirlineName(e.currentTarget.value)}
                size="sm"
                radius="sm"
                styles={{ input: { height: 48, fontFamily: LANDING_TOKENS.fontFamily.display, fontSize: 16 } }}
              />
            </Box>
            <Box style={{ flex: 1, minWidth: 220, paddingLeft: 16, paddingRight: 16, paddingTop: 14, paddingBottom: 16 }}>
              <Text
                component="span"
                style={{
                  fontSize: 16,
                  fontWeight: 600,
                  lineHeight: '20px',
                  color: LANDING_TOKENS.textColor,
                  margin: 0,
                  display: 'block',
                  paddingBottom: 4,
                  fontFamily: LANDING_TOKENS.fontFamily.display,
                }}
              >
                Program Name
              </Text>
              <TextInput
                placeholder="e.g. LifeMiles"
                value={programName}
                onChange={(e) => setProgramName(e.currentTarget.value)}
                size="sm"
                radius="sm"
                styles={{ input: { height: 48, fontFamily: LANDING_TOKENS.fontFamily.display, fontSize: 16 } }}
              />
            </Box>
          </Group>

          <Group align="flex-start" gap={0} style={{ width: '100%', flexWrap: 'wrap' }}>
            <Box style={{ flex: 1, minWidth: 220, paddingLeft: 16, paddingRight: 16, paddingTop: 14, paddingBottom: 16 }}>
              <Text
                component="span"
                style={{
                  fontSize: 16,
                  fontWeight: 600,
                  lineHeight: '20px',
                  color: LANDING_TOKENS.textColor,
                  margin: 0,
                  display: 'block',
                  paddingBottom: 4,
                  fontFamily: LANDING_TOKENS.fontFamily.display,
                }}
              >
                Member Number
              </Text>
              <TextInput
                placeholder="AV123456"
                value={memberNumber}
                onChange={(e) => setMemberNumber(e.currentTarget.value)}
                size="sm"
                radius="sm"
                styles={{ input: { height: 48, fontFamily: LANDING_TOKENS.fontFamily.display, fontSize: 16 } }}
              />
            </Box>
            <Box style={{ flex: 1, minWidth: 220, paddingLeft: 16, paddingRight: 16, paddingTop: 14, paddingBottom: 16 }}>
              <Text
                component="span"
                style={{
                  fontSize: 16,
                  fontWeight: 600,
                  lineHeight: '20px',
                  color: LANDING_TOKENS.textColor,
                  margin: 0,
                  display: 'block',
                  paddingBottom: 4,
                  fontFamily: LANDING_TOKENS.fontFamily.display,
                }}
              >
                Points Label
              </Text>
              <TextInput
                placeholder="Miles"
                value={pointsLabel}
                onChange={(e) => setPointsLabel(e.currentTarget.value)}
                size="sm"
                radius="sm"
                styles={{ input: { height: 48, fontFamily: LANDING_TOKENS.fontFamily.display, fontSize: 16 } }}
              />
            </Box>
          </Group>

          <Group justify="flex-end" gap="xs" style={{ paddingTop: 16, paddingBottom: 16, paddingLeft: 24, paddingRight: 24 }}>
            <Button
              variant="subtle"
              tt="none"
              fw={600}
              onClick={() => setFormExpanded(false)}
              c={LANDING_TOKENS.textColor}
            >
              Cancel
            </Button>
            <Button
              disabled={!canSave}
              radius={100}
              tt="none"
              fw={600}
              style={{
                backgroundColor: LANDING_TOKENS.baseColor,
                color: LANDING_TOKENS.textLight,
              }}
            >
              Save Program
            </Button>
          </Group>
        </Box>
      )}
    </Stack>
  );
}

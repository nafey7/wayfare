/// <reference types="vite/client" />
import { Accordion, Box, Button, Card, Group, Stack, Text } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import {
  CheckCircle,
  Clock,
  History,
  Hotel as HotelIcon,
  PlaneTakeoff,
  Zap,
} from 'lucide-react';
import tokyoImage from '../../../../assets/images/landing-page/example-itineraries/Tokyo.png';
import { LANDING_TOKENS } from '../../../landing/landingTokens';

/** Action item for the trip status list */
export interface ActionItem {
  id: string;
  label: string;
  linkText?: string;
  completed: boolean;
}

export interface VoyaAIActiveSessionProps {
  title?: string;
  lastActive?: string;
  destination?: string;
  tripSummary?: string;
  flightRoute?: string;
  flightPrice?: string;
  flightDetails?: string;
  hotelName?: string;
  hotelPrice?: string;
  hotelDetails?: string;
  backgroundImage?: string;
  actionItems?: ActionItem[];
  resumeLabel?: string;
  discardLabel?: string;
}

const BASE_COLOR = LANDING_TOKENS.baseColor;
const BASE_LIGHTER = LANDING_TOKENS.baseLighter;
const HIGHLIGHT_GREEN = '#caff33';
const TEXT_LIGHT = LANDING_TOKENS.textLight;

const defaultActionItems: ActionItem[] = [
  { id: '1', label: 'Itinerary created', completed: true },
  { id: '2', label: 'Arrange activities', completed: true },
  {
    id: '3',
    label: 'Secure travel → ',
    linkText: 'Review flights',
    completed: false,
  },
  {
    id: '4',
    label: 'Secure accommodation → ',
    linkText: 'Review hotel',
    completed: false,
  },
];

/**
 * Voya AI active session — callout pill and main trip card with gradient overlay.
 */
export function VoyaAIActiveSession({
  title = 'Voya AI · Active Session',
  lastActive = 'Continue where you left off · 2 days ago',
  destination = 'Tokyo',
  tripSummary = 'Mar 10 – 18 · 8 nights · 2 passengers',
  flightRoute = 'JFK → NRT',
  flightPrice = '$2,000 - $2,800',
  flightDetails = 'JAL 5 · Business · Nonstop',
  hotelName = 'Andaz Tokyo',
  hotelPrice = '$225 - $315/night',
  hotelDetails = 'Toranomon · 5★ · Breakfast included',
  backgroundImage = tokyoImage,
  actionItems = defaultActionItems,
  resumeLabel = 'Resume your Trip',
  discardLabel = 'Discard this Trip',
}: VoyaAIActiveSessionProps) {
  const isLgUp = useMediaQuery('(min-width: 1200px)') ?? false;
  const isSmUp = useMediaQuery('(min-width: 600px)') ?? false;

  return (
    <Accordion
      defaultValue="voya-ai"
      variant="default"
      chevronPosition="right"
      styles={{
        item: { border: 'none' },
        control: { padding: '10px 16px', minHeight: 48 },
        content: { padding: 0, paddingBottom: 24 },
        chevron: { color: LANDING_TOKENS.textColor },
      }}
    >
      <Accordion.Item value="voya-ai">
        <Accordion.Control>
          <Text
            component="span"
            style={{
              fontFamily: LANDING_TOKENS.fontFamily.display,
              fontSize: 28,
              fontWeight: 700,
              lineHeight: '36px',
              color: LANDING_TOKENS.textColor,
            }}
          >
            {title}
          </Text>
        </Accordion.Control>
        <Accordion.Panel>
          <Stack gap="lg" px="md" style={{ width: '100%' }}>
            <Group
              align="center"
              gap={11}
              style={{
                width: 'fit-content',
                paddingLeft: 24,
                paddingRight: 24,
                paddingTop: 13,
                paddingBottom: 13,
                borderRadius: 100,
                backgroundColor: BASE_COLOR,
              }}
            >
              <Zap size={24} color={TEXT_LIGHT} />
              <Text
                style={{
                  fontFamily: LANDING_TOKENS.fontFamily.display,
                  fontSize: 16,
                  fontWeight: 600,
                  lineHeight: '20px',
                  letterSpacing: '1px',
                  color: TEXT_LIGHT,
                  textTransform: 'uppercase',
                }}
              >
                {title}
              </Text>
              <Box
                style={{
                  width: 11.43,
                  height: 11.43,
                  borderRadius: '50%',
                  backgroundColor: HIGHLIGHT_GREEN,
                  opacity: 0.83,
                  boxShadow: '0 0 11.43px #caff33',
                }}
              />
            </Group>

            <Box
              style={{
                position: 'relative',
                width: '100%',
                minHeight: 382,
                borderRadius: 28,
                overflow: 'hidden',
                boxShadow:
                  '0px 2px 6px -8px rgba(0,0,0,0.1), 0px 10px 18px -6px rgba(0,0,0,0.12)',
              }}
            >
              <Box
                style={{
                  position: 'absolute',
                  inset: 0,
                  backgroundImage: `url(${backgroundImage})`,
                  backgroundSize: 'cover',
                  backgroundPosition: 'center',
                }}
              />
              <Box
                style={{
                  position: 'absolute',
                  inset: 0,
                  background:
                    'linear-gradient(132.26deg, rgba(8, 7, 42, 0.95) 7.735%, rgba(8, 7, 42, 0.75) 45.774%, rgba(8, 7, 42, 0.2) 92.265%)',
                }}
              />
              <Box
                style={{
                  position: 'absolute',
                  inset: 0,
                  background:
                    'linear-gradient(163.57deg, rgba(107, 114, 183, 0.15) 0%, rgba(0, 0, 0, 0) 60%)',
                }}
              />

              <Box
                style={{
                  position: 'relative',
                  display: 'flex',
                  flexDirection: isLgUp ? 'row' : 'column',
                  gap: 24,
                  paddingLeft: isLgUp ? 75 : 24,
                  paddingRight: isLgUp ? 75 : 24,
                  paddingTop: isLgUp ? 38 : 24,
                  paddingBottom: isLgUp ? 38 : 24,
                }}
              >
                <Stack gap={22} style={{ flex: 1, minWidth: 0 }}>
                  <Group align="flex-start" gap={11}>
                    <Clock size={24} color={TEXT_LIGHT} style={{ marginTop: 2 }} />
                    <Text
                      style={{
                        fontFamily: LANDING_TOKENS.fontFamily.display,
                        fontSize: 16,
                        fontWeight: 600,
                        lineHeight: '20px',
                        letterSpacing: '1px',
                        color: TEXT_LIGHT,
                        textTransform: 'uppercase',
                      }}
                    >
                      {lastActive}
                    </Text>
                  </Group>
                  <Text
                    component="h2"
                    style={{
                      fontFamily: LANDING_TOKENS.fontFamily.display,
                      fontSize: isSmUp ? 45 : 32,
                      fontWeight: 700,
                      lineHeight: isSmUp ? '52px' : '40px',
                      color: TEXT_LIGHT,
                      margin: 0,
                    }}
                  >
                    Your trip to{' '}
                    <Box
                      component="span"
                      style={{
                        background: 'linear-gradient(90deg, #fff 0%, #c0c6f4 50%, #7c86ff 100%)',
                        backgroundClip: 'text',
                        WebkitBackgroundClip: 'text',
                        color: 'transparent',
                      }}
                    >
                      {destination}
                    </Box>
                  </Text>
                  <Text
                    style={{
                      fontFamily: LANDING_TOKENS.fontFamily.display,
                      fontSize: 16,
                      fontWeight: 600,
                      lineHeight: '20px',
                      color: TEXT_LIGHT,
                    }}
                  >
                    {tripSummary}
                  </Text>
                  <Stack gap={29} style={{ flexDirection: isSmUp ? 'row' : 'column', flexWrap: 'wrap' }}>
                    <Card
                      radius={18}
                      padding={17}
                      style={{
                        flex: isSmUp ? 1 : undefined,
                        minWidth: isSmUp ? 340 : undefined,
                        maxWidth: 341,
                        backgroundColor: 'rgba(255,255,255,0.5)',
                        border: `1.275px solid ${BASE_LIGHTER}`,
                      }}
                    >
                      <Group gap={18} align="center" wrap="nowrap">
                        <Box
                          style={{
                            width: 43.4,
                            height: 43.4,
                            borderRadius: 13,
                            backgroundColor: 'rgba(202,255,51,0.1)',
                            border: '1.275px solid rgba(202,255,51,0.1)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            flexShrink: 0,
                          }}
                        >
                          <PlaneTakeoff size={24} color={TEXT_LIGHT} />
                        </Box>
                        <Box style={{ minWidth: 0, flex: 1 }}>
                          <Group justify="space-between" align="center" gap="xs">
                            <Text
                              style={{
                                fontFamily: LANDING_TOKENS.fontFamily.display,
                                fontSize: 16,
                                fontWeight: 600,
                                color: TEXT_LIGHT,
                              }}
                            >
                              {flightRoute}
                            </Text>
                            <Text
                              style={{
                                fontFamily: LANDING_TOKENS.fontFamily.display,
                                fontSize: 16,
                                fontWeight: 600,
                                color: HIGHLIGHT_GREEN,
                              }}
                            >
                              {flightPrice}
                            </Text>
                          </Group>
                          <Text
                            style={{
                              fontFamily: LANDING_TOKENS.fontFamily.display,
                              fontSize: 14,
                              fontWeight: 600,
                              color: LANDING_TOKENS.textSecondary,
                              letterSpacing: '0.1px',
                            }}
                          >
                            {flightDetails}
                          </Text>
                        </Box>
                      </Group>
                    </Card>
                    <Card
                      radius={18}
                      padding={17}
                      style={{
                        flex: isSmUp ? 1 : undefined,
                        minWidth: isSmUp ? 280 : undefined,
                        maxWidth: 341,
                        backgroundColor: 'rgba(255,255,255,0.5)',
                        border: `1.275px solid ${BASE_LIGHTER}`,
                      }}
                    >
                      <Group gap={18} align="center" wrap="nowrap">
                        <Box
                          style={{
                            width: 43.4,
                            height: 43.4,
                            borderRadius: 13,
                            backgroundColor: 'rgba(202,255,51,0.1)',
                            border: '1.275px solid rgba(202,255,51,0.1)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            flexShrink: 0,
                          }}
                        >
                          <HotelIcon size={24} color={TEXT_LIGHT} />
                        </Box>
                        <Box style={{ minWidth: 0, flex: 1 }}>
                          <Group justify="space-between" align="center" gap="xs">
                            <Text
                              style={{
                                fontFamily: LANDING_TOKENS.fontFamily.display,
                                fontSize: 16,
                                fontWeight: 600,
                                color: TEXT_LIGHT,
                              }}
                            >
                              {hotelName}
                            </Text>
                            <Text
                              style={{
                                fontFamily: LANDING_TOKENS.fontFamily.display,
                                fontSize: 16,
                                fontWeight: 600,
                                color: HIGHLIGHT_GREEN,
                              }}
                            >
                              {hotelPrice}
                            </Text>
                          </Group>
                          <Text
                            style={{
                              fontFamily: LANDING_TOKENS.fontFamily.display,
                              fontSize: 14,
                              fontWeight: 600,
                              color: LANDING_TOKENS.textSecondary,
                              letterSpacing: '0.1px',
                            }}
                          >
                            {hotelDetails}
                          </Text>
                        </Box>
                      </Group>
                    </Card>
                  </Stack>
                </Stack>

                <Stack
                  gap={11}
                  style={{
                    width: isLgUp ? 264 : '100%',
                    flexShrink: 0,
                    justifyContent: 'flex-end',
                    paddingTop: 16,
                    paddingBottom: 16,
                  }}
                >
                  {actionItems.map((item) => (
                    <Group key={item.id} align="center" px="md" style={{ minHeight: 48 }} wrap="nowrap">
                      <Box style={{ marginRight: 16, display: 'flex', alignItems: 'center' }}>
                        {item.completed ? (
                          <CheckCircle size={24} color={TEXT_LIGHT} />
                        ) : (
                          <History size={24} color={TEXT_LIGHT} />
                        )}
                      </Box>
                      <Text
                        style={{
                          fontFamily: LANDING_TOKENS.fontFamily.display,
                          fontSize: 16,
                          fontWeight: 600,
                          lineHeight: '20px',
                          color: TEXT_LIGHT,
                        }}
                      >
                        {item.label}
                        {item.linkText && (
                          <Box component="span" style={{ textDecoration: 'underline' }}>
                            {item.linkText}
                          </Box>
                        )}
                      </Text>
                    </Group>
                  ))}
                  <Stack gap="xs" align="flex-end" pt="md">
                    <Button
                      radius={100}
                      tt="none"
                      fw={600}
                      style={{
                        backgroundColor: BASE_COLOR,
                        color: TEXT_LIGHT,
                        fontSize: 14,
                      }}
                    >
                      {resumeLabel}
                    </Button>
                    <Button
                      variant="outline"
                      radius={100}
                      tt="none"
                      fw={600}
                      style={{
                        borderColor: BASE_LIGHTER,
                        color: '#c0c6f4',
                        fontSize: 14,
                      }}
                    >
                      {discardLabel}
                    </Button>
                  </Stack>
                </Stack>
              </Box>
            </Box>
          </Stack>
        </Accordion.Panel>
      </Accordion.Item>
    </Accordion>
  );
}

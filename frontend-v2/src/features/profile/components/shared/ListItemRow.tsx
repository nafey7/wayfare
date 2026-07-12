import { Box, Group, Text } from '@mantine/core';
import { LANDING_TOKENS } from '@/features/landing/landingTokens';

/** List item row — icon + text. Figma: min-h-[48px], leading 24px icon, text py-[10px] */
export function ListItemRow({
  icon,
  text,
}: {
  icon: React.ReactNode;
  text: string;
}) {
  return (
    <Group align="center" gap={0} style={{ minHeight: 48 }} wrap="nowrap">
      <Box
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-end',
          width: 56,
          height: 48,
          flexShrink: 0,
          paddingLeft: 16,
          paddingRight: 16,
        }}
      >
        {icon}
      </Box>
      <Text
        component="span"
        style={{
          flex: 1,
          paddingTop: 10,
          paddingBottom: 10,
          paddingLeft: 0,
          margin: 0,
          fontFamily: LANDING_TOKENS.fontFamily.display,
          fontWeight: 600,
          fontSize: 16,
          lineHeight: '20px',
          color: LANDING_TOKENS.textColor,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          display: 'block',
        }}
      >
        {text}
      </Text>
    </Group>
  );
}

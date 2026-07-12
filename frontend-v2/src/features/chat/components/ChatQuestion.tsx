import { Avatar, Box, Group, Stack } from '@mantine/core';
import { ChatChip, type ChatChipVariant } from './ChatChip';
import voyaAvatar from '@/assets/images/voya.jpeg';
import './chat.css';

export interface ChatSuggestionItem {
  /** Unique id. Used to identify which chip was selected. */
  id: string;
  label: string;
  /** Override variant — e.g. `signIn` for the guest sign-in chip. */
  variant?: Exclude<ChatChipVariant, 'selected'>;
}

export interface ChatQuestionProps {
  /** Voya's question. If `typing` is true, dots show instead. */
  message: string;
  /** Show typing dots; ignored if suggestions are rendered as answered. */
  typing?: boolean;
  /** Suggestion chips. When `answeredWith` is set, only the matching chip renders as selected. */
  suggestions?: ChatSuggestionItem[];
  /** Id of the chip the user picked. When set, only that chip is rendered (`selected` variant). */
  answeredWith?: string;
  onSelect?: (id: string, item: ChatSuggestionItem) => void;
}

function TypingDots() {
  const dot = {
    width: 6,
    height: 6,
    borderRadius: '50%',
    background: 'var(--mantine-color-navy-3)',
    display: 'inline-block',
  } as const;
  return (
    <Group gap={3} align="center" style={{ minHeight: 20 }}>
      <span style={{ ...dot, animation: 'voyaBlink 1.4s infinite 0s' }} />
      <span style={{ ...dot, animation: 'voyaBlink 1.4s infinite 0.2s' }} />
      <span style={{ ...dot, animation: 'voyaBlink 1.4s infinite 0.4s' }} />
    </Group>
  );
}

/**
 * Renders one turn in the chat welcome flow:
 *   [Voya avatar] [bubble with message or typing dots]
 *   [chip row, right-aligned]  ← active chips OR the single selected chip
 *
 * Behaviour:
 *   - typing=true → bubble shows dots, no chips
 *   - answeredWith set → chips collapse to the selected one (dashed + muted)
 *   - otherwise → all suggestions render as active; tapping fires onSelect
 */
export function ChatQuestion({
  message,
  typing,
  suggestions,
  answeredWith,
  onSelect,
}: ChatQuestionProps) {
  const bubble = (
    <Box
      style={{
        background: 'var(--mantine-color-navy-0)',
        color: 'var(--mantine-color-navy-7)',
        padding: '10px 14px',
        borderRadius: '12px 12px 12px 2px',
        maxWidth: 280,
        fontSize: 15,
        lineHeight: 1.4,
      }}
    >
      {typing ? <TypingDots /> : message}
    </Box>
  );

  const selectedItem =
    answeredWith && suggestions
      ? suggestions.find((s) => s.id === answeredWith)
      : undefined;

  const renderChips = () => {
    if (!suggestions || suggestions.length === 0) return null;

    if (selectedItem) {
      return (
        <Group gap={6} justify="flex-end" wrap="wrap" mt={8}>
          <ChatChip label={selectedItem.label} variant="selected" />
        </Group>
      );
    }

    return (
      <Group gap={6} justify="flex-end" wrap="wrap" mt={8}>
        {suggestions.map((s) => (
          <ChatChip
            key={s.id}
            label={s.label}
            variant={s.variant ?? 'active'}
            onClick={() => onSelect?.(s.id, s)}
          />
        ))}
      </Group>
    );
  };

  return (
    <Stack gap={4}>
      <Group gap={10} align="flex-end" wrap="nowrap">
        <Avatar
          src={voyaAvatar}
          size={32}
          radius="50%"
          alt="Voya"
          style={{
            border: '2px solid var(--mantine-color-brand-1)',
            flexShrink: 0,
          }}
        />
        {bubble}
      </Group>
      {!typing && renderChips()}
    </Stack>
  );
}

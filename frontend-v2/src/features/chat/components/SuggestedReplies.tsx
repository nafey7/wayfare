import { Group, Button } from '@mantine/core';
import { AnimatePresence, motion } from 'framer-motion';
import type { ChatSuggestion } from '@/types/chat';

interface SuggestedRepliesProps {
  suggestions: ChatSuggestion[];
  onSelect: (suggestion: ChatSuggestion) => void;
  /** When the parent already applies horizontal padding (e.g. ChatPanel), omit default px */
  omitHorizontalPadding?: boolean;
}

/**
 * Anchored suggestion chips that sit directly above the chat input.
 * Visible only when the latest bot message carries suggestions and the
 * user hasn't dismissed them (by clicking one or typing).
 */
export function SuggestedReplies({
  suggestions,
  onSelect,
  omitHorizontalPadding = false,
}: SuggestedRepliesProps) {
  return (
    <AnimatePresence mode="wait">
      {suggestions.length > 0 && (
        <motion.div
          key="suggestions"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 4 }}
          transition={{ type: 'spring', stiffness: 300, damping: 24 }}
        >
          <Group
            justify="flex-end"
            gap={6}
            pb={8}
            px={omitHorizontalPadding ? 0 : 16}
            wrap="wrap"
          >
            {suggestions.map((item) => (
              <Button
                key={item.command}
                size="sm"
                radius="xl"
                onClick={() => onSelect(item)}
                styles={{
                  root: {
                    background: 'transparent',
                    border: '1px solid var(--mantine-color-navy-1)',
                    color: 'var(--mantine-color-navy-5)',
                    fontWeight: 500,
                  },
                }}
              >
                {item.title}
              </Button>
            ))}
          </Group>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

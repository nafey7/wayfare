import { useCallback, useRef, useEffect } from 'react';
import { Box, Paper, Textarea, ActionIcon, Text, Group } from '@mantine/core';
import { SendHorizonal } from 'lucide-react';
import { motion } from 'framer-motion';

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: (message: string) => void;
  disabled?: boolean;
  loading?: boolean;
  placeholder?: string;
  disclaimerText?: string;
}

export function ChatInput({
  value,
  onChange,
  onSend,
  disabled = false,
  loading = false,
  placeholder = 'Type your message...',
  disclaimerText = 'AI responses may contain errors. Please verify important information.',
}: ChatInputProps) {
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const shouldRefocusRef = useRef(false);

  const isButtonDisabled = loading || disabled || !value.trim();

  useEffect(() => {
    if (!loading && shouldRefocusRef.current) {
      shouldRefocusRef.current = false;
      setTimeout(() => {
        inputRef.current?.focus();
      }, 50);
    }
  }, [loading]);

  const handleSend = useCallback(() => {
    if (value.trim() && !disabled && !loading) {
      shouldRefocusRef.current = true;
      onSend(value.trim());
    }
  }, [value, disabled, loading, onSend]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey && !isButtonDisabled) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend, isButtonDisabled]
  );

  return (
    <Box px={24} pb={16} pt={8}>
      <Paper
        component="form"
        radius="lg"
        withBorder
        style={{ overflow: 'hidden' }}
        onSubmit={(e: React.FormEvent) => {
          e.preventDefault();
          handleSend();
        }}
      >
        <Group gap={8} align="flex-end" px={16} py={10}>
          <Textarea
            ref={inputRef}
            autosize
            minRows={1}
            maxRows={4}
            placeholder={placeholder}
            value={value}
            onChange={(e) => onChange(e.currentTarget.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            autoFocus
            variant="unstyled"
            style={{ flex: 1 }}
            styles={{
              input: {
                fontSize: '0.95rem',
                padding: '2px 0',
                resize: 'none',
                lineHeight: 1.5,
              },
            }}
          />
          <motion.div
            whileHover={isButtonDisabled ? {} : { scale: 1.08 }}
            whileTap={isButtonDisabled ? {} : { scale: 0.92 }}
          >
            <ActionIcon
              color="navy"
              size={36}
              radius="xl"
              onClick={handleSend}
              disabled={isButtonDisabled}
              variant={value.trim() ? 'filled' : 'subtle'}
              aria-label="Send message"
              mb={2}
            >
              <SendHorizonal size={16} />
            </ActionIcon>
          </motion.div>
        </Group>
      </Paper>
      <Text size="xs" c="dimmed" ta="center" mt={8}>
        {disclaimerText}
      </Text>
    </Box>
  );
}

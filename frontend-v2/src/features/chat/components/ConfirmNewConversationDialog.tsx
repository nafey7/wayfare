import { Button, Group, Modal, Stack, Text } from '@mantine/core';

import { NAV_NAVY, NAV_SLATE } from '@/theme/navTokens';

export interface ConfirmNewConversationDialogProps {
  open: boolean;
  onClose: () => void;
  onSaveChat: () => void;
  onProceed: () => void;
}

/**
 * Guest-only confirmation shown when the user attempts to start a new
 * conversation while an active guest chat session already exists. Offers
 * "Save chat" (opens auth modal so the existing claim flow can attach the
 * chat to the new account) or "Proceed anyway" (discards the current
 * guest chat and any persisted guest itinerary).
 */
export function ConfirmNewConversationDialog({
  open,
  onClose,
  onSaveChat,
  onProceed,
}: ConfirmNewConversationDialogProps) {
  return (
    <Modal
      opened={open}
      onClose={onClose}
      withCloseButton={false}
      centered
      radius="md"
      size="sm"
      padding={0}
      shadow="md"
      aria-labelledby="confirm-new-conversation-title"
    >
      <Stack gap={12} p={20}>
        <Text
          id="confirm-new-conversation-title"
          style={{
            fontSize: 16,
            fontWeight: 700,
            color: NAV_NAVY,
            fontFamily: 'inherit',
          }}
        >
          Start a new conversation?
        </Text>
        <Text
          style={{
            fontSize: 13,
            lineHeight: 1.5,
            color: NAV_SLATE,
            fontFamily: 'inherit',
          }}
        >
          You have an unsaved chat. Save it to your account, or start fresh —
          your current chat and any saved trip will be discarded.
        </Text>

        <Group justify="flex-end" gap="xs" mt={4}>
          <Button
            variant="subtle"
            size="xs"
            onClick={onProceed}
            tt="none"
            fw={500}
            color="dark.8"
          >
            Proceed anyway
          </Button>
          <Button
            size="xs"
            radius="xl"
            style={{ backgroundColor: NAV_NAVY, color: 'white' }}
            onClick={onSaveChat}
            tt="none"
            fw={600}
            px="lg"
          >
            Save chat
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

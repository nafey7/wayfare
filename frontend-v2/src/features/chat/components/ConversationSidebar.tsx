import { useState, useMemo, useCallback } from 'react';
import {
  ActionIcon,
  Box,
  Button,
  Divider,
  Menu,
  Modal,
  Stack,
  Text,
  TextInput,
  UnstyledButton,
} from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { Plus, MoreVertical, Pencil, Trash2, PanelLeftClose } from 'lucide-react';

import type { ConversationMeta } from '@/types/chat';

// ---------------------------------------------------------------------------
// Date grouping
// ---------------------------------------------------------------------------

type DateGroup = 'Today' | 'Yesterday' | 'Previous 7 days' | 'Previous 30 days' | 'Older';

function getDateGroup(dateStr: string | null): DateGroup {
  if (!dateStr) return 'Older';
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / 86_400_000);
  if (diffDays <= 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays <= 7) return 'Previous 7 days';
  if (diffDays <= 30) return 'Previous 30 days';
  return 'Older';
}

const DATE_GROUP_ORDER: DateGroup[] = [
  'Today',
  'Yesterday',
  'Previous 7 days',
  'Previous 30 days',
  'Older',
];

function groupConversations(
  conversations: ConversationMeta[]
): Map<DateGroup, ConversationMeta[]> {
  const groups = new Map<DateGroup, ConversationMeta[]>();
  for (const conv of conversations) {
    const group = getDateGroup(conv.last_message_at ?? conv.created_at);
    const arr = groups.get(group) ?? [];
    arr.push(conv);
    groups.set(group, arr);
  }
  return groups;
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface ConversationSidebarProps {
  conversations: ConversationMeta[];
  activeChatId: string | null;
  onSelect: (chatId: string) => void;
  onNewChat: () => void;
  onRename: (chatId: string, name: string) => void;
  onDelete: (chatId: string) => void;
  onClose?: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ConversationSidebar({
  conversations = [],
  activeChatId,
  onSelect,
  onNewChat,
  onRename,
  onDelete,
  onClose,
}: ConversationSidebarProps) {
  // Mantine breakpoint matches MUI's `md` (≤900px).
  const isMobile = useMediaQuery('(max-width: 900px)') ?? false;

  // Rename dialog state
  const [renameDialogOpen, setRenameDialogOpen] = useState(false);
  const [renameValue, setRenameValue] = useState('');
  const [renameChatId, setRenameChatId] = useState<string | null>(null);

  // Delete dialog state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteChatId, setDeleteChatId] = useState<string | null>(null);

  const grouped = useMemo(() => groupConversations(conversations), [conversations]);

  const handleRenameClick = useCallback(
    (chatId: string) => {
      const conv = conversations.find((c) => c.chat_id === chatId);
      setRenameChatId(chatId);
      setRenameValue(conv?.name ?? '');
      setRenameDialogOpen(true);
    },
    [conversations]
  );

  const handleDeleteClick = useCallback((chatId: string) => {
    setDeleteChatId(chatId);
    setDeleteDialogOpen(true);
  }, []);

  // --- Rename dialog ---
  const handleRenameConfirm = useCallback(() => {
    if (renameChatId && renameValue.trim()) {
      onRename(renameChatId, renameValue.trim());
    }
    setRenameDialogOpen(false);
    setRenameChatId(null);
    setRenameValue('');
  }, [renameChatId, renameValue, onRename]);

  // --- Delete dialog ---
  const handleDeleteConfirm = useCallback(() => {
    if (deleteChatId) {
      onDelete(deleteChatId);
    }
    setDeleteDialogOpen(false);
    setDeleteChatId(null);
  }, [deleteChatId, onDelete]);

  const handleSelect = useCallback(
    (chatId: string) => {
      onSelect(chatId);
      if (isMobile) onClose?.();
    },
    [onSelect, isMobile, onClose]
  );

  const handleNewChat = useCallback(() => {
    onNewChat();
    if (isMobile) onClose?.();
  }, [onNewChat, isMobile, onClose]);

  return (
    <Stack
      gap={0}
      style={{
        height: '100%',
        backgroundColor: 'var(--mantine-color-gray-0)',
        borderRight: '1px solid var(--mantine-color-default-border)',
      }}
    >
      {/* Header */}
      <Box
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          paddingInline: 16,
          paddingBlock: 12,
          borderBottom: '1px solid var(--mantine-color-default-border)',
        }}
      >
        <Button
          size="xs"
          radius="md"
          fw={600}
          leftSection={<Plus size={16} />}
          onClick={handleNewChat}
        >
          New chat
        </Button>
        {onClose && (
          <ActionIcon
            variant="subtle"
            color="dark"
            size="md"
            onClick={onClose}
            aria-label="Close sidebar"
          >
            <PanelLeftClose size={18} />
          </ActionIcon>
        )}
      </Box>

      {/* Conversation list */}
      <Box style={{ flex: 1, overflow: 'auto', paddingBlock: 4 }}>
        {conversations.length === 0 ? (
          <Text c="dimmed" size="sm" ta="center" mt="xl" px="md">
            No conversations yet. Start a new chat!
          </Text>
        ) : (
          <Stack gap={0}>
            {DATE_GROUP_ORDER.map((group) => {
              const items = grouped.get(group);
              if (!items || items.length === 0) return null;
              return (
                <Box key={group}>
                  <Text
                    component="div"
                    c="dimmed"
                    fw={700}
                    style={{
                      paddingInline: 16,
                      paddingTop: 12,
                      paddingBottom: 4,
                      fontSize: '0.68rem',
                      letterSpacing: '0.08em',
                      textTransform: 'uppercase',
                    }}
                  >
                    {group}
                  </Text>
                  {items.map((conv) => {
                    const isActive = conv.chat_id === activeChatId;
                    return (
                      <Box
                        key={conv.chat_id}
                        className="voya-conv-row"
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          marginInline: 8,
                          borderRadius: 6,
                          backgroundColor: isActive
                            ? 'var(--mantine-color-blue-1)'
                            : 'transparent',
                        }}
                      >
                        <UnstyledButton
                          onClick={() => handleSelect(conv.chat_id)}
                          style={{
                            flex: 1,
                            paddingInline: 12,
                            paddingBlock: 6,
                            minWidth: 0,
                          }}
                        >
                          <Text
                            size="sm"
                            fw={isActive ? 600 : 400}
                            truncate
                          >
                            {conv.name}
                          </Text>
                        </UnstyledButton>
                        <Menu position="bottom-end" withinPortal>
                          <Menu.Target>
                            <ActionIcon
                              variant="subtle"
                              color="gray"
                              size="sm"
                              className="voya-conv-row-menu"
                              onClick={(e) => e.stopPropagation()}
                              aria-label="Conversation options"
                              style={{
                                opacity: 0,
                                transition: 'opacity 0.15s',
                                marginRight: 4,
                              }}
                            >
                              <MoreVertical size={16} />
                            </ActionIcon>
                          </Menu.Target>
                          <Menu.Dropdown>
                            <Menu.Item
                              leftSection={<Pencil size={14} />}
                              onClick={() => handleRenameClick(conv.chat_id)}
                            >
                              Rename
                            </Menu.Item>
                            <Divider />
                            <Menu.Item
                              color="red"
                              leftSection={<Trash2 size={14} />}
                              onClick={() => handleDeleteClick(conv.chat_id)}
                            >
                              Delete
                            </Menu.Item>
                          </Menu.Dropdown>
                        </Menu>
                      </Box>
                    );
                  })}
                </Box>
              );
            })}
          </Stack>
        )}
      </Box>

      {/* Reveal the row's options button on row hover. Placed alongside the
         conversation list because Mantine has no `:has`-style row-hover sx
         shortcut equivalent to the MUI `.MuiListItem-root:hover &` pattern. */}
      <style>{`
        .voya-conv-row:hover .voya-conv-row-menu,
        .voya-conv-row:focus-within .voya-conv-row-menu {
          opacity: 1;
        }
      `}</style>

      {/* Rename dialog */}
      <Modal
        opened={renameDialogOpen}
        onClose={() => setRenameDialogOpen(false)}
        title="Rename conversation"
        size="xs"
        centered
      >
        <Stack gap="md">
          <TextInput
            data-autofocus
            value={renameValue}
            onChange={(e) => setRenameValue(e.currentTarget.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleRenameConfirm();
            }}
            maxLength={50}
            size="sm"
          />
          <Box
            style={{
              display: 'flex',
              justifyContent: 'flex-end',
              gap: 8,
            }}
          >
            <Button variant="subtle" onClick={() => setRenameDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleRenameConfirm} disabled={!renameValue.trim()}>
              Rename
            </Button>
          </Box>
        </Stack>
      </Modal>

      {/* Delete dialog */}
      <Modal
        opened={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
        title="Delete conversation"
        size="xs"
        centered
      >
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            Delete this conversation? You won&apos;t be able to see it again.
          </Text>
          <Box
            style={{
              display: 'flex',
              justifyContent: 'flex-end',
              gap: 8,
            }}
          >
            <Button variant="subtle" onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button color="red" onClick={handleDeleteConfirm}>
              Delete
            </Button>
          </Box>
        </Stack>
      </Modal>
    </Stack>
  );
}

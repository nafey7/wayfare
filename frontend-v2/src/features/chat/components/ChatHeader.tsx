import { useState } from 'react';
import { Avatar, Box, Badge, ActionIcon, Menu, Switch, Divider, Tooltip, Group } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { X, Maximize2, Minimize2, MoreVertical, Trash2, Volume2, VolumeX, ArrowDownToLine } from 'lucide-react';
import logoLight from '@/assets/images/logo-light2.png';
import { chatConfig } from '../styles/chatTheme';
import { zIndex } from '@/theme';

interface ChatHeaderProps {
  onClose: () => void;
  onClearChat: () => void;
  soundEnabled: boolean;
  onToggleSound: () => void;
  autoScroll: boolean;
  onToggleAutoScroll: () => void;
  isFullScreen: boolean;
  onToggleFullScreen: () => void;
  showCloseButton?: boolean;
  showFullScreenButton?: boolean;
}

export function ChatHeader({
  onClose,
  onClearChat,
  soundEnabled,
  onToggleSound,
  autoScroll,
  onToggleAutoScroll,
  isFullScreen,
  onToggleFullScreen,
  showCloseButton = true,
  showFullScreenButton = true,
}: ChatHeaderProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const isMobile = useMediaQuery('(max-width: 600px)');

  return (
    <Box
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingInline: 16,
        paddingBlock: 12,
        backgroundColor: 'var(--mantine-color-brand-8)',
        color: 'white',
        position: 'relative',
      }}
    >
      {/* Left: Avatar + Logo + Alpha badge */}
      <Group gap={8} align="center">
        <Avatar src={chatConfig.avatars.bot} size={32} />
        <Box
          component="img"
          src={logoLight}
          style={{ width: 'auto', height: 30, cursor: 'pointer' }}
          alt="Voya Logo"
        />
        <Badge
          size="xs"
          styles={{
            root: {
              backgroundColor: 'rgba(255, 255, 255, 0.2)',
              color: 'white',
              border: 'none',
              textTransform: 'none',
            },
          }}
        >
          Alpha
        </Badge>
      </Group>

      {/* Right: Fullscreen, Menu, Close */}
      <Group gap={4}>
        {!isMobile && showFullScreenButton && (
          <Tooltip label={isFullScreen ? 'Exit Fullscreen' : 'Fullscreen'}>
            <ActionIcon
              size="sm"
              variant="transparent"
              aria-label={isFullScreen ? 'Exit fullscreen' : 'Enter fullscreen'}
              onClick={onToggleFullScreen}
              style={{ color: 'white' }}
            >
              {isFullScreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
            </ActionIcon>
          </Tooltip>
        )}

        <Menu
          opened={menuOpen}
          onChange={setMenuOpen}
          closeOnItemClick={false}
          position="bottom-end"
        >
          <Menu.Target>
            <ActionIcon
              size="sm"
              variant="transparent"
              aria-label="Chat options"
              style={{ color: 'white' }}
            >
              <MoreVertical size={16} />
            </ActionIcon>
          </Menu.Target>
          <Menu.Dropdown style={{ zIndex: zIndex.detailModal + 1 }}>
            <Menu.Item
              leftSection={soundEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
              rightSection={<Switch checked={soundEnabled} size="xs" readOnly tabIndex={-1} />}
              onClick={onToggleSound}
            >
              Sound
            </Menu.Item>
            <Menu.Item
              leftSection={<ArrowDownToLine size={16} />}
              rightSection={<Switch checked={autoScroll} size="xs" readOnly tabIndex={-1} />}
              onClick={onToggleAutoScroll}
            >
              Auto-scroll
            </Menu.Item>
            <Divider />
            <Menu.Item
              color="red"
              leftSection={<Trash2 size={16} />}
              onClick={() => {
                setMenuOpen(false);
                onClearChat();
              }}
            >
              Clear chat
            </Menu.Item>
          </Menu.Dropdown>
        </Menu>

        {showCloseButton && (
          <ActionIcon
            size="sm"
            variant="transparent"
            aria-label="Close chat"
            onClick={onClose}
            style={{ color: 'white' }}
          >
            <X size={16} />
          </ActionIcon>
        )}
      </Group>
    </Box>
  );
}

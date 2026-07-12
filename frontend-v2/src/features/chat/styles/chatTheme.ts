import voyaAvatar from '@/assets/images/voya.jpeg';

/**
 * Chat-domain non-theme constants.
 *
 * The legacy `chatBotTheme` (MUI `createTheme`) was dropped in the M3
 * Mantine migration; the chat surface now inherits from the app-level
 * MantineProvider. Only colour and avatar/animation constants remain.
 */

// Chat message colors (used inline in ChatMessage / bubble components)
export const chatColors = {
  botMessage: '#CCCBFCC2',
  userMessage: '#E7FBBC',
};

// Chat config — bot avatar + framer-motion spring animation defaults
export const chatConfig = {
  avatars: {
    bot: voyaAvatar,
  },
  animation: {
    spring: {
      type: 'spring' as const,
      stiffness: 300,
      damping: 30,
    },
  },
};

import { useCallback } from 'react';
import { useAppSelector } from '@/store';
import { selectSoundEnabled } from '@/store/slices/uiSlice';

interface UseChatSoundReturn {
  playMessageSound: () => void;
  playNotificationSound: () => void;
}

/**
 * Hook to manage chat sound effects
 *
 * @returns Functions to play sounds
 */
export function useChatSound(): UseChatSoundReturn {
  const soundEnabled = useAppSelector(selectSoundEnabled);

  const playSound = useCallback(
    (soundPath: string) => {
      if (!soundEnabled) return;

      try {
        const audio = new Audio(soundPath);
        audio.volume = 0.5;
        audio.play().catch(() => {
          // Ignore autoplay errors
        });
      } catch {
        // Ignore audio errors
      }
    },
    [soundEnabled]
  );

  const playMessageSound = useCallback(() => {
    playSound('/assets/sounds/message.mp3');
  }, [playSound]);

  const playNotificationSound = useCallback(() => {
    playSound('/assets/sounds/notification.mp3');
  }, [playSound]);

  return {
    playMessageSound,
    playNotificationSound,
  };
}

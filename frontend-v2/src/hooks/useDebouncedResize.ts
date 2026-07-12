import { useState, useEffect } from 'react';
import { useDebounce } from './useDebounce';

interface WindowSize {
  width: number;
  height: number;
}

/**
 * Track window size with debouncing
 *
 * @param delay - Debounce delay in milliseconds (default: 100)
 * @returns Current window dimensions
 *
 * @example
 * ```tsx
 * const { width, height } = useDebouncedResize(200);
 * const isMobile = width < 768;
 * ```
 */
export function useDebouncedResize(delay = 100): WindowSize {
  const [windowSize, setWindowSize] = useState<WindowSize>({
    width: typeof window !== 'undefined' ? window.innerWidth : 0,
    height: typeof window !== 'undefined' ? window.innerHeight : 0,
  });

  useEffect(() => {
    const handleResize = () => {
      setWindowSize({
        width: window.innerWidth,
        height: window.innerHeight,
      });
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const debouncedWidth = useDebounce(windowSize.width, delay);
  const debouncedHeight = useDebounce(windowSize.height, delay);

  return {
    width: debouncedWidth,
    height: debouncedHeight,
  };
}

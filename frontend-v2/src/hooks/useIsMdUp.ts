import { useMediaQuery } from '@mantine/hooks';

/** True when viewport is `md` breakpoint or wider — single source of truth for "desktop inline panel vs mobile chat-inline" layout decisions. */
export function useIsMdUp(): boolean {
  return useMediaQuery('(min-width: 900px)') ?? false;
}

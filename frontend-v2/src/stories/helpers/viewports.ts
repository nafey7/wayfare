/** Phone viewport for mobile Storybook stories.
 *
 *  375 px is the iPhone SE width — the lower bound for mainstream phone screens
 *  and the project's standard mobile reference. MUI's `md` breakpoint is 900 px,
 *  so any viewport below that causes `useIsMdUp()` to return `false` and the
 *  mobile branch of chat rich-result components to render.
 *
 *  In Storybook v10 viewport is built into core (`storybook/viewport`); the
 *  parameter shape uses `options` (v10) but `viewports` (v8) is still read by
 *  `@storybook/addon-vitest` for backward-compat. `defaultViewport` is the
 *  per-story default (vitest browser also reads `globals.viewport.value`).
 *
 *  Usage in a story:
 *
 *  ```ts
 *  import { PHONE_VIEWPORT } from '@/stories/helpers/viewports';
 *
 *  export const Mobile: Story = {
 *    parameters: { viewport: PHONE_VIEWPORT },
 *    args: { ... },
 *  };
 *  ```
 */
export const PHONE_VIEWPORT = {
  options: {
    mobile375: {
      name: 'iPhone SE / Mobile (375 px)',
      styles: { width: '375px', height: '812px' },
      type: 'mobile' as const,
    },
  },
  defaultViewport: 'mobile375',
};

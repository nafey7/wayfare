/**
 * Thin re-export shim — preserves existing import paths (`import { theme } from '@/theme'`
 * and the relative `'../src/theme.ts'` used by some older story/test files).
 *
 * All real theme logic lives in `src/theme/`. Once all callers migrate to `@/theme`,
 * this file can be deleted (tracked in issue #707).
 */
export * from './theme/index';

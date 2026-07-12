/**
 * Logs to console only when VITE_ENV is not "production".
 * Use for debugging (e.g. rateBasisId, state) without polluting production.
 */
export function devLog(message: string, ...args: unknown[]): void {
  if (import.meta.env.VITE_ENV !== 'production') {
    console.log(`[dev] ${message}`, ...args);
  }
}

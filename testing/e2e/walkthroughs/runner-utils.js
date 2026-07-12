// Shared utilities for walkthrough runner scripts.

/**
 * Parse `--key=value` style CLI flags into an object. Unknown forms are
 * silently ignored — the runner is responsible for validating the keys.
 *
 * @param {string[]} argv — typically `process.argv.slice(2)`
 * @returns {Record<string, string>}
 */
export function parseArgs(argv) {
  const out = {};
  for (const arg of argv) {
    const m = arg.match(/^--([^=]+)=(.*)$/);
    if (m) out[m[1]] = m[2];
  }
  return out;
}

/**
 * Validate the staging-walkthrough environment. Exits the process with code 1
 * (and a clear error message) if TEST_ENV !== 'staging', or if `creds` is
 * true and STAGING_TEST_USER_EMAIL / _PASSWORD are missing.
 *
 * Walkthrough runners share the same prerequisites; this consolidates the
 * guard blocks that were previously duplicated.
 *
 * @param {string} runnerName — for the error message hint (e.g.
 *   `'e2e/walkthroughs/run-itinerary.js'`)
 * @param {object} [options]
 * @param {boolean} [options.creds] — also require staging test-user creds.
 *   Default true. Pass false for guest/public walkthroughs that don't login.
 */
export function ensureStagingEnv(runnerName, { creds = true } = {}) {
  if (creds && (!process.env.STAGING_TEST_USER_EMAIL || !process.env.STAGING_TEST_USER_PASSWORD)) {
    console.error(
      'STAGING_TEST_USER_EMAIL / STAGING_TEST_USER_PASSWORD missing.\n' +
        'Run: source .local/test-credentials/staging-test-user.env',
    );
    process.exit(1);
  }
  if (process.env.TEST_ENV !== 'staging') {
    console.error(
      `TEST_ENV must be "staging" (got: ${JSON.stringify(process.env.TEST_ENV)}).\n` +
        `Run: TEST_ENV=staging node ${runnerName} [...args]`,
    );
    process.exit(1);
  }
}

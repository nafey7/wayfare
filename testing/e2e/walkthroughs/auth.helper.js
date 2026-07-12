// Reusable login helper for walkthroughs.
//
// Wraps the AuthModalPage Page Object so walkthroughs don't re-derive the auth
// modal selectors. Reads STAGING_TEST_USER_EMAIL / STAGING_TEST_USER_PASSWORD
// from env (sourced from .local/test-credentials/staging-test-user.env locally,
// or injected by GitHub Actions in CI).
//
// Walked manually 2026-05-02 against staging — confirms login lands on /home or /chat
// per AuthModalPage.expectPostLoginRedirect.

import { AuthModalPage } from '../pages/AuthModalPage.js';

/**
 * Walks the email-step → password-step happy path on the auth modal.
 *
 * Side-effects: dispatches the `user_login` GTM event when successful.
 *
 * @param {import('@playwright/test').Page} page
 * @param {object} [options]
 * @param {(event: string, ctx: { page: import('@playwright/test').Page }) => Promise<void>} [options.onStep]
 *   Called after each user-visible state transition. Step names are GTM
 *   `dataLayer` event names where one fires (`user_login`), or synthetic
 *   prefixed names (`__opened_auth_modal`, `__submitted_email`).
 * @returns {Promise<{ url: string, events: string[] }>}
 */
export async function loginAsStagingTestUser(page, options = {}) {
  const { onStep = noop } = options;

  const email = required('STAGING_TEST_USER_EMAIL');
  const password = required('STAGING_TEST_USER_PASSWORD');

  const auth = new AuthModalPage(page);
  const events = [];

  await auth.open();
  await runStep(events, onStep, '__opened_auth_modal', { page });

  const checkEmailResponse = await auth.submitEmail(email);
  if (checkEmailResponse.status() !== 200) {
    throw new Error(
      `Auth modal email step expected 200, got ${checkEmailResponse.status()}. Account ${email} may not exist on staging.`,
    );
  }
  await auth.expectLoginStep(email);
  await runStep(events, onStep, '__submitted_email', { page });

  const loginResponse = await auth.submitLoginPassword(password);
  if (loginResponse.status() !== 200) {
    throw new Error(
      `Auth modal login step expected 200, got ${loginResponse.status()}. Password may be wrong.`,
    );
  }

  await auth.expectDialogClosed();
  await auth.expectPostLoginRedirect();
  await runStep(events, onStep, 'user_login', { page });

  return { url: page.url(), events };
}

function required(name) {
  const value = process.env[name];
  if (!value) {
    throw new Error(
      `Missing env var ${name}. Source .local/test-credentials/staging-test-user.env or export manually.`,
    );
  }
  return value;
}

async function runStep(events, onStep, eventName, ctx) {
  events.push(eventName);
  await onStep(eventName, ctx);
}

function noop() {}

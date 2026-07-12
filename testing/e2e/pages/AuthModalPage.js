// Page Object for the Voya auth modal (`AuthModal.tsx`).
//
// Encodes every selector + flow primitive the auth specs rely on so specs
// don't re-derive them. The modal has three steps — `email`, `registration`
// (new user), `login` (existing verified user) — plus a post-registration
// confirmation state. Methods are grouped by step. See `testing/CLAUDE.md`
// for the general Page Object shape and conventions.
//
// Known UI quirks handled here (see testing/specs/auth.md Appendix B):
// - Email field is disabled in the registration + login steps (read-only carry-
//   over from step 1); asserting via `.inputValue()` works on disabled fields.
// - "Forgot your password?" is a `<Button>`, not an anchor, so we target
//   `getByRole('button', …)`.
// - `ProtectedRoute` redirects unauthenticated users to `/`, not `/login`.

import { expect } from '@playwright/test';
import { TIMEOUTS } from '../../utils/constants.js';
import { openAuthModal } from '../../helpers/auth-helpers.js';
import { navigateToApp } from '../../helpers/navigation-helpers.js';

export class AuthModalPage {
  /**
   * @param {import('@playwright/test').Page} page
   */
  constructor(page) {
    this.page = page;
  }

  // ---------------------------------------------------------------------------
  // Entry / container
  // ---------------------------------------------------------------------------

  /** Navigate to the app landing (does NOT open the modal). */
  async navigate() {
    await navigateToApp(this.page);
  }

  /**
   * Open the auth modal from whatever page the user is currently on.
   * Uses `helpers/auth-helpers.js::openAuthModal` which tries the main button
   * then falls back to the hamburger menu.
   */
  async openModal() {
    await openAuthModal(this.page);
    await expect(this.dialog).toBeVisible({ timeout: TIMEOUTS.MODAL_APPEAR });
  }

  /** Convenience: navigate + openModal in one call. */
  async open() {
    await this.navigate();
    await this.openModal();
  }

  /** Dialog container. All step content lives inside it. */
  get dialog() {
    return this.page.getByRole('dialog');
  }

  // ---------------------------------------------------------------------------
  // Email step — the modal opens here.
  // ---------------------------------------------------------------------------

  /** "Login" heading that identifies the email step. */
  get emailStepHeading() {
    return this.dialog.getByRole('heading', { name: 'Login' });
  }

  /** Email input — editable in this step, disabled in the next two. */
  get emailField() {
    return this.dialog.getByLabel('Email Address');
  }

  /**
   * Primary submit for the email step.
   *
   * `exact: true` is load-bearing: GoogleAuthButton renders a sibling
   * `role="button"` whose accessible name is "Continue with Google. Opens…",
   * which substring-matches "Continue". Without `exact`, strict-mode picks
   * up both buttons when Google's OAuth widget is enabled (staging always,
   * compose.test.yaml when the config flag is on).
   */
  get continueButton() {
    return this.dialog.getByRole('button', { name: 'Continue', exact: true });
  }

  /**
   * Fill the email and submit. Returns the POST /api/auth/check-email response
   * so the spec can assert status + body without re-wiring the race.
   * @param {string} email
   * @returns {Promise<import('@playwright/test').Response>}
   */
  async submitEmail(email) {
    await this.emailField.fill(email);
    const [response] = await Promise.all([
      this.page.waitForResponse(
        (r) => r.url().includes('/auth/check-email') && r.request().method() === 'POST',
        { timeout: TIMEOUTS.API_RESPONSE },
      ),
      this.continueButton.click(),
    ]);
    return response;
  }

  /** Assert we're on the email step (modal just opened, no submission yet). */
  async expectEmailStep() {
    await expect(this.dialog).toBeVisible({ timeout: TIMEOUTS.MODAL_APPEAR });
    await expect(this.emailStepHeading).toBeVisible({ timeout: TIMEOUTS.ELEMENT_VISIBLE });
    await expect(this.emailField).toBeVisible({ timeout: TIMEOUTS.ELEMENT_VISIBLE });
    await expect(this.continueButton).toBeVisible({ timeout: TIMEOUTS.ELEMENT_VISIBLE });
    await expect(this.continueButton).toBeEnabled();
  }

  // ---------------------------------------------------------------------------
  // Registration step — reached when check-email reports a new address.
  // ---------------------------------------------------------------------------

  get createAccountHeading() {
    return this.dialog.getByRole('heading', { name: 'Create Account' });
  }

  get firstNameField() {
    return this.dialog.getByLabel('First Name');
  }

  get lastNameField() {
    return this.dialog.getByLabel('Last Name');
  }

  get completeRegistrationButton() {
    return this.dialog.getByRole('button', { name: 'Complete Registration' });
  }

  /** Post-registration confirmation state. */
  get postRegistrationGotItButton() {
    return this.dialog.getByRole('button', { name: 'Got it' });
  }

  /** Success alert shown after the Complete Registration click. */
  get registrationSuccessAlert() {
    return this.dialog.getByRole('alert');
  }

  /**
   * Fill the Create Account form and submit. Returns the POST /api/auth/register
   * response.
   * @param {{firstName: string, lastName: string}} details
   */
  async submitRegistrationDetails({ firstName, lastName }) {
    await this.firstNameField.fill(firstName);
    await this.lastNameField.fill(lastName);
    const [response] = await Promise.all([
      this.page.waitForResponse(
        (r) => r.url().includes('/auth/register') && r.request().method() === 'POST',
        { timeout: TIMEOUTS.API_RESPONSE },
      ),
      this.completeRegistrationButton.click(),
    ]);
    return response;
  }

  /**
   * Assert the modal is on the registration step.
   * @param {string} [carriedEmail] — if provided, asserts the email field is
   *   disabled and carries this value (plan Appendix B #4).
   */
  async expectRegistrationStep(carriedEmail) {
    await expect(this.createAccountHeading).toBeVisible({ timeout: TIMEOUTS.MODAL_APPEAR });
    await expect(this.firstNameField).toBeVisible({ timeout: TIMEOUTS.ELEMENT_VISIBLE });
    await expect(this.lastNameField).toBeVisible({ timeout: TIMEOUTS.ELEMENT_VISIBLE });
    if (carriedEmail !== undefined) {
      await expect(this.emailField).toBeDisabled();
      await expect(this.emailField).toHaveValue(carriedEmail);
    }
  }

  // ---------------------------------------------------------------------------
  // Login step — reached when check-email reports a verified user.
  // ---------------------------------------------------------------------------

  get welcomeBackHeading() {
    return this.dialog.getByRole('heading', { name: 'Welcome Back' });
  }

  get passwordField() {
    return this.dialog.getByLabel('Password');
  }

  get signInButton() {
    return this.dialog.getByRole('button', { name: 'Sign In' });
  }

  /** "Forgot your password?" — rendered as a `<Button>`, not an anchor. */
  get forgotPasswordButton() {
    return this.dialog.getByRole('button', { name: /forgot your password/i });
  }

  /**
   * Fill the password and click Sign In. Returns the POST /api/auth/login response.
   * @param {string} password
   */
  async submitLoginPassword(password) {
    await this.passwordField.fill(password);
    const [response] = await Promise.all([
      this.page.waitForResponse(
        (r) => r.url().includes('/auth/login') && r.request().method() === 'POST',
        { timeout: TIMEOUTS.API_RESPONSE },
      ),
      this.signInButton.click(),
    ]);
    return response;
  }

  /**
   * Assert the modal is on the login step.
   * @param {string} [carriedEmail]
   */
  async expectLoginStep(carriedEmail) {
    await expect(this.welcomeBackHeading).toBeVisible({ timeout: TIMEOUTS.MODAL_APPEAR });
    await expect(this.passwordField).toBeVisible({ timeout: TIMEOUTS.ELEMENT_VISIBLE });
    await expect(this.forgotPasswordButton).toBeVisible();
    if (carriedEmail !== undefined) {
      await expect(this.emailField).toBeDisabled();
      await expect(this.emailField).toHaveValue(carriedEmail);
    }
  }

  // ---------------------------------------------------------------------------
  // Whole-modal assertions
  // ---------------------------------------------------------------------------

  /** Assert the dialog has been dismissed (e.g. after successful login). */
  async expectDialogClosed() {
    await expect(this.dialog).not.toBeVisible({ timeout: TIMEOUTS.MODAL_APPEAR });
  }

  /**
   * Assert the post-login URL landed on /home or /chat as a root-level route
   * (PublicRoute can pick either; see plan Appendix B §7). Anchored on the
   * full URL so /public/chat — which shares the /chat suffix — is excluded.
   */
  async expectPostLoginRedirect() {
    await expect(this.page).toHaveURL(/^https?:\/\/[^/]+\/(home|chat)(\?.*)?$/, {
      timeout: TIMEOUTS.PAGE_LOAD,
    });
  }

  // ---------------------------------------------------------------------------
  // Landing-page context (used by specs that verify the modal opens).
  // ---------------------------------------------------------------------------

  get landingHeroHeading() {
    return this.page.getByRole('heading', { level: 1, name: /Your next trip/ });
  }

  // V2 landing (since v2026.4.9) replaced the "Start your trip" button with a
  // chat search input. That input is now the primary landing CTA.
  // The landing page now renders three inputs sharing the "Chat with Voya AI"
  // aria-label (hero, closing section, and chat panel), so we target the hero
  // by its stable id.
  get landingHeroCta() {
    return this.page.locator('#landing-hero-search-input');
  }
}

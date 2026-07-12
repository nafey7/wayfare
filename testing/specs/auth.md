# Authentication Flows — E2E Test Plan

**Issue:** #788 (part 1 of #687)
**Feature:** Authentication — email check, registration, login, password reset
**Target URL:** `http://localhost:3002` (dev stack; `https://staging.myvoya.ai` in CI)
**Last updated:** 2026-04-18

---

## Architecture Notes for the Generator

The Voya auth UI is a **single combined modal** (`AuthModal`) and a standalone **`AuthPage`** (`/login`). Both implement the same three-step flow: `email` → `registration` (new user) or `login` (existing verified user).

Key routes:
- `/` — public landing; `AuthModal` opens on the header "Log in" button (V2 landing also has a chat input as primary CTA)
- `/login` — `AuthPage` (standalone, mirrors modal flow; see Appendix B — this route may be a 404)
- `/forgot-password` — `ForgotPasswordPage`
- `/reset-password?token=<token>` — `ResetPasswordPage` (validates token on mount)
- `/complete-registration?token=<token>` — `CompleteRegistrationPage` (validates token on mount, sets password)

Protected routes redirect to `/` (not `/login`) when unauthenticated — `ProtectedRoute` in `App.tsx`. `PublicRoute` redirects already-authenticated users to `/home`.

Password rules (Zod, both `complete-registration` and `reset-password`):
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number

Registration email field is **read-only** in step 2 of the modal and `AuthPage`; carried from step 1. "Back" returns to step 1 without losing the email value.

Google OAuth button is visible on the email step of both modal and `AuthPage`. It is **not covered** by automated E2E — marked `@manual` in the relevant scenario.

Fixture availability:
- `authenticatedUser` — environment-aware (local: registers via API + MailHog; staging: logs in with env vars)
- `registeredUser` — unverified user, local only (`@mock-required`)
- `userWithResetToken` — verified user with a live reset token, local only (`@mock-required`)

---

## Section 1 — Email Check (Modal entry point)

**Seed:** `testing/seed.spec.js`
**Starting state:** Fresh browser session, no cookies or localStorage, navigated to `http://localhost:3002`.

The email check is the gateway step shared by both login and registration. The UI branches based on the API response from `POST /api/auth/check-email`.

### Scenario 1.1 — Auth modal opens from the landing page CTA

**Tag:** (none — runs everywhere)

**Steps:**
1. Navigate to `http://localhost:3002` using `navigateToApp(page)`.
2. Verify the heading "Your next trip, planned in minutes." is visible using `page.getByRole('heading', { level: 1 })`.
3. Verify the chat input ("Ask Voya AI to plan your trip…") is visible using `page.getByRole('textbox', { name: 'Chat with Voya AI' })`.
4. Open the auth modal using `openAuthModal(page)` (tries the "Log in" header button then hamburger fallback).
5. Verify a dialog is visible using `page.getByRole('dialog')`.
6. Verify the dialog title reads "Login" using `page.getByRole('heading', { name: 'Login' })`.
7. Verify the "Email Address" text field is visible using `page.getByLabel('Email Address')`.
8. Verify a "Continue" button is visible and enabled using `page.getByRole('button', { name: 'Continue' })`.
9. ~~Verify a Google sign-in button is visible (presence check only — no interaction).~~ **Deferred** — `GoogleAuthButton` renders `null` when `/api/config/google` reports `enabled: false`, which is the default in the `compose.test.yaml` stack. Presence is env-dependent, so the automated test omits this assertion. Scenario 3.7 owns the manual Google OAuth check (`@manual`).

**Expected outcome:** The modal opens in the `email` step, showing the email field and "Continue" button. (Google OAuth button is env-dependent — see step 9 note.)

### Scenario 1.2 — Invalid email format is rejected client-side

**Tag:** (none — runs everywhere)

**Steps:**
1. Navigate to `http://localhost:3002` and open the auth modal using `openAuthModal(page)`.
2. Fill the "Email Address" field with `not-an-email` using `page.getByLabel('Email Address').fill('not-an-email')`.
3. Click the "Continue" button using `page.getByRole('button', { name: 'Continue' })`.
4. Verify a validation error is visible using `page.getByText(/invalid email/i)`.
5. Verify the modal has NOT advanced (dialog title is still "Login").
6. Verify the "Email Address" field is still visible and editable.

**Expected outcome:** Client-side Zod validation fires. No API call is made. Error shown under the email field.

### Scenario 1.3 — Empty email submission is rejected client-side

**Tag:** (none — runs everywhere)

**Steps:**
1. Navigate to `http://localhost:3002` and open the auth modal.
2. Leave the "Email Address" field empty.
3. Click the "Continue" button.
4. Verify a validation error appears using `page.getByText(/invalid email/i)`.
5. Verify the modal remains on the email step.

**Expected outcome:** Submission is blocked. An inline error appears under the email field.

### Scenario 1.4 — New email address routes to registration step

**Tag:** `@mock-required`

**Steps:**
1. Navigate to `http://localhost:3002` and open the auth modal.
2. Generate a unique test email using `generateTestUser()` from `utils/constants.js`.
3. Fill the "Email Address" field with the generated email.
4. Click "Continue".
5. Wait for the `POST /api/auth/check-email` 200 response using `page.waitForResponse(r => r.url().includes('/auth/check-email') && r.status() === 200)`.
6. Verify the dialog title changes to "Create Account" using `page.getByRole('heading', { name: 'Create Account' })`.
7. Verify the "First Name" field is visible using `page.getByLabel('First Name')`.
8. Verify the "Last Name" field is visible using `page.getByLabel('Last Name')`.
9. Verify the email field is **disabled** (read-only, pre-filled with the entered email).
10. Verify an info alert is visible containing "Please enter your details to complete registration."

**Expected outcome:** Modal transitions from `email` step to `registration` step.

### Scenario 1.5 — Existing verified email routes to login step

**Tag:** `@mock-required`
**Fixture:** `authenticatedUser` (API-level only — do not inject browser state)

**Steps:**
1. Obtain a verified user's `email` from the `authenticatedUser` fixture (request context only).
2. Navigate to `http://localhost:3002` and open the auth modal.
3. Fill the "Email Address" field with the verified user's email.
4. Click "Continue".
5. Wait for the `POST /api/auth/check-email` 200 response.
6. Verify the dialog title changes to "Welcome Back" using `page.getByRole('heading', { name: 'Welcome Back' })`.
7. Verify the "Password" field is visible using `page.getByLabel('Password')`.
8. Verify the email field is **disabled** and pre-filled with the verified email.
9. Verify an info alert contains "Welcome back! Please enter your password."
10. Verify a "Forgot your password?" button is visible using `page.getByRole('button', { name: /forgot your password/i })`.

**Expected outcome:** Modal transitions from `email` step to `login` step.

### Scenario 1.6 — Unverified email triggers resend and stays on email step

**Tag:** `@mock-required`
**Fixture:** `registeredUser`

**Steps:**
1. Obtain the unverified user's `email` from the `registeredUser` fixture.
2. Navigate to `http://localhost:3002` and open the auth modal.
3. Fill the "Email Address" field with the unverified user's email.
4. Click "Continue".
5. Wait for the `POST /api/auth/check-email` 200 response.
6. Verify the modal remains on the email step (title still "Login").
7. Verify a success-severity alert is visible using `expect(page.getByRole('alert')).toBeVisible()`.
8. Verify MailHog received a new email for the address using `mailhog.waitForEmail(email, TIMEOUTS.EMAIL_DELIVERY)`.

**Expected outcome:** Modal stays on email step. Backend auto-resends the verification email. Success alert is shown.

### Scenario 1.7 — "Cancel" button dismisses the modal

**Tag:** (none — runs everywhere)

**Steps:**
1. Navigate to `http://localhost:3002` and open the auth modal.
2. Click the "Cancel" button using `page.getByRole('button', { name: 'Cancel' })`.
3. Verify the dialog is no longer visible using `expect(page.getByRole('dialog')).not.toBeVisible()`.
4. Verify the URL is still `http://localhost:3002/`.

**Expected outcome:** Modal closes. No navigation occurs.

### Scenario 1.8 — Close icon (X) dismisses the modal

**Tag:** (none — runs everywhere)

**Steps:**
1. Navigate to `http://localhost:3002` and open the auth modal.
2. Click the close icon button using `page.getByRole('button', { name: 'close' })` (MUI renders `aria-label="close"` on the IconButton).
3. Verify the dialog is no longer visible.
4. Verify the landing page is still rendered.

**Expected outcome:** Modal closes cleanly.

### Scenario 1.9 — "Back" button returns from registration step to email step

**Tag:** `@mock-required`

**Steps:**
1. Navigate to `http://localhost:3002` and open the auth modal.
2. Enter a new (non-existent) email and click "Continue" to reach the registration step.
3. Verify the modal shows the "Create Account" title.
4. Click the "Back" button using `page.getByRole('button', { name: 'Back' })`.
5. Verify the modal returns to the "Login" step (email input is visible and editable).

**Expected outcome:** "Back" returns cleanly to the email step. The email field is reset/editable.

### Scenario 1.10 — "Back" button returns from login step to email step

**Tag:** `@mock-required`
**Fixture:** `authenticatedUser` (API-level only)

**Steps:**
1. Navigate to `http://localhost:3002` and open the auth modal.
2. Enter the verified user's email and click "Continue" to reach the login step.
3. Verify the modal shows the "Welcome Back" title.
4. Click the "Back" button using `page.getByRole('button', { name: 'Back' })`.
5. Verify the modal returns to the "Login" step.

**Expected outcome:** "Back" returns cleanly to the email step from the login step.

---

## Section 2 — Registration

**Seed:** `testing/seed.spec.js`
**Starting state:** Fresh browser session. All scenarios requiring MailHog are tagged `@mock-required`.

The registration flow: enter new email → "Create Account" step → fill first/last name → "Complete Registration" → success state ("Check your email...") → user clicks email link → `/complete-registration?token=` → set password → auto-login → `/home`.

### Scenario 2.1 — Successful new user registration (happy path, modal)

**Tag:** `@mock-required`

**Steps:**
1. Navigate to `http://localhost:3002` and open the auth modal.
2. Generate a unique test user using `generateTestUser()`.
3. Fill "Email Address" with `testUser.email` and click "Continue".
4. Wait for the "Create Account" step to appear.
5. Fill "First Name" with `testUser.firstName` using `page.getByLabel('First Name').fill(testUser.firstName)`.
6. Fill "Last Name" with `testUser.lastName` using `page.getByLabel('Last Name').fill(testUser.lastName)`.
7. Click the "Complete Registration" button using `page.getByRole('button', { name: 'Complete Registration' })`.
8. Wait for the `POST /api/auth/register` 200 response.
9. Verify a success alert "Registration initiated. Please check your email" is visible.
10. Verify the modal shows the post-success state: text "Check your email and click the link to set your password" is visible.
11. Verify a "Got it" button is visible using `page.getByRole('button', { name: 'Got it' })`.
12. Verify MailHog received an email for `testUser.email` using `mailhog.waitForEmail(testUser.email, TIMEOUTS.EMAIL_DELIVERY)`.

**Expected outcome:** Registration initiated. Success messaging shown in modal. Verification email in MailHog.

### Scenario 2.2 — Registration form requires first name

**Tag:** `@mock-required`

**Steps:**
1. Open the auth modal and advance to the "Create Account" step using a new email.
2. Leave "First Name" empty.
3. Fill "Last Name" with "Smith".
4. Click "Complete Registration".
5. Verify validation error "First name is required" is visible using `page.getByText('First name is required')`.
6. Verify no `POST /api/auth/register` request was made.

**Expected outcome:** Client-side validation blocks submission.

### Scenario 2.3 — Registration form requires last name

**Tag:** `@mock-required`

**Steps:**
1. Open the auth modal and advance to the "Create Account" step.
2. Fill "First Name" with "Jane".
3. Leave "Last Name" empty.
4. Click "Complete Registration".
5. Verify validation error "Last name is required" is visible.

**Expected outcome:** Client-side validation blocks submission.

### Scenario 2.4 — First name exceeding 50 characters is rejected

**Tag:** `@mock-required`

**Steps:**
1. Open the auth modal and advance to the "Create Account" step.
2. Fill "First Name" with a 51-character string (e.g. `'A'.repeat(51)`).
3. Fill "Last Name" with "Doe".
4. Click "Complete Registration".
5. Verify validation error "First name must be less than 50 characters" is visible.

**Expected outcome:** Zod `max(50)` validation rejects oversized names.

### Scenario 2.5 — Email verification link loads CompleteRegistrationPage with valid token

**Tag:** `@mock-required`
**Fixture:** `registeredUser`

**Steps:**
1. Use the `registeredUser` fixture to obtain `registrationToken`.
2. Navigate directly to `http://localhost:3002/complete-registration?token=<registrationToken>`.
3. Wait for `networkidle`.
4. Verify the page heading "Complete Registration" is visible using `page.getByRole('heading', { name: 'Complete Registration' })`.
5. Verify a loading indicator ("Validating your link...") appears and then the form appears.
6. Verify the "Password" field is visible using `page.getByLabel('Password')`.
7. Verify the "Confirm Password" field is visible using `page.getByLabel('Confirm Password')`.
8. Verify the "Complete Registration" submit button is visible and enabled.

**Expected outcome:** Token validated on mount. Password-setting form is shown.

### Scenario 2.6 — New user sets password and completes registration (happy path)

**Tag:** `@mock-required`
**Fixture:** `registeredUser`

**Steps:**
1. Use the `registeredUser` fixture to obtain `registrationToken`.
2. Navigate to `http://localhost:3002/complete-registration?token=<registrationToken>`.
3. Wait for the password form to appear.
4. Fill "Password" with `NewPassword123!` using `page.getByLabel('Password').fill('NewPassword123!')`.
5. Fill "Confirm Password" with `NewPassword123!` using `page.getByLabel('Confirm Password').fill('NewPassword123!')`.
6. Click the "Complete Registration" button.
7. Wait for the `POST /api/auth/complete-registration` 200 response.
8. Verify the URL changes to `/home` using `expect(page).toHaveURL(/\/home/)`.
9. Verify the user appears authenticated (navigation bar renders authenticated variant).

**Expected outcome:** Password set, user auto-logged in, redirected to `/home`.

### Scenario 2.7 — Password below minimum length rejected on CompleteRegistrationPage

**Tag:** `@mock-required`
**Fixture:** `registeredUser`

**Steps:**
1. Navigate to `/complete-registration?token=<registrationToken>` with a valid token.
2. Fill "Password" with `Short1` (fewer than 8 characters).
3. Fill "Confirm Password" with `Short1`.
4. Click "Complete Registration".
5. Verify validation error "Password must be at least 8 characters" is visible using `page.getByText(/at least 8 characters/i)`.

**Expected outcome:** Client-side Zod validation rejects short passwords.

### Scenario 2.8 — Password missing uppercase letter is rejected

**Tag:** `@mock-required`
**Fixture:** `registeredUser`

**Steps:**
1. Navigate to `/complete-registration?token=<registrationToken>` with a valid token.
2. Fill "Password" with `alllowercase1`.
3. Fill "Confirm Password" with `alllowercase1`.
4. Click "Complete Registration".
5. Verify validation error "Password must contain at least one uppercase letter" is visible.

**Expected outcome:** Zod regex validation rejects passwords without uppercase.

### Scenario 2.9 — Mismatched passwords rejected on CompleteRegistrationPage

**Tag:** `@mock-required`
**Fixture:** `registeredUser`

**Steps:**
1. Navigate to `/complete-registration?token=<registrationToken>` with a valid token.
2. Fill "Password" with `ValidPass1!`.
3. Fill "Confirm Password" with `DifferentPass2!`.
4. Click "Complete Registration".
5. Verify validation error "Passwords do not match" is visible using `page.getByText('Passwords do not match')`.

**Expected outcome:** Zod `.refine()` cross-field validation fires. No API call is made.

### Scenario 2.10 — Invalid registration token shows error state

**Tag:** (none — runs everywhere)

**Steps:**
1. Navigate to `http://localhost:3002/complete-registration?token=definitely-invalid-token-xyz`.
2. Wait for `networkidle`.
3. Verify a loading state briefly appears and then resolves.
4. Verify an error alert is visible using `page.getByRole('alert')` with `severity="error"`.
5. Verify the alert text "This registration link is invalid or has expired." is visible using `page.getByText(/invalid or has expired/i)`.
6. Verify a "Back to Login" button is visible using `page.getByRole('button', { name: 'Back to Login' })`.

**Expected outcome:** Invalid token shows error state. No form is shown.

### Scenario 2.11 — Missing token parameter shows error state

**Tag:** (none — runs everywhere)

**Steps:**
1. Navigate to `http://localhost:3002/complete-registration` (no `?token=` parameter).
2. Wait for `networkidle`.
3. Verify an error alert "This registration link is invalid or has expired." is visible.
4. Verify a "Back to Login" button is visible.

**Expected outcome:** Missing token treated as invalid — same error state as 2.10.

### Scenario 2.12 — Resend verification email by re-entering unverified email

**Tag:** `@mock-required`
**Fixture:** `registeredUser`

**Steps:**
1. Obtain the unverified user's `email` from the `registeredUser` fixture.
2. Clear MailHog emails using `mailhog.clearEmails()`.
3. Navigate to `http://localhost:3002` and open the auth modal.
4. Fill "Email Address" with the unverified email and click "Continue".
5. Wait for the `POST /api/auth/check-email` 200 response.
6. Verify the modal shows a success alert (backend auto-resends activation email).
7. Verify a new email is delivered to MailHog using `mailhog.waitForEmail(email, TIMEOUTS.EMAIL_DELIVERY)`.

**Expected outcome:** Backend auto-resends the registration email. Success alert shown. New email in MailHog.

---

## Section 3 — Login

**Seed:** `testing/seed.spec.js`
**Starting state:** Fresh browser session unless stated otherwise.

### Scenario 3.1 — Successful login with correct credentials (happy path, modal)

**Tag:** `@mock-required`
**Fixture:** `authenticatedUser` (API-level only — obtains email/password without injecting browser state)

**Steps:**
1. From the `authenticatedUser` fixture, extract `email` and `password`.
2. Call `clearAuthState(page)` to ensure no stale session.
3. Navigate to `http://localhost:3002` and open the auth modal.
4. Fill "Email Address" with `email` and click "Continue".
5. Wait for the "Welcome Back" step.
6. Fill "Password" with `password` using `page.getByLabel('Password').fill(password)`.
7. Click the "Sign In" button using `page.getByRole('button', { name: 'Sign In' })`.
8. Wait for the `POST /api/auth/login` 200 response.
9. Verify the dialog is dismissed.
10. Verify the URL changes to `/home` or `/chat` using `expect(page).toHaveURL(/\/(home|chat)/)`.

**Expected outcome:** User is logged in, redirected to the post-auth page.

### Scenario 3.2 — Wrong password shows error message

**Tag:** `@mock-required`
**Fixture:** `authenticatedUser` (API-level only)

**Steps:**
1. From the `authenticatedUser` fixture, extract `email`.
2. Navigate to `http://localhost:3002` and open the auth modal.
3. Fill "Email Address" with `email` and click "Continue".
4. Wait for the "Welcome Back" step.
5. Fill "Password" with `WrongPassword999!`.
6. Click "Sign In".
7. Wait for the `POST /api/auth/login` 401 response.
8. Verify an error alert "Login failed. Please try again." is visible using `page.getByRole('alert')`.
9. Verify the modal remains open on the "Welcome Back" step.

**Expected outcome:** Wrong password shows error. Modal stays open. No redirect.

### Scenario 3.3 — Password field minimum length validation (client-side)

**Tag:** `@mock-required`
**Fixture:** `authenticatedUser` (API-level only)

**Steps:**
1. Advance to the "Welcome Back" login step by entering the verified user's email.
2. Fill "Password" with `short` (fewer than 8 characters).
3. Click "Sign In".
4. Verify validation error "Password must be at least 8 characters" is visible.
5. Verify no `POST /api/auth/login` request was made.

**Expected outcome:** Client-side Zod validation blocks the API call.

### Scenario 3.4 — Login via the standalone AuthPage

**Tag:** `@mock-required`
**Fixture:** `authenticatedUser` (API-level only)

**Note for Generator:** `App.tsx` does not define a `<Route path="/login">`. Navigating to `/login` may redirect to `/` via the catch-all. Verify the route exists before generating this test. If `/login` returns a 404 or redirects, document as a known issue and skip this test in favor of modal-based Scenario 3.1.

**Steps:**
1. From the `authenticatedUser` fixture, extract `email` and `password`.
2. Navigate to `http://localhost:3002/login`.
3. Check the URL after navigation — if it redirected to `/`, mark this scenario as a known routing gap and skip.
4. If `/login` resolves, verify heading "Welcome to Voya" is visible using `page.getByRole('heading', { name: 'Welcome to Voya' })`.
5. Fill "Email" with `email` and click "Continue".
6. Verify heading changes to "Welcome Back".
7. Fill "Password" with `password` and click "Sign In".
8. Wait for `POST /api/auth/login` 200 response.
9. Verify URL changes to `/home` or `/chat`.

**Expected outcome:** Standalone auth page supports the same flow as the modal.

### Scenario 3.5 — Authenticated user visiting landing is redirected to `/home`

**Tag:** `@mock-required`
**Fixture:** `authenticatedUser` (provides `accessToken`)

**Steps:**
1. Use the `authenticatedUser` fixture to get `accessToken`.
2. Set the token in localStorage using `page.evaluate(token => localStorage.setItem('Authorization', token), accessToken)`.
3. Navigate to `http://localhost:3002/`.
4. Wait for `networkidle`.
5. Verify the URL changes to `/home` (or `/chat` if public chat preference is set) using `expect(page).toHaveURL(/\/(home|chat)/)`.
6. Verify the landing "Log in" header button is NOT visible (authenticated users see the avatar menu instead).

**Expected outcome:** `PublicRoute` detects authenticated state and redirects to `/home`.

### Scenario 3.6 — "Forgot your password?" navigates to the forgot-password page

**Tag:** `@mock-required`
**Fixture:** `authenticatedUser` (API-level only)

**Steps:**
1. Open the auth modal and advance to the "Welcome Back" login step.
2. Click "Forgot your password?" using `page.getByRole('button', { name: /forgot your password/i })`.
3. Verify the modal closes.
4. Verify URL changes to `/forgot-password` using `expect(page).toHaveURL(/\/forgot-password/)`.
5. Verify heading "Reset Password" is visible.

**Expected outcome:** Clicking "Forgot your password?" closes the modal and navigates to `/forgot-password`.

### Scenario 3.7 — Google OAuth button visible (manual, out-of-scope for automated E2E)

**Tag:** `@manual`

> **Out of scope for automated E2E.** The Google OAuth flow requires a third-party popup that Playwright cannot reliably control without mocking the OAuth provider.

**Manual steps for QA reference:**
1. Open the auth modal or navigate to `/login`.
2. Verify the "Continue with Google" (or equivalent label) button is visible.
3. Click it and confirm a Google OAuth popup or redirect opens.
4. Complete the OAuth flow with a valid Google account.
5. Verify the user is redirected to `/home` and appears authenticated.

---

## Section 4 — Password Reset

**Seed:** `testing/seed.spec.js`
**Starting state:** Fresh browser session.

Two pages:
- `ForgotPasswordPage` (`/forgot-password`) — accepts email, sends reset link.
- `ResetPasswordPage` (`/reset-password?token=`) — validates token on mount, shows form to set new password.

### Scenario 4.1 — Valid email submits forgot-password request (happy path)

**Tag:** `@mock-required`
**Fixture:** `authenticatedUser` (API-level only)

**Steps:**
1. Navigate to `http://localhost:3002/forgot-password`.
2. Verify heading "Reset Password" is visible using `page.getByRole('heading', { name: 'Reset Password' })`.
3. Fill "Email" with the verified user's email using `page.getByLabel('Email').fill(email)`.
4. Click "Send Reset Link" using `page.getByRole('button', { name: 'Send Reset Link' })`.
5. Wait for `POST /api/auth/forgot-password` 200 response.
6. Verify a success alert "If an account exists with this email, you will receive a password reset link shortly." is visible using `page.getByRole('alert')`.
7. Verify a "Back to Login" button is visible using `page.getByRole('button', { name: 'Back to Login' })`.
8. Verify MailHog received an email for the user's address using `mailhog.waitForEmail(email, TIMEOUTS.EMAIL_DELIVERY)`.

**Expected outcome:** Form submits, success state shown, reset email arrives in MailHog.

### Scenario 4.2 — Non-existent email still shows success (no email enumeration)

**Tag:** (none — runs everywhere)

**Steps:**
1. Navigate to `http://localhost:3002/forgot-password`.
2. Fill "Email" with `noreply-ghost-user-xyz@example.com`.
3. Click "Send Reset Link".
4. Wait for `POST /api/auth/forgot-password` 200 response.
5. Verify the success alert "If an account exists with this email, you will receive a password reset link shortly." is visible.

**Expected outcome:** Backend returns 200 regardless of email existence. Frontend shows same success message (prevents enumeration).

### Scenario 4.3 — Invalid email format rejected on forgot-password page

**Tag:** (none — runs everywhere)

**Steps:**
1. Navigate to `http://localhost:3002/forgot-password`.
2. Fill "Email" with `not-a-valid-email`.
3. Click "Send Reset Link".
4. Verify inline validation error "Please enter a valid email address" is visible using `page.getByText(/valid email/i)`.
5. Verify no API call was made.

**Expected outcome:** Client-side Zod validation blocks the request.

### Scenario 4.4 — "Back to Login" link on forgot-password form navigates to login

**Tag:** (none — runs everywhere)

**Steps:**
1. Navigate to `http://localhost:3002/forgot-password`.
2. Locate the "Back to Login" link (rendered as `<Link>` in the form state) using `page.getByRole('link', { name: 'Back to Login' })`.
3. Click it.
4. Verify navigation to `/login` occurs (or `/` if `/login` is undefined — see Appendix B).

**Expected outcome:** The link routes the user toward the login entry point.

### Scenario 4.5 — Valid reset token shows the reset password form

**Tag:** `@mock-required`
**Fixture:** `userWithResetToken`

**Steps:**
1. Use the `userWithResetToken` fixture to obtain a valid `resetToken`.
2. Navigate to `http://localhost:3002/reset-password?token=<resetToken>`.
3. Wait for `networkidle`.
4. Verify a loading indicator "Validating reset link..." appears briefly.
5. After loading resolves, verify heading "Set New Password" is visible using `page.getByRole('heading', { name: 'Set New Password' })`.
6. Verify "New Password" field is visible using `page.getByLabel('New Password')`.
7. Verify "Confirm Password" field is visible using `page.getByLabel('Confirm Password')`.
8. Verify the "Reset Password" submit button is visible and enabled.

**Expected outcome:** Token validated server-side on mount. Password form is shown.

### Scenario 4.6 — User successfully resets their password

**Tag:** `@mock-required`
**Fixture:** `userWithResetToken`

**Steps:**
1. Use the `userWithResetToken` fixture to obtain a valid `resetToken`.
2. Navigate to `http://localhost:3002/reset-password?token=<resetToken>`.
3. Wait for the form to appear.
4. Fill "New Password" with `BrandNewPass1!` using `page.getByLabel('New Password').fill('BrandNewPass1!')`.
5. Fill "Confirm Password" with `BrandNewPass1!`.
6. Click "Reset Password" using `page.getByRole('button', { name: 'Reset Password' })`.
7. Wait for `POST /api/auth/reset-password` 200 response.
8. Verify success alert "Your password has been reset successfully." is visible.
9. Verify a "Sign In" button is visible using `page.getByRole('button', { name: 'Sign In' })`.
10. Click "Sign In" and verify navigation to `/login` (or `/`).

**Expected outcome:** Password reset succeeds. Success state shown. User can navigate to login.

### Scenario 4.7 — Mismatched passwords rejected on reset-password page

**Tag:** `@mock-required`
**Fixture:** `userWithResetToken`

**Steps:**
1. Navigate to `/reset-password?token=<resetToken>` with a valid token.
2. Fill "New Password" with `ValidPass1!`.
3. Fill "Confirm Password" with `DifferentPass2!`.
4. Click "Reset Password".
5. Verify validation error "Passwords do not match" is visible.

**Expected outcome:** Zod cross-field validation fires. No API call is made.

### Scenario 4.8 — Password below 8 characters rejected on reset-password page

**Tag:** `@mock-required`
**Fixture:** `userWithResetToken`

**Steps:**
1. Navigate to `/reset-password?token=<resetToken>` with a valid token.
2. Fill "New Password" with `Ab1` (3 characters).
3. Fill "Confirm Password" with `Ab1`.
4. Click "Reset Password".
5. Verify validation error "Password must be at least 8 characters" is visible.

**Expected outcome:** Client-side validation rejects short passwords before any API call.

### Scenario 4.9 — Invalid reset token shows error state

**Tag:** (none — runs everywhere)

**Steps:**
1. Navigate to `http://localhost:3002/reset-password?token=this-is-an-invalid-token-xyz`.
2. Wait for `networkidle`.
3. Verify a loading state briefly appears and resolves.
4. Verify an error alert "This password reset link is invalid or has expired." is visible using `page.getByRole('alert')`.
5. Verify a "Request New Reset Link" button is visible using `page.getByRole('button', { name: 'Request New Reset Link' })`.
6. Verify the "New Password" and "Confirm Password" fields are NOT visible.

**Expected outcome:** Invalid token shows error state. Password form is hidden.

### Scenario 4.10 — Missing token on reset-password page shows error

**Tag:** (none — runs everywhere)

**Steps:**
1. Navigate to `http://localhost:3002/reset-password` (no `?token=` parameter).
2. Wait for `networkidle`.
3. Verify error alert "This password reset link is invalid or has expired." is visible.
4. Verify "Request New Reset Link" button is visible.

**Expected outcome:** Missing token treated as invalid.

### Scenario 4.11 — "Request New Reset Link" navigates to forgot-password page

**Tag:** (none — runs everywhere)

**Steps:**
1. Navigate to `http://localhost:3002/reset-password?token=bad-token-abc`.
2. Wait for the error state to appear.
3. Click "Request New Reset Link" using `page.getByRole('button', { name: 'Request New Reset Link' })`.
4. Verify navigation to `/forgot-password` using `expect(page).toHaveURL(/\/forgot-password/)`.

**Expected outcome:** Error state CTA correctly routes to `/forgot-password`.

---

## Section 5 — Protected Routes (Unauthenticated Access)

**Seed:** `testing/seed.spec.js`
**Starting state:** Fresh browser session with no auth state (no localStorage token). Call `clearAuthState(page)` in `beforeEach`.

`ProtectedRoute` in `App.tsx` redirects unauthenticated users to `/` (NOT `/login`).

### Scenario 5.1 — Unauthenticated user navigating to `/home` is redirected to landing

**Tag:** (none — runs everywhere)

**Steps:**
1. Call `clearAuthState(page)`.
2. Navigate directly to `http://localhost:3002/home`.
3. Wait for `networkidle`.
4. Verify the URL is `http://localhost:3002/` using `expect(page).toHaveURL('http://localhost:3002/')`.
5. Verify the landing page heading "Your next trip, planned in minutes." is visible.

**Expected outcome:** `ProtectedRoute` redirects to `/`. Landing page is shown.

### Scenario 5.2 — Unauthenticated user navigating to `/profile` is redirected to landing

**Tag:** (none — runs everywhere)

**Steps:**
1. Call `clearAuthState(page)`.
2. Navigate directly to `http://localhost:3002/profile`.
3. Wait for `networkidle`.
4. Verify the URL is `http://localhost:3002/`.

**Expected outcome:** Protected route redirects to `/`.

### Scenario 5.3 — Unauthenticated user navigating to `/chat` is redirected to landing

**Tag:** (none — runs everywhere)

**Steps:**
1. Call `clearAuthState(page)`.
2. Navigate directly to `http://localhost:3002/chat`.
3. Wait for `networkidle`.
4. Verify the URL is `http://localhost:3002/`.

**Expected outcome:** Chat route is protected. Unauthenticated access redirects to `/`.

### Scenario 5.4 — Unauthenticated user navigating to `/itineraries` is redirected to landing

**Tag:** (none — runs everywhere)

**Steps:**
1. Call `clearAuthState(page)`.
2. Navigate directly to `http://localhost:3002/itineraries`.
3. Wait for `networkidle`.
4. Verify the URL is `http://localhost:3002/`.

**Expected outcome:** Protected route redirects to `/`.

### Scenario 5.5 — Unauthenticated API request to a protected endpoint returns 401

**Tag:** (none — runs everywhere)

**Steps:**
1. Make a `GET` request to `URLS.BACKEND + '/api/flights/my-bookings?limit=10'` with no Authorization header using `request.get(...)`.
2. Verify the response status is 401 using `expect(response.status()).toBe(401)`.

**Expected outcome:** Backend rejects unauthenticated API access with HTTP 401.

### Scenario 5.6 — Invalid token in localStorage is treated as unauthenticated

**Tag:** (none — runs everywhere)

**Steps:**
1. Set a malformed token in localStorage using `page.evaluate(() => localStorage.setItem('Authorization', 'invalid.jwt.token'))`.
2. Navigate to `http://localhost:3002/home`.
3. Wait for `networkidle`.
4. Verify the URL redirects to `http://localhost:3002/`.

**Note for Generator:** The Redux `authSlice` loads the token from `localStorage` key `Authorization`. An invalid JWT string may fail `selectIsAuthenticated` or it may be accepted (presence check only). If the app renders `/home` with an invalid token, document as a separate bug.

**Expected outcome:** Invalid token is not treated as a valid session. Redirect to landing occurs.

### Scenario 5.7 — Unknown route redirects to landing

**Tag:** (none — runs everywhere)

**Steps:**
1. Call `clearAuthState(page)`.
2. Navigate to `http://localhost:3002/definitely-does-not-exist-route`.
3. Wait for `networkidle`.
4. Verify the URL is `http://localhost:3002/` (catch-all `<Route path="*">` in `App.tsx`).
5. Verify the landing page is displayed.

**Expected outcome:** Catch-all redirects unknown routes to `/`.

---

## Appendix A — Selector Reference

Prefer `getByRole` / `getByLabel` / `getByText` for all elements with accessible names. Fall back to `SELECTORS.*` only for elements without an accessible name.

| Element | Preferred locator | SELECTORS fallback |
|---|---|---|
| Auth modal dialog | `page.getByRole('dialog')` | `SELECTORS.AUTH_MODAL` |
| "Email Address" field (modal) | `page.getByLabel('Email Address')` | `SELECTORS.EMAIL_INPUT` |
| "Email" field (AuthPage/ForgotPassword) | `page.getByLabel('Email')` | `SELECTORS.EMAIL_INPUT` |
| Continue button | `page.getByRole('button', { name: 'Continue' })` | `SELECTORS.CONTINUE_BUTTON` |
| Sign In button | `page.getByRole('button', { name: 'Sign In' })` | — |
| First Name field | `page.getByLabel('First Name')` | `SELECTORS.REGISTRATION.FIRST_NAME` |
| Last Name field | `page.getByLabel('Last Name')` | `SELECTORS.REGISTRATION.LAST_NAME` |
| Password field | `page.getByLabel('Password')` | `SELECTORS.REGISTRATION.PASSWORD` |
| Confirm Password field | `page.getByLabel('Confirm Password')` | — |
| New Password field | `page.getByLabel('New Password')` | — |
| Close button (modal X) | `page.getByRole('button', { name: 'close' })` | — |
| Back button | `page.getByRole('button', { name: 'Back' })` | — |
| Cancel button | `page.getByRole('button', { name: 'Cancel' })` | — |
| Complete Registration button | `page.getByRole('button', { name: 'Complete Registration' })` | `SELECTORS.REGISTRATION.SUBMIT` |
| Send Reset Link button | `page.getByRole('button', { name: 'Send Reset Link' })` | — |
| Reset Password button | `page.getByRole('button', { name: 'Reset Password' })` | — |
| Request New Reset Link button | `page.getByRole('button', { name: 'Request New Reset Link' })` | — |
| Back to Login button (success state) | `page.getByRole('button', { name: 'Back to Login' })` | — |
| Back to Login link (form state) | `page.getByRole('link', { name: 'Back to Login' })` | — |
| Forgot password button | `page.getByRole('button', { name: /forgot your password/i })` | — |
| Error/success alert | `page.getByRole('alert')` | `SELECTORS.ERROR_MESSAGE` |

---

## Appendix B — Known Issues / Flags for Triage

1. **`/login` route is not registered in `App.tsx`.** The `AuthPage` component exists but `App.tsx` contains no `<Route path="/login">`. Pages like `ForgotPasswordPage` and `CompleteRegistrationPage` call `navigate('/login')` on some CTAs — this lands on the catch-all and redirects to `/`. Scenario 3.4 notes this; verify before generating the test. If confirmed, the Generator should skip Scenario 3.4 or convert it to a modal-based test.

2. **"Forgot your password?" is a `<Button>`, not an anchor.** In `AuthModal.tsx` it is rendered as `<Button variant="text">`. Use `getByRole('button', { name: /forgot your password/i })` not `getByRole('link')`.

3. **"Back to Login" has two element types on `ForgotPasswordPage`.** In the form state it is a `<Link>` (anchor); in the success state it is a `<Button>`. Scenarios 4.1 and 4.4 target different element types accordingly.

4. **Email field on registration and login steps is `disabled`.** Asserting its value with `.inputValue()` works even on disabled fields. Do not attempt to `.fill()` it on those steps.

5. **`ProtectedRoute` redirects to `/`, not `/login`.** All protected-route redirect assertions in Section 5 target `/` as the destination.

6. **Logout button selector is unresolved.** `SELECTORS.LOGOUT_BUTTON` covers common patterns but the NavbarHome user-menu structure requires live exploration. The Healer should resolve this if any generated test that depends on logout state fails.

7. **`PublicRoute` redirect for authenticated users can land on `/chat` instead of `/home`** when the public-chat localStorage flag (`voya_public_chat_route_user_messaged_v1`) is set. Scenarios 3.5 and Section 5 use `/\/(home|chat)/` regex patterns to tolerate both destinations.

---

*Plan produced by: playwright-test-planner agent — Voya auth flows (#788), code-read (live browser MCP not wired up at runtime; selectors should be verified against live app before Generator runs).*

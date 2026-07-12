# Google Places images — public chat security

This document describes how Voya protects **Google Places photo proxy** traffic for **guest (public chat) users**, and how to add **Cloudflare** edge controls in production. Application code lives in the backend (`app/api/public_places.py`, `app/core/places_session.py`, `app/core/public_places_rate_limit.py`) and frontend (`AuthenticatedImage`, `useLazyImage`).

---

## Defense layers (overview)

| Layer | Responsibility |
|-------|----------------|
| **1. Cloudflare (edge)** | Bot scoring, JS challenges, optional Turnstile — configured in the Cloudflare dashboard (not in this repo). |
| **2. Session continuity token** | Short-lived JWT (`places_session`) bound to `X-Public-Chat-Session` and client IP prefix; proves the browser went through chat before fetching photos. |
| **3. Rate limits (always on)** | Per-IP sliding window + per-session lifetime cap on `GET /api/public/places/photos/.../media` — not gated by `RATE_LIMIT_ENABLED`. |
| **4. Lazy-loaded images (browser)** | Guest Places images fetch only after the card intersects the **nearest scroll container** (or viewport); JWT images are unchanged (immediate fetch). Reduces scripted traffic; rate limits still apply. |

Authenticated users continue to use **`GET /api/places/photos/{resource}/media`** with a normal JWT (`Authorization: Bearer`). That path is unchanged.

---

## Session token flow (guest)

1. Guest sends a message with `X-Public-Chat-Session` to `POST /api/public/chat/message`.
2. When the response includes itinerary data with backend photo URLs, the API may return **`places_session_token`** (top-level field on `ChatResponse`).
3. The SPA stores the token in Redux + `sessionStorage` and, for each Places image, calls **`GET /api/public/places/photos/{path}/media`** with:
   - `X-Places-Session-Token: <jwt>`
   - `X-Public-Chat-Session: <same UUID as chat>`
4. The backend validates the JWT (type, expiry, session id, IP prefix), applies rate limits, then proxies bytes from Google.

Token claims (conceptually): `type: places_session`, `session_id`, `ip_prefix`, `iat`, `exp`. See `app/core/places_session.py`.

---

## Rate limit reference (backend constants)

Configurable in `app/core/security_constants.py` (names may vary slightly in code):

| Limit | Typical value | Notes |
|-------|----------------|-------|
| Per IP (sliding window) | 40 requests/minute | Public photo endpoint only. |
| Per guest session (lifetime) | 100 successful photo responses | Across token re-mints in the same browser session. |

Production tuning should follow staging metrics (429 rate, typical itinerary image counts).

### In-memory capacity eviction (backend)

If the process tracks more IPs or guest sessions than `_MAX_TRACKED_*` constants, the
rate limiter **evicts cold entries** using **last-activity time** (LRU-style), not
arbitrary FIFO order: IPs are dropped by oldest latest request timestamp; guest session
rows are dropped by oldest `last_seen` after a successful photo. See the module
docstring in `app/core/public_places_rate_limit.py`.

---

## Cloudflare: Super Bot Fight Mode (Pro)

**Goal:** Drop or challenge automated traffic before it hits the origin.

1. In **Cloudflare Dashboard** → **Security** → **Bots**, enable **Super Bot Fight Mode** (included on Pro+).
2. Add **WAF custom rules** (or Firewall Rules, depending on your plan UI), scoped to the public Places path, for example:
   - **Block** when `cf.bot_management.score` **less than** `30`
   - **Managed Challenge (JS)** when `cf.bot_management.score` **less than** `60`
3. **Expression scope example** (adjust zone/host):
   `(http.request.uri.path contains "/api/public/places/")`

Bot score field names follow your Cloudflare plan (Bot Management / Super Bot Fight). Validate expressions in the rule editor against your zone.

**Also apply** similar scoping to `POST /api/public/chat/message` if you want edge protection on guest chat itself (separate path prefix).

---

## Cloudflare Turnstile (optional, future hardening)

Turnstile is an **invisible** challenge widget. A possible future flow:

1. Create a Turnstile site in Cloudflare (**Turnstile** section).
2. Frontend: render the widget at a transition point (e.g. before or after the first itinerary with images).
3. Backend: verify the Turnstile token with `POST https://challenges.cloudflare.com/turnstile/v0/siteverify` before minting or refreshing `places_session_token`.

**Launch posture:** Session tokens + rate limits + lazy loading are sufficient for many deployments; Turnstile is optional if edge bot scores and billing alerts are healthy.

---

## Monitoring checklist

- **Google Cloud / Maps Platform**: Billing alert on Places API (Text Search + Places Photo) daily or monthly threshold.
- **Application logs** (grep / log aggregation):
  - **Token mint** (guest itinerary with photo URLs): `places_session_token_mint | session_prefix=<8 chars>`
  - **Public photo proxy**: `public_places_proxy | outcome=http_*` — `401` (missing/invalid token), `403` (expired / session / IP mismatch), `429` (rate limit, also `WARNING`), `400` (bad resource), `200` success at **DEBUG** (`bytes=<n>`). Rate limits include `Retry-After: 60` on `429`.
- **429 responses**: `Retry-After: 60` is set on the public photo route; tune limits using staging metrics if legitimate users hit `429`.
- **Sentry (if enabled):** Watch for spikes in client-side image load failures after deploys; backend 429s are logged and can be alerted via log-based metrics (avoid per-request Sentry noise).

## E2E coverage (Playwright)

- **`testing/e2e/tests/public-chat/public-itinerary-places-images.spec.js`**: Mocks chat + photo bytes (no Gemini/Places). Asserts guest `/public/chat` → `/public/chat/itinerary` image load, lazy behavior (no `<img>` until scroll), and authenticated `/chat` → `/itinerary` with JWT photo proxy. Tagged `@mock-required` (local Docker stack).

---

## Environment variables (backend)

| Variable | Purpose |
|----------|---------|
| `PLACES_SESSION_TOKEN_SECRET` | Signing key for guest Places session JWTs. In development, the app may fall back to a derivative of `SECRET_KEY`; set explicitly in production. |
| `PLACES_SESSION_TOKEN_EXPIRE_MINUTES` | Token lifetime (default often 60 minutes). |

See `app/core/config.py` for defaults and startup warnings.

---

## Related code

- Public photo route: `backend_python/app/api/public_places.py`
- Token mint/validate: `backend_python/app/core/places_session.py`
- Rate limiter: `backend_python/app/core/public_places_rate_limit.py`
- Chat token mint: `backend_python/app/domains/chat/service.py` (guest itinerary with photo URLs)
- Frontend: `frontend-v2/src/features/itinerary/components/AuthenticatedImage.tsx`, `frontend-v2/src/hooks/useLazyImage.ts`

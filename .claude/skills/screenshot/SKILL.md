---
name: screenshot
description: Take screenshots of Storybook stories, staging, production, or local dev. Uses playwright-cli with named sessions so login state persists across screenshots. Use when you need to visually verify components, compare environments, or debug UI issues.
allowed-tools: Bash(./bin/playwright-cli:*), Bash(npx playwright screenshot:*), Bash(mkdir:*), Bash(date:*), Read
argument-hint: [storybook <story-id>|staging|prod|local|<url>]
---

# Take Screenshots

Take a screenshot using `playwright-cli` and view it. Screenshots are saved to `.local/journal/YYYY-MM-DD/screenshots/`.

This skill uses `playwright-cli` (see `playwright-cli` skill for full reference) with **named sessions** so login state persists across multiple screenshots. Sessions used:

| Session | Use case |
|---|---|
| `voya-storybook` | Storybook stories at localhost:6006 |
| `voya-staging` | Deployed staging (auth persists) |
| `voya-prod` | Production (auth persists) |
| `voya-local` | Vite dev server at localhost:3002 |

## Setup

```bash
SCREENSHOTS=".local/journal/$(date +%Y-%m-%d)/screenshots"
mkdir -p "$SCREENSHOTS"
```

## Quick Commands

Based on $ARGUMENTS:

### `storybook <story-id>` - Screenshot a Storybook story
Requires Storybook running at localhost:6006.

```bash
./bin/playwright-cli -s=voya-storybook goto \
  "http://localhost:6006/iframe.html?id=$STORY_ID&viewMode=story"
./bin/playwright-cli -s=voya-storybook screenshot \
  --filename="$SCREENSHOTS/storybook-$STORY_ID.png"
```

Story ID format: title lowered, `/` becomes `-`, then `--default`.
Examples: `foundation-colors--default`, `flights-flightcard--default`

### `staging` - Screenshot staging
First time: agent will need to authenticate (if access protected).
Subsequent calls reuse the session.

```bash
./bin/playwright-cli -s=voya-staging goto https://staging.myvoya.ai
./bin/playwright-cli -s=voya-staging screenshot --filename="$SCREENSHOTS/staging.png"
```

### `prod` - Screenshot production
```bash
./bin/playwright-cli -s=voya-prod goto https://www.myvoya.ai
./bin/playwright-cli -s=voya-prod screenshot --filename="$SCREENSHOTS/prod.png"
```

### `local` - Screenshot local dev
```bash
./bin/playwright-cli -s=voya-local goto http://localhost:3002
./bin/playwright-cli -s=voya-local screenshot --filename="$SCREENSHOTS/local.png"
```

### `<url>` - Screenshot any URL
Defaults to the `voya-custom` named session so auth state persists across calls. If the URL belongs to one of the environments above, prefer that named session instead (`-s=voya-staging`, `-s=voya-prod`, etc.) so login state is shared.

```bash
./bin/playwright-cli -s=voya-custom goto "$URL"
./bin/playwright-cli -s=voya-custom screenshot --filename="$SCREENSHOTS/custom.png"
```

> Note: an unnamed (default) session is in-memory only and loses cookies between invocations. For any auth-gated URL, always pass `-s=<session-name>`.

## After Taking Screenshot

Always view the screenshot using Read to verify the result:

```
Read the screenshot file to view it.
```

## Comparing Environments

Take screenshots of the same page across environments to spot differences:

```bash
# Compare Storybook buttons with staging buttons
/screenshot storybook foundation-buttons--default
/screenshot staging
```

Then view both and compare visually.

## Why playwright-cli with named sessions?

Token-efficient (doesn't load schemas into context) and login state persists across calls. The session keeps cookies/storage in memory until `playwright-cli close` or `playwright-cli kill-all` runs. Use `./bin/playwright-cli list` to see active sessions and `./bin/playwright-cli show` to open the live session dashboard.

## Interactive Workflows (advanced)

For workflows that need clicking buttons, filling forms, or checking computed styles, use the full `playwright-cli` skill directly. See `.claude/skills/playwright-cli/SKILL.md` and its `references/` for:

- Element interactions (`click`, `fill`, `type`, `press`)
- Snapshots (`snapshot` returns the accessibility tree with element refs)
- JavaScript evaluation (`eval`)
- Network mocking, tracing, video recording
- Session and storage state management

## Fallback: legacy `npx playwright screenshot`

If `playwright-cli` is unavailable, fall back to the basic Playwright CLI:

```bash
npx playwright screenshot --wait-for-timeout 2000 --full-page \
  "$URL" "$SCREENSHOTS/screenshot.png"
```

Note: each invocation starts a fresh browser, no session reuse.

# PR #767 — Multi-Conversation Chat with Sidebar

**Issue:** [#749](https://github.com/myvoya/voya/issues/749)
**Branch:** `749-feature-multi-conversation-chat-with-sidebar`
**Net delta:** 27 files · +2380 / −81

## Goal

Replace the single-thread chat with a ChatGPT/Claude-style multi-conversation experience. Users now see a left-hand sidebar listing every chat they have, with start-new / switch / rename / soft-delete. Each conversation has fully isolated LangGraph agent memory — intent, slot-filling, and shared context no longer bleed across trips.

## Why this was needed

The previous single-thread model was unusable past one trip-in-flight:

- Old conversation context contaminated new searches (e.g. flight-search slot state from "Paris" trip leaking into a "Tokyo" trip).
- No way to return to a prior planning session — the only chat was "the latest one".
- LangGraph checkpointer state was scoped per `thread_id` but every chat shared one `thread_id` per user, so memory was effectively a single bucket.

## Architecture decisions

| Decision | Rationale |
|---|---|
| **`thread_id == chat_id` everywhere in LangGraph** | Each conversation gets its own checkpointer state — full isolation of agent memory, intent, slots, and shared context |
| **"New chat" is a UI-only reset** | No DB row created; the server only inserts a `conversations` row when the user actually sends the first message. Avoids a graveyard of empty "New conversation" rows |
| **Async LLM auto-naming on first message** | OpenAI `gpt-5.4-nano` generates a 2–5 word title. Naming failures are swallowed — they never block the chat response |
| **Title blocklist + fallback** | Generic titles ("New Conversation", "Chat", "Hello") are rejected and replaced with `"Travel Assistant"` so the sidebar never shows placeholders |
| **Upsert reducers on the frontend** | Backend may auto-create a conversation on first message, so Redux can hear about a `chat_id` before the sidebar list has refetched |
| **Checkpoint TTL bumped 24h → 30d** | Users return to older conversations with agent memory intact |
| **Soft delete (`is_deleted: true`)** | Hard-delete / GDPR wipe deferred as a follow-up |

---

## Backend changes

### New collection — `conversations`

Stores per-conversation metadata (name, timestamps, counts). The existing `chats_python` collection still holds individual messages.

**Schema (per document):**
```
chat_id              str  # PK, unique index
user_id              str  # owner
name                 str  # auto-generated, max ~50 chars
is_deleted           bool # soft-delete flag
message_count        int
last_message_at      datetime
last_message_preview str  # first 100 chars of last user message
created_at           datetime
updated_at           datetime
```

### Migration `006_create_conversations_collection.py`

- Creates the `conversations` collection
- Creates two named indexes:
  - `user_active_conversations` — `(user_id, is_deleted, last_message_at desc)` — drives the sidebar list query
  - `chat_id_unique` — unique index on `chat_id`
- **Idempotent backfill** from existing `chats_python` rows: groups by `(user_id, chat_id)` where `status=10` and creates one conversations doc per distinct pair, named `"Conversation"` (one-off rename job is out of scope per PR description). Skips any `chat_id` already in `conversations`.
- `down()` drops both indexes (intentionally does not drop the collection — preserves user data on rollback).

### New API endpoints — `/api/chat/conversations`

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/chat/conversations` | List active conversations for the current user, ordered by `last_message_at desc`. Returns `ConversationListResponse` |
| `POST` | `/chat/conversations` | Create a conversation explicitly (rarely needed — the message-send path auto-creates one). Returns `ConversationMeta`, status 201 |
| `PUT` | `/chat/conversations/{chat_id}` | Rename. Body: `{name: str}`. Owner-only |
| `DELETE` | `/chat/conversations/{chat_id}` | Soft-delete (`is_deleted: true`). Owner-only |
| `GET` | `/chat/{chat_id}` | Fetch transcript for a specific conversation. Owner-only |
| `DELETE` | `/chat/{chat_id}` | Clear messages in a specific conversation. Owner-only |

Existing `POST /chat/message` was modified: when `chat_id` is `null` it now **always creates a new conversation** instead of falling back to "the user's latest chat".

All routes apply ownership checks via `user_owns_conversation(chat_id, user_id)`.

### Repository — `app/domains/chat/repository.py`

New functions:
- `list_user_conversations(user_id, limit, before)` — paginated sidebar feed
- `create_conversation(user_id, chat_id, name)` — explicit insert
- `rename_conversation(chat_id, user_id, name)` — owner-scoped update
- `soft_delete_conversation(chat_id, user_id)` — owner-scoped soft delete
- `user_owns_conversation(chat_id, user_id)` — bool ownership check used by every mutating route
- `update_conversation_on_message(chat_id, message_preview)` — bumps `last_message_at`, increments `message_count`, updates the preview

### Service layer — `app/domains/chat/service.py`

**Auto-naming:** when a conversation receives its first user message, the service kicks off a background LLM call to generate a 2–5 word title. Implementation details:

- New module-level prompt `_CONVERSATION_NAME_PROMPT` (Title Case, no punctuation, examples like `"Find flights to Paris" → Flights to Paris`).
- `_GENERIC_TITLE_BLOCKLIST` rejects titles like `"new conversation"`, `"chat"`, `"hello"` — those map to `"Travel Assistant"`.
- For trivial greetings (`"hi"`, `"hello"`, `"thanks"`), the prompt itself returns `"Travel Assistant"`.
- Naming runs async (`asyncio.create_task`) so it never blocks the chat response. Naming failures are caught and logged; the conversation just stays as `"Conversation"`.

### LLM factory — `app/ai/graph/llm_factory.py`

Added one new component:
```python
"conversation_namer": {"provider": "openai", "model": "gpt-5.4-nano"}
```
Cheap & fast — ~50 tokens output, ~$0.00001/call.

### Schema additions — `app/domains/chat/schemas.py`

New Pydantic models:
- `ConversationMeta` — wire shape for sidebar entries
- `ConversationListResponse` — `{conversations: [...], has_more: bool}`
- `CreateConversationRequest` — `{name?: str}`
- `RenameConversationRequest` — `{name: str}`

---

## Frontend changes

### New components

#### `ConversationSidebar.tsx` (386 lines, new)

The left-hand sidebar UI.

- **Date-bucket grouping:** conversations are grouped under `Today` / `Yesterday` / `Previous 7 days` / `Previous 30 days` / `Older`.
- **Active highlight:** the currently-open conversation is visually highlighted.
- **Hover row actions:** rename + delete icons appear on hover.
- **Rename dialog:** modal input with current name pre-filled.
- **Delete dialog:** confirmation modal — soft-delete only.
- **`+ New chat` button:** UI reset only (does not create a DB row).
- **Mobile overlay support:** on screens ≤900px the sidebar floats over the chat with a dimmed backdrop; tapping the backdrop closes it.

#### `useConversations.ts` hook (169 lines, new)

Orchestrates everything sidebar-related:
- `switchConversation(chat_id)` — loads history, updates Redux `chatId`, hides welcome
- `createNewConversation()` — UI-only: clears messages, resets `chat_id` to null, shows welcome + suggestion chips
- `renameConversation(chat_id, name)` — RTK Query mutation + cache invalidation
- `deleteConversation(chat_id)` — soft-delete; if the deleted conversation was active, falls back to the next-most-recent or to a fresh "new chat" state

### Updated components

#### `LayoutWithChat.tsx` (+126 lines)

Embeds the sidebar on the `/chat` route for authenticated users only. After the merge with main:
- Outer layout uses Mantine `Flex` (consistent with main's hybrid Mantine+MUI direction)
- Sidebar overlay/backdrop and absolute-positioned mobile sidebar
- Hamburger toggle (MUI `IconButton` + `MenuIcon`) appears in the top-left when the sidebar is collapsed on `/chat`
- `useMediaQuery('(max-width: 900px)')` from `@mantine/hooks` (matches MUI's `md` breakpoint) drives mobile behaviour
- `SearchParamsBar` from main is preserved above the chat area on non-`/chat` routes

#### `ChatContext.tsx` (+49 lines)

- Threads `chat_id` through `sendMessage`
- Loads per-conversation history on switch
- Includes a guard that prevents the history fetch from wiping live welcome / suggestion-chip messages (the chips are local UI state, not server-side messages)

#### `chatSlice.ts` (+124 lines)

New state fields:
- `conversations: ConversationMeta[]`
- `conversationsLoaded: boolean`
- `conversationSidebarOpen: boolean` (default `true`)

New reducers:
- `setConversations` — replaces full list (from sidebar refetch)
- `addConversation` — upsert (used when first message creates a conversation server-side)
- `removeConversation` — soft-delete from local state
- `toggleConversationSidebar`, `setConversationSidebarOpen`

Existing reducers got minor adjustments to interact with the new fields cleanly.

#### `applySuccessfulChatResponse.ts` (+27 lines)

When a `POST /chat/message` response comes back with a new `chat_id` (server auto-created the conversation), this util now also dispatches `addConversation` so the sidebar updates instantly without waiting for a refetch.

### RTK Query — `chatApi.ts`

Added endpoints + auto-generated hooks:
- `listConversations` → `useListConversationsQuery`
- `createConversation` → `useCreateConversationMutation`
- `renameConversation` → `useRenameConversationMutation`
- `deleteConversation` → `useDeleteConversationMutation`

`baseApi.ts` got a new tag type `Conversations` for cache invalidation.

### Type additions — `types/chat.ts`

```ts
interface ConversationMeta {
  chat_id: string;
  name: string;
  message_count: number;
  last_message_at: string;
  last_message_preview: string;
  created_at: string;
  updated_at: string;
}
```
Plus list/request/rename DTOs that mirror the backend Pydantic models.

---

## Tests

### Backend (Python)

| File | Coverage |
|---|---|
| `tests/unit_tests/test_domains/test_chat_conversations.py` (505 lines, **new**) | Repository ownership filtering, list pagination, create / rename / soft-delete happy paths, owner-mismatch rejection, edge cases (empty user, deleted-then-listed) |
| `tests/unit_tests/test_database/test_migration_006_create_conversations_collection.py` (313 lines, **new**) | `up()` index creation + idempotent backfill, `down()` index drop, defensive paths (existing collection, missing chats, partial backfill) |
| `tests/unit_tests/test_domains/test_chat_auto_save_itinerary.py` (+23 lines) | Updated with an autouse fixture patching the new conversation-metadata calls so existing itinerary auto-save tests still pass |
| `tests/unit_tests/test_ai/test_graph/test_supervisor_v2.py` (+6 lines) | TTL test updated for the new 30-day checkpoint lifetime |

41 backend chat-related tests pass after the merge.

### Frontend (TypeScript)

| File | Coverage |
|---|---|
| `features/chat/components/PublicChatRouteGate.test.tsx` (+3 lines) | Adapted to new `ChatState` shape |
| `features/landing/components/NavbarHome.test.tsx` (+3 lines) | Same — added `conversations` / `conversationsLoaded` / `conversationSidebarOpen` to fixtures |
| `features/onboarding/useStartPlanning.test.tsx` (+3 lines) | Same |
| `features/routing/PublicRoute.test.tsx` (+3 lines) | Same |

`tsc --noEmit` clean. Vitest run on touched files: 28 pass.

---

## What's intentionally out of scope

These are listed in the PR description as deferred follow-ups:

- Search over conversations
- Pinning / archiving
- Shared conversations
- Hard delete / GDPR wipe
- One-off rename job for backfilled `"Conversation"` rows (admin tool)
- Optimistic UI for rename / delete
- E2E Playwright coverage

---

## Today's session — main merge + conflict resolution

`ec2b06e6` brought in 423 main-side commits (PR #1009 support chat, weekly trace review, and others). Three conflicts resolved by keeping both feature additions:

| File | Resolution |
|---|---|
| `app/domains/chat/service.py` | Kept HEAD's auto-naming prompt + blocklist **and** main's anti-spam dedup cache (`_DEDUPE_WINDOW_SECONDS`, `_recent_messages`, `_is_duplicate_resend`). They're independent module-level features |
| `frontend-v2/src/api/baseApi.ts` | Kept all three new RTK Query tag types: `Conversations` (HEAD), `AdminDiscounts`, `AdminDiscountBatches` (main) |
| `frontend-v2/src/components/layout/LayoutWithChat.tsx` | Wove HEAD's sidebar + hamburger logic into main's Mantine `Flex` rewrite. Replaced `useMediaQuery`/`useTheme` from MUI with `useMediaQuery('(max-width: 900px)')` from `@mantine/hooks`. Kept MUI `IconButton`/`MenuIcon` for the hamburger toggle (consistent with the chat module's MUI surface). Preserved main's new `SearchParamsBar` header for non-chat routes |

Backfilled the new `ChatState` fields in two main-side test files (`NavbarHome.test.tsx`, `useStartPlanning.test.tsx`) so `tsc` stayed clean.

**Verification after merge:**
- `ruff check` + `ruff format --check` clean on touched backend files
- `tsc --noEmit` clean across the frontend
- Backend chat tests: 41 pass
- Frontend tests on the two resolved files: 28 pass

---

## Files modified (full list)

**Backend (12 files)**
```
app/ai/graph/base.py                                                         +2 / −1
app/ai/graph/llm_factory.py                                                  +1
app/api/chat.py                                                            +210
app/database/migrations/006_create_conversations_collection.py             +117 (new)
app/domains/chat/repository.py                                             +137
app/domains/chat/schemas.py                                                 +49
app/domains/chat/service.py                                                +108
tests/unit_tests/test_ai/test_graph/test_supervisor_v2.py                    +6
tests/unit_tests/test_database/test_migration_006_create_conversations_collection.py  +313 (new)
tests/unit_tests/test_domains/test_chat_auto_save_itinerary.py              +23
tests/unit_tests/test_domains/test_chat_conversations.py                   +505 (new)
```

**Frontend (15 files)**
```
src/api/baseApi.ts                                                           +1
src/api/chatApi.ts                                                          +64
src/api/index.ts                                                             +5
src/components/layout/LayoutWithChat.tsx                                   +126
src/features/chat/components/ConversationSidebar.tsx                       +386 (new)
src/features/chat/components/PublicChatRouteGate.test.tsx                    +3
src/features/chat/components/index.ts                                        +1
src/features/chat/context/ChatContext.tsx                                   +49
src/features/chat/hooks/index.ts                                             +1
src/features/chat/hooks/useConversations.ts                                +169 (new)
src/features/chat/utils/applySuccessfulChatResponse.ts                      +27
src/features/landing/components/NavbarHome.test.tsx                          +3
src/features/onboarding/useStartPlanning.test.tsx                            +3
src/features/routing/PublicRoute.test.tsx                                    +3
src/store/slices/chatSlice.ts                                              +124
src/types/chat.ts                                                           +25
```

---

## Acceptance / smoke-test checklist

From the PR description, verified working:

- [x] Fresh login with no conversations → welcome + suggestion chips, no sidebar entries, `chat_id` is `null`
- [x] Send first message → conversation appears in sidebar, `chat_id` is set, auto-generated title arrives within 1–2s
- [x] Click **New chat** → sidebar unchanged, welcome shown, `chat_id` resets to `null`
- [x] Send a second message → a new conversation row appears in the sidebar
- [x] Click an older conversation → history loads, subsequent messages go to that thread
- [x] Rename / delete via the sidebar menu
- [x] Agent memory does not leak across conversations (Paris in conv A, Tokyo in conv B starts fresh)
- [x] Welcome + suggestion chips persist after the first response
- [x] Backend unit tests pass
- [x] Migration 006 applies cleanly and is idempotent on a DB with existing chats

---

## Branch commits

```
ec2b06e6  Merge remote-tracking branch 'origin/main' into 749-feature-multi-conversation-chat-with-sidebar  (today)
30ce5147  style(chat): ruff format migration 006 test file
e46d39a5  fix(chat): address PR review — route order, ownership check, migration tests
8989b6aa  Merge branch 'main' into 749-feature-multi-conversation-chat-with-sidebar
52a7ffbf  feat(chat): multi-conversation chat with sidebar (#749)
```

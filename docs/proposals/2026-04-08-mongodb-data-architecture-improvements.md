# MongoDB Data Architecture Improvements

> **Companion to:** [2026-04-08-mongodb-schema.md](2026-04-08-mongodb-schema.md)
> **Status:** Proposal (no code changes yet)
> **Last Updated:** 2026-04-08

## Why this document exists

We're about to start syncing the production MongoDB to BigQuery (hourly) so the team can build analytics, marketing dashboards, and feed audiences to ActiveCampaign / Google Ads / Meta. While inspecting the database we found a number of data quality issues that:

1. **Block efficient incremental sync.** Without reliable `updated_at` fields and indexes on them, every sync has to be a full snapshot, which gets expensive once collections grow.
2. **Make analytics queries fragile.** Field naming is inconsistent across writers (Mongoose vs Python) and even within a single collection. Queries break in surprising ways.
3. **Bloat the database with dead data.** Roughly 32,000 LangGraph V1 checkpoint documents and ~1,100 documents in 7 orphaned collections sit untouched, increasing backup size and slowing collection scans.

This doc proposes a set of fixes, prioritised by impact. None of it is urgent enough to block the BigQuery sync (we'll start with full snapshots), but every item below pays for itself the moment we want to move to incremental, scale up, or trust analytics output.

For the raw findings (per-collection schema, doc counts, indexes, timestamp field presence), see [2026-04-08-mongodb-schema.md](2026-04-08-mongodb-schema.md).

---

## Migration timeline (the context that explains the rest of this doc)

Most of the schema weirdness in this database has a simple historical explanation: Voya's backend was rewritten from Node.js (Mongoose, camelCase) to Python (motor/pymongo, snake_case) in **late August 2025**, and the artefacts of that migration are still visible in the data.

| Event | When | Evidence |
|---|---|---|
| Last Mongoose write to `users` (`__v` marker) | 2025-08-22 | Latest doc with `__v` |
| Last camelCase create on `users` | 2025-08-27 | Latest doc with `createdAt` field |
| First snake_case create on `users` | 2025-08-31 | Earliest doc with `created_at` field |
| Last write to legacy `chats` (Mongoose) | 2025-09-02 | Latest doc by `_id` |
| First write to `chats_python` | 2025-09-09 | Earliest doc |
| Last write to `trips` (legacy Mongoose) | 2025-08-18 | Frozen since |
| Last write to `search_history` | 2025-08-29 | Frozen since |
| n8n integration ripped out | 2026-01-16 | Both `n8n_integration_logs` and `itinerary_sessions` last write same day |
| LangGraph V1 → V2 supervisor cutover | ~2026-03-18 | Last writes to V1 checkpoint collections |

**Implications:**

- **There is no active Mongoose / Node.js writer.** Old camelCase data exists, but it's frozen — no new writes and no in-place updates from Node code. This dramatically simplifies the cleanup story (it's a backfill, not a hunt for a rogue writer).
- **All "orphaned" collections have a clean cutoff date.** None of them have been written to in the last 80+ days. Confirmation that they can be archived or dropped is straightforward.
- **The LangGraph V1 cleanup is recent.** V1 checkpoint collections were the active production system as recently as ~3 weeks ago. The 31,797 documents represent the previous architecture, not crusty technical debt — but they're now safe to drop.

---

## Issues, ranked

### 🟠 High: `users` collection has 67 pre-migration users with camelCase-only fields (one-time backfill)

The `users` collection has two distinct cohorts due to the August 2025 Node→Python migration:

```
Total: 249 users
ONLY createdAt (camelCase only):  67   ← pre-migration cohort, never updated since
ONLY created_at (snake_case):    181   ← created post-migration by Python
BOTH:                              0   ← no document has both
NEITHER:                           1   ← edge case (probably an admin-created user)
```

A similar split applies to other field pairs (`firstName`/`first_name`, `lastName`/`last_name`, `googleId`/`google_id`, `lastLogin`/`last_login`, `profileImage`/`profile_image`).

For `updatedAt`/`updated_at` the pattern is slightly different:

```
ONLY updatedAt (camelCase):      61
ONLY updated_at (snake_case):   167
BOTH (mixed):                    20   ← old users that got touched by Python after migration
```

The 20 "BOTH" docs are pre-migration users whose record was later updated by Python (e.g. a profile change or last_login refresh). Python wrote a new `updated_at` but didn't remove the legacy `updatedAt` left over from Mongoose.

**This is NOT an active dual-writer problem.** The Mongoose code path stopped writing on 2025-08-22 (last `__v`) / 2025-08-27 (last camelCase create). Only 9 docs ever had `__v`, and the latest one is from 2025-08-22. **There is no rogue writer to find and stop.** This is a one-time backfill problem.

**Why it still matters (analytics correctness):**

- Any query like `SELECT COUNT(*) FROM users WHERE created_at > '2025-01-01'` would silently undercount by ~67 users (the entire pre-migration cohort), because their creation timestamp is in `createdAt`, not `created_at`.
- Marketing analytics segmentation by signup date would treat 27% of the user base as if they didn't exist.
- For incremental sync, the impact is actually **near zero**: the 67 frozen users haven't been touched since August 2025, so they wouldn't qualify for any incremental window anyway. They just need to be loaded once during the initial backfill.
- The 20 BOTH docs need a decision: are we keeping `updatedAt` or `updated_at` as authoritative? The values may differ if Python touched the record post-migration.

**Action:** one-time migration script:

1. For the 67 docs with only camelCase fields: copy values into snake_case equivalents (`createdAt` → `created_at`, `firstName` → `first_name`, etc.), then unset the camelCase fields.
2. For the 20 docs with both `updatedAt` and `updated_at`: take `MAX(updatedAt, updated_at)` (whichever is more recent), write it to `updated_at`, unset `updatedAt`.
3. For the 9 docs with `__v`: unset.
4. Repeat for any other field pairs (`firstName`/`first_name`, etc.).
5. Verify with a query that no user has any camelCase remnant.

This should fit in a single migration script under 50 lines. Risk: low (read-modify-write on 67-87 documents). Effort: a few hours including testing.

---

### 🔴 Critical: No consistent timestamp convention across collections

The 12 active collections use **four different timestamp conventions**:

| Convention | Used by |
|---|---|
| `created_at` + `updated_at` (snake_case) | `agent_prompts`, `booking_sessions`, `chat_feedback`, `sessions`, `transactions`, `user_preferences` |
| `created_at` only (insert-only) | `chats_python` |
| `timestamp` (single field) | `booking_events` |
| Mixed Mongoose + Python (legacy data only) | `users` (pre-migration cohort, see issue above) |
| _(none)_ | `chat_locks`, LangGraph checkpoint collections (use TTL on different fields) |

**Why this is critical:**

- Incremental sync needs a single, predictable field per collection. Today every collection requires custom handling.
- Querying "everything that changed since X" across collections requires per-collection logic.
- New collections inherit whatever convention the developer happened to remember.

**Action:** adopt a project-wide standard. Recommendation:

1. **Every collection MUST have `created_at` and `updated_at` fields**, both in snake_case, both `datetime` (UTC).
2. **Both fields are set on insert**; `updated_at` is touched on every update.
3. **`updated_at` is set server-side**, not from client-supplied data, to avoid clock skew breaking ordering.
4. Existing collections that use other conventions (`booking_events.timestamp`, `users.createdAt`) get migrated to the standard, with backwards-compatible reads during the transition.
5. Document the convention in `backend_python/CLAUDE.md` (or wherever the Python coding standards live) so new collections inherit it.

This change unlocks generic incremental sync for *all* collections without per-collection special cases.

---

### 🟠 High: Missing indexes on production-load collections

Several active collections have **zero custom indexes** (only the default `_id_`), despite carrying the bulk of the production data:

| Collection | Doc count | Custom indexes |
|---|---:|---:|
| `users` | 248 | 0 |
| `chats_python` | 7,127 | 0 |
| `agent_prompts` | 3 | 0 |
| `booking_sessions` | 497 | 0 |
| `chat_feedback` | 4 | 0 |
| `transactions` | 23 | 0 |
| `user_preferences` | 3 | 0 |

**Why this is high severity:**

- Any query filtering `chats_python` by `chat_id`, `user_id`, or `created_at` does a full collection scan today. With 7,127 docs the query may still complete in milliseconds, but the cost grows linearly.
- Lookups by `email` on `users` are unindexed (and `email` should also be `unique`). This is a security and correctness issue, not just performance.
- Once we move to incremental sync, every sync run will need to query `WHERE updated_at > ?`. Without an index this is O(N) per sync.

**Action:** add the indexes documented in the next section. None of these are large or risky to add (the collections are small).

**Recommended index baseline**:

```javascript
// users (and any future user-keyed collection)
db.users.createIndex({ email: 1 }, { unique: true })
db.users.createIndex({ updated_at: -1 })
db.users.createIndex({ status: 1 })
db.users.createIndex({ created_at: -1 })

// chats_python (queried by chat session, user, and time)
db.chats_python.createIndex({ chat_id: 1, created_at: -1 })
db.chats_python.createIndex({ user_id: 1, created_at: -1 })
db.chats_python.createIndex({ updated_at: -1 })  // for incremental sync once added

// booking_sessions
db.booking_sessions.createIndex({ user_id: 1 })
db.booking_sessions.createIndex({ updated_at: -1 })

// transactions (money: index everything sane)
db.transactions.createIndex({ user_id: 1, created_at: -1 })
db.transactions.createIndex({ status: 1 })
db.transactions.createIndex({ stripe_payment_intent_id: 1 }, { unique: true, sparse: true })
db.transactions.createIndex({ updated_at: -1 })

// user_preferences
db.user_preferences.createIndex({ user_id: 1 }, { unique: true })
db.user_preferences.createIndex({ updated_at: -1 })

// chat_feedback
db.chat_feedback.createIndex({ user_id: 1, created_at: -1 })
db.chat_feedback.createIndex({ message_id: 1 })
db.chat_feedback.createIndex({ updated_at: -1 })
```

---

### 🟠 High: User foreign keys are stored as `str`, not `ObjectId`

In `chats_python` and `booking_events`, the `user_id` field is a `str`, not an `ObjectId`. The canonical `users._id` is an `ObjectId`.

**Why this matters:**

- Joins require explicit type coercion: `WHERE user_id = ObjectId(...).str()` is needed everywhere.
- BigQuery joins between the synced `users` table (where `_id` is a hex string from `ObjectId`) and `chats_python` (where `user_id` is a regular string) only work if both are normalised to the same string format.
- In MongoDB itself, you can't `$lookup` cleanly between these collections without an aggregation that converts types.

**Action:**

1. Confirm whether the string is the hex representation of the ObjectId, or some other identifier (e.g. an external auth provider id). If hex, change the writers to store `ObjectId` directly.
2. If conversion is impractical, document the convention clearly so the BigQuery loader knows to normalise both sides.

---

### 🟠 High: 32,000 documents in 8 legacy LangGraph V1 checkpoint collections

Eight legacy LangGraph V1 collections sit in production with no active writes. The V1 → V2 supervisor cutover happened in mid-March 2026, and the collections are listed for cleanup in `app/ai/graph/supervisor_v2.py` (`_AGENT_CHECKPOINT_COLLECTIONS` and `_AGENT_WRITES_COLLECTIONS`), but no job actually deletes them:

| Collection | Doc count | Last write |
|---|---:|---|
| `checkpoint_writes` | 17,188 | 2026-03-18 |
| `checkpoints` | 5,362 | 2026-03-18 |
| `flight_checkpoint_writes` | 4,426 | 2026-03-18 |
| `flight_checkpoints` | 2,384 | 2026-03-18 |
| `hotel_checkpoint_writes` | 1,137 | 2026-03-17 |
| `hotel_checkpoints` | 658 | 2026-03-17 |
| `general_checkpoint_writes` | 348 | 2026-03-19 |
| `general_checkpoints` | 294 | 2026-03-19 |
| **Total** | **31,797** | _last write across all: 2026-03-19_ |

**Context:** these aren't crusty technical debt — they were the active production system as recently as ~3 weeks ago. The data represents accumulated agent state from December 2025 through mid-March 2026 (roughly 3 months of conversations). LangGraph V2 (`supervisor_v2_checkpoints` / `supervisor_v2_checkpoint_writes`) took over in mid-March and runs cleanly with a 24h TTL.

**Why dropping them is now safe:**

- ~3 weeks of zero writes is strong evidence the V2 cutover is complete and stable.
- The data has no analytics value (it's serialised LangGraph internal state, not user actions).
- Backups still exist if anything needs to be recovered.

**Action:** drop the 8 collections. Recommended sequence:

1. **Sanity check first**: re-run the timeline query to confirm no new writes have arrived since 2026-03-19. If all collections are still frozen, proceed.
2. Drop the 8 collections. Reversible from backup.
3. Remove the cleanup-marker constants from `supervisor_v2.py`.

Effort: under an hour. Risk: very low (no active reads or writes).

---

### 🟡 Medium: 7 orphaned collections, all confirmed dead

These collections exist in production but have **no active writers**. Confirmed by checking the `_id` timestamp of the most recent document in each:

| Collection | Doc count | Last write | Days dead | Likely owner |
|---|---:|---|---:|---|
| `n8n_integration_logs` | 580 | 2026-01-16 | 82 | n8n workflow (now removed) |
| `itinerary_sessions` | 123 | 2026-01-16 | 82 | n8n workflow (now removed) |
| `chats` | 330 | 2025-09-02 | 218 | Mongoose (legacy Node.js) |
| `search_history` | 73 | 2025-08-29 | 222 | Mongoose (legacy Node.js) |
| `trips` | 20 | 2025-08-18 | 233 | Mongoose (legacy Node.js, has `__v`) |
| `travel_events` | 1 | 2025-08-17 | 234 | Mongoose (legacy Node.js, designed but never used) |
| `chathistories` | 0 | _(empty)_ | n/a | Mongoose (legacy Node.js) |

**Two distinct cohorts:**

1. **Mongoose-era collections** (5): `chats`, `search_history`, `trips`, `travel_events`, `chathistories`. All last touched in August/September 2025, around the Node→Python migration. Safe to drop.
2. **n8n integration collections** (2): `n8n_integration_logs` and `itinerary_sessions`. Both last written on **the same day**: 2026-01-16. This is a smoking gun: an n8n workflow was disabled or removed on that day, and these collections have been receiving no writes since (~3 months as of writing). The collections are documented in `docs/STAGING_MONGODB_SETUP.md` as written by n8n directly, which fits this story.

**Why this still matters:**

- We don't want to waste BigQuery sync effort on these collections. Skip them entirely.
- Indexes on empty/dead collections still cost write performance if writes ever resume (none today).
- Carrying dead data around bloats backups.

**Action:**

1. **Confirm with whoever runs n8n** (likely Aneeq) that the n8n itinerary integration was indeed removed in mid-January, and that the collections won't be revived.
2. **Export each collection to JSON** as an archive (storage is cheap, regret is expensive).
3. **Drop all 7 collections** in one batch. Reversible from the JSON archives if needed.
4. Remove `chats` constant from `app/database/constants.py:9`.
5. Remove the `trips_created` counter stub from the `users` schema (it never went anywhere meaningful).

Risk: very low. None of these collections have had a write in months, and most are nearly a year dead.

---

### 🟡 Medium: Schema drift inside collections

Several active and orphaned collections show fields with **multiple types** across sampled documents (a clear sign of schema evolution without migration):

- `users.firstName`: `str | null`
- `users.lastName`: `str | null`
- `users.password_hash`: `str | null`
- `trips.destination`: `dict | str` (sometimes a structured object, sometimes a plain string)
- `trips.travelers`: `dict | null`
- `trips.itinerary`: `list[dict] | list[empty]`
- `trips.itinerary[].events[].lat`: `float | int`
- `chats_python` is mostly clean

**Why this matters:**

- BigQuery types are strict. Loading a document where `destination` is sometimes a string and sometimes a struct requires either two columns or a JSON catch-all.
- Application code has to defensively check types everywhere.

**Action:** for each multi-type field, decide what the canonical type is and write a migration to normalise the documents. For new code, add Pydantic validators that reject the wrong type at write time.

---

### 🟢 Low: Reserved keyword used as field name

`chats_python.from` collides with the SQL `FROM` keyword and Python's `from` keyword. The Python code already aliases it as `from_` in the model layer (per the agent investigation), but the field on disk is still `from`.

**Action:** rename to `from_user` or `sender` in a future migration. Until then, document the alias clearly so the BigQuery loader knows to rename it during transformation.

---

### 🟢 Low: Booking events use `timestamp` instead of `created_at`

`booking_events` uses a single `timestamp` field instead of the standard `created_at`/`updated_at` pair. Since this collection appears to be append-only (per the code investigation), `created_at` would be a synonym for `timestamp` here, but the inconsistent naming forces special-case handling.

**Action:** rename `timestamp` → `created_at` (and decide whether `updated_at` is needed). Backwards compatible: can be done via dual-write for one release, then drop `timestamp`.

---

## Proposed standard for new collections going forward

To keep this from happening again, document a standard in `backend_python/CLAUDE.md` (or wherever Python conventions live):

### Field naming
- All field names: `snake_case`. No exceptions for new fields.
- Foreign keys to `users._id` are stored as `ObjectId`, named `user_id`.
- Timestamps: `created_at`, `updated_at` (always both, always UTC `datetime`, always set server-side).

### Required fields on every document
- `_id` (ObjectId, default)
- `created_at` (set on insert)
- `updated_at` (set on insert AND on every update)

### Required indexes on every collection
- `{ updated_at: -1 }` (for incremental sync and recency queries)
- `{ user_id: 1, created_at: -1 }` if user-keyed (covers user history queries)
- Domain-specific indexes as needed

### Naming conventions for collections
- `snake_case` (matches existing Python collections)
- No `_v2` suffixes — version via explicit versioning fields if needed (the LangGraph V1/V2 mess is what happens otherwise)

### Reserved-word avoidance
- Don't use SQL or Python reserved words as field names (`from`, `to`, `select`, `where`, `order`, `group`, `class`, `type`, etc.). When unavoidable, use a prefix: `from_user`, `to_user`, `event_type`, `booking_class`.

---

## Migration plan (suggested order)

### Phase 1 — Quick wins (0.5-1 day)
1. **Add the missing indexes** on the 7 active collections (snippet under the missing-indexes issue above). Risk: low. Time: 30 minutes.
2. **Drop the 8 LangGraph V1 collections** after re-confirming no writes since 2026-03-19.
3. **Drop the 7 orphaned collections** after a JSON archive export. Confirm n8n ownership question with Aneeq first.

### Phase 2 — Data migration (2-3 days)
4. **Backfill the 67 + 20 + 9 pre-migration users** to consolidated snake_case schema. One migration script.
5. **Standardise timestamp fields** across collections that don't follow the convention (`booking_events.timestamp` → `created_at`).
6. **Convert string `user_id` to `ObjectId`** in `chats_python` and `booking_events`.
7. **Normalise the remaining multi-type fields** (most of them collapse on their own once the users backfill is done).

### Phase 3 — Hardening (ongoing)
8. **Document standards** in `backend_python/CLAUDE.md`. (See above section)
9. **Add Pydantic validators** that enforce timestamp convention on every model.
10. **Add a CI check** that fails if new collections are created without the required indexes (optional, can be a periodic audit instead).

---

## What this means for the BigQuery sync project

The BigQuery sync **doesn't need to wait** for any of these fixes. We start with full hourly snapshots, which work regardless of timestamp conventions or indexes. Volumes are tiny (the entire active database is a few hundred MB), and full snapshots will be cheap.

However, the value of fixing these issues is:

1. **Once Phase 2 is done**, we can switch the sync to incremental mode. Sync time drops from "snapshot the whole collection" to "fetch documents touched in the last hour", which scales much better as the database grows.
2. **Once the users backfill is done** (Phase 2 step 1), the analytics in BigQuery become trustworthy. Today, `SELECT COUNT(*) FROM users WHERE created_at > '2025-01-01'` would silently undercount by 67 users (the entire pre-migration cohort).
3. **After Phase 1**, the sync isn't dragging ~33,000 dead documents (LangGraph V1 + orphaned collections) into BigQuery on every run.

A reasonable plan: **start the BigQuery sync now in full-snapshot mode** (skipping the dead collections from day one), and treat Phase 1 of this document as a parallel cleanup track that closes within a week. Phase 2 then unlocks incremental sync mode, but isn't time-critical.

---

## Open questions for the team

A few of the original questions have been answered by inspecting `_id` timestamps on production data. Here's what's left:

1. **n8n itinerary integration cleanup confirmation.** Both `n8n_integration_logs` and `itinerary_sessions` last received a write on 2026-01-16 (same day). This strongly suggests an n8n workflow was disabled/removed that day. **Question for Aneeq:** can you confirm the n8n itinerary integration was indeed removed in mid-January, and that these collections are safe to drop?
2. **Canonical user identifier in `chats_python` and `booking_events`.** Is the `user_id` field the hex string of `users._id`, or some other ID (e.g. an external auth provider id)? This determines whether we migrate to `ObjectId` or document the join.
3. **20 mixed `updatedAt`/`updated_at` users.** When backfilling, do we trust the camelCase `updatedAt` value (could be stale, last touched by Mongoose) or the snake_case `updated_at` (post-migration Python writes)? Default proposal: take `MAX(updatedAt, updated_at)`. Confirm.
4. **Pre-migration users with no recent activity.** 67 users haven't been touched since August 2025. Some may be test accounts, abandoned signups, or genuinely inactive. When we migrate them, do we want to also flag them as `status=inactive`, or just rename their fields and leave them as-is? Marketing impact: are we including them in audience syncs?

**Already answered (by inspecting production):**

- ~~Who still writes to `users` in camelCase?~~ → No one. Last Mongoose write was 2025-08-22 (`__v` field), last camelCase create was 2025-08-27. The dual-schema is purely historical.
- ~~Is `chats` (Mongoose) truly dead?~~ → Yes. Last write 2025-09-02. Confirmed.
- ~~Anything still writing to the legacy LangGraph V1 collections?~~ → No. All last writes were 2026-03-17 to 2026-03-19. ~3 weeks of zero activity confirms the V2 cutover is stable.

---

## Effort estimate

| Phase | Effort | Risk | Owner |
|---|---|---|---|
| Phase 1 (quick wins: indexes + drop dead collections) | 0.5-1 day | Low | Backend dev |
| Phase 2 (data migration: users backfill + standardisation) | 2-3 days | Low-medium | Backend dev |
| Phase 3 (hardening + standards) | 0.5 day + ongoing | Low | Backend dev |
| **Total** | **~3-5 days** | | |

These estimates are lower than my original guess because the timeline analysis collapsed the two biggest unknowns (rogue Mongoose writer, n8n collection ownership) into already-answered questions. The biggest remaining unknown is the migration script for the 67 + 20 + 9 user records, which is a contained piece of work.

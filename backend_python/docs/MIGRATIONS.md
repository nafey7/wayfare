# MongoDB Migration Runner

Lightweight async migration runner for the Voya backend. Replaces ad-hoc scripts with discoverable, ordered, tracked migrations.

## Quick Reference

```bash
python -m app.database.migrate           # Run pending migrations
python -m app.database.migrate --dry-run # List pending without executing
```

## Migration File Convention

**Location**: `app/database/migrations/`

**Naming**: `NNN_description.py` or `YYYYMMDD_NNN_description.py` (timestamp prefix recommended to avoid merge conflicts)

**Structure**:
```python
async def up(db):
    """Apply migration. Must be idempotent."""
    ...

async def down(db):
    """Optional: revert migration."""
    pass
```

- `db`: `AsyncIOMotorDatabase` (same as `get_connection().get_database()`)

**`down()` contract**:

- The runner **never calls `down()`** today. Only `up()` is invoked automatically.
- Migrations should still include `down()` where a rollback path exists (e.g., dropping an index or reverting a schema change).
- It is the **developer's responsibility** to invoke `down()` manually if a rollback is needed (e.g., via a one-off script or ECS task).

## Requirements

1. **Idempotent**: Safe to run multiple times. Half-finished retries must not corrupt data.
2. **Non-interactive**: No prompts or user input.
3. **Backwards-compatible**: Must not break currently running code. Rolling deploys mean old and new code coexist briefly. Use two-phase deploys for breaking changes.

## Unit tests for migrations

Add or extend **unit** tests under `tests/unit_tests/test_database/` (e.g. `test_migration_NNN_*.py`) that load the migration module with `importlib` (same pattern as existing migration tests). Use `AsyncMock` / `MagicMock` for `db` and collections—no real MongoDB.

**`up()`**

- Assert the migration calls the expected collection API (e.g. `create_index` awaited once).
- For index migrations, assert the **full key spec** (first positional argument), not only `name=` or “was called”. Wrong field order or keys should fail the test.
- Include relevant **kwargs** (`name`, `unique`, `sparse`, etc.) that the migration passes through.

**`down()`**

- Cover the **success** path: e.g. `drop_index(name)` awaited with the expected index name.
- If `down()` **catches** `pymongo.errors.OperationFailure` (or similar) for idempotent rollback (e.g. index already dropped), add a test where the mocked `drop_index` raises that failure—e.g. MongoDB **code 27** (IndexNotFound) or the `"index not found"` message path your code treats as safe—and assert `down()` does **not** re-raise.

## Imports in migration modules (avoid circular dependencies)

Migration files are loaded with `importlib` **before** the full app stack is initialized. Importing from `app.domains.*` (or other packages whose `__init__.py` pulls services, repositories, or models) can trigger **circular imports** at migration load time and fail deploys (e.g. `ImportError: cannot import name 'BookingService' from partially initialized module 'app.domains.bookings'`).

**Do:**

- Prefer constants from shallow modules such as `app.database.constants` when they already exist.
- **Inline** stable literals when needed: collection names, index names, enum string values that must match domain definitions.
- For index specs that duplicate `ensure_*_indexes` in a repository, **duplicate** the `create_index` calls in the migration and add a comment: *keep in sync with* the canonical function.

**Do not:**

- `from app.domains...` in migration modules (including “just” importing a constant from `app.domains.foo.constants` if that package’s `__init__` imports services).

If you change the canonical enum, constant, or `ensure_*_indexes` helper, update any duplicated literals in migrations in the same PR when applicable.

## Tracking

- **Collection**: `_migrations`
- **Schema**: `{_id: "001_description", applied_at: datetime}`
- Presence = applied. Absence = pending. No "in progress" state; record only on success.

## CI/CD Integration

Migrations run as a separate ECS job **before** the service update:

1. Build & push new image
2. **Migrate** (one-off ECS task with new image, command `python -m app.database.migrate`)
3. Deploy (update ECS service)

Workflows: `deploy-staging.yml`, `deploy-prod.yml` (both call `run-migrations.yml` for the migrate step)

## Retrofit: Mark Existing Migrations as Applied

**Numbering gap (001)**: Migration `001_clear_booking_events` was intentionally removed before the runner shipped: it was destructive and would have re-run on first deploy. The first migration in the tree is therefore `002_set_myvoya_admin_role`. Future readers can ignore the gap.

For environments where migrations were run manually before the runner existed, mark them as applied so the runner skips them:

```javascript
// In MongoDB shell or Compass
db._migrations.insertOne({ _id: "002_set_myvoya_admin_role", applied_at: new Date() })
```

Run once per environment (staging, production) that already had these migrations applied.

## Concurrency Protection

The runner uses a MongoDB advisory lock (`_migration_lock` collection) to prevent concurrent migration runs. If two deploys overlap (e.g., quick tag push while staging auto-deploys), only one runner will acquire the lock; the other exits with an error. The lock has a 10-minute TTL and auto-expires if the holder crashes.

## Migration Logs (CI/CD)

Migration stdout/stderr runs inside the ECS task. Logs are sent to CloudWatch using the same log group as the main app (from the task definition). If the migrate job fails, the workflow fetches and prints the migration logs; otherwise, view them in AWS CloudWatch (log group: `/ecs/<env>-voya-backend`).

## Safety Rules

- All migrations must be **backwards-compatible** with currently running code
- Breaking changes use a **two-phase approach** across two deploys:
  1. Deploy 1: Add new schema/code that supports both old and new
  2. Deploy 2: Remove old schema/code after migration

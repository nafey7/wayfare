# Voya CMS (Strapi)

Strapi 5 CMS for Voya. Source lives in this monorepo, deploys independently to ECS.

## Stack

- Strapi 5.40.0 (Node 20)
- PostgreSQL 16 (RDS in cloud, Docker locally)
- Media: AWS S3 + CloudFront (cloud), local filesystem (dev)
- Email: SendGrid (cloud), disabled locally
- MCP plugin (dev only) — exposes content types to AI tools

## Local development

From the repo root:

```bash
docker compose up -d strapi strapi-db
```

- Admin panel: http://localhost:1337/admin
- First run: register an admin user, then build content types
- Postgres: `localhost:5433` (creds in [compose.dev.yaml](../compose.dev.yaml))
- Hot reload: edits to `cms/src/` trigger restart automatically

To run outside Docker, copy [.env.example](.env.example) → `.env`, fill in secrets (`openssl rand -base64 32`), then `npm install && npm run develop`.

## Development workflow

Strapi schema changes can **only** be made in development mode. Production runs `strapi start`, which hides the Content-Type Builder entirely. The flow is therefore:

1. **Edit locally** at http://localhost:1337/admin → Content-Type Builder
2. **Strapi writes files** into `cms/src/`:
   - `src/api/{name}/content-types/{name}/schema.json` — the schema
   - `src/api/{name}/controllers/{name}.js`, `routes/{name}.js`, `services/{name}.js` — auto-generated handlers
   - `src/components/{category}/{name}.json` — reusable components
3. **Regenerate types and OpenAPI spec** — `docker compose exec strapi npm run generate`
4. **Commit those files** — `git add cms/src/ cms/types/generated/`
5. **Push to `main`** — auto-deploys to staging via [.github/workflows/deploy-strapi-staging.yml](../.github/workflows/deploy-strapi-staging.yml) when `cms/**` changes
6. **Tag for production** — `git tag strapi-vX.Y.Z && git push origin strapi-vX.Y.Z`

You **cannot** create or modify content types via `cms.myvoya.ai` or `cms-staging.myvoya.ai`. Only **content** (entries) is editable there. This is intentional Strapi behavior, not a config issue — see the [Strapi docs](https://docs.strapi.io/cms/quick-start).

## What to commit

**Always commit:**

- `cms/src/api/**` — content type schemas and handlers
- `cms/src/components/**` — reusable component schemas
- `cms/src/extensions/**` — Strapi extensions
- `cms/config/**` — server, database, plugins config
- `cms/package.json`, `cms/package-lock.json`
- `cms/Dockerfile`, `cms/.dockerignore`, `cms/.env.example`
- `cms/types/generated/` — TypeScript type definitions for content types and components
- `cms/src/generated/openapi-spec.json` — OpenAPI 3.1 specification (auto-generated)

**Never commit** (gitignored):

- `cms/node_modules/`
- `cms/.env` (secrets)
- `cms/build/`, `cms/dist/`, `cms/.strapi/`, `cms/.tmp/`, `cms/.cache/`, `cms/exports/`
- `cms/.strapi-updater.json` — version-check cache, regenerated on startup

Custom Strapi code under `src/extensions/` (for example upload-provider overrides) is **tracked in git**. Do not add a blanket ignore for `src/extensions/` or you risk excluding required server files.

## Generated files

Two sets of generated files are tracked in git so consumers (frontend, tooling) can use them without running Strapi:

- **TypeScript types** (`types/generated/`) — `contentTypes.d.ts` and `components.d.ts`
- **OpenAPI spec** (`src/generated/openapi-spec.json`) — Swagger/OpenAPI 3.1

Regenerate both after any content type or component change:

```bash
docker compose exec strapi npm run generate
```

Or outside Docker (from `cms/`):

```bash
npm run generate
```

## Landing page API (frontend consumption)

The `landing-page` single-type is exposed at `GET /api/landing-page`. By default Strapi does **not** grant anonymous access: in the admin UI, open **Settings → Users & Permissions → Roles → Public**, enable **find** (and **findOne** if listed) for **Landing-page**, so the marketing site can load content without a JWT.

Nested and repeatable components (for example `footer` → `quickLinks`, `socialLinks`, or `signUpCta` → `testimonial` with media) are not always returned unless you **populate** them. The Voya frontend builds explicit `populate[...]` query strings in [`frontend-v2/src/api/strapiApi.ts`](../frontend-v2/src/api/strapiApi.ts). For ad hoc calls you can use nested populate parameters or the populate-deep plugin if installed—see [Strapi REST populate](https://docs.strapi.io/dev-docs/api/rest/populate-select).

**Footer and social URLs** are stored as plain strings. The frontend mapper drops dangerous `javascript:` / `data:` URLs before binding to `<a href>`; treat any other CMS-provided URL with normal care for external links.

**How it works — step numbers:** Component JSON cannot express integer `min`; validation runs in [`src/api/landing-page/content-types/landing-page/lifecycles.js`](src/api/landing-page/content-types/landing-page/lifecycles.js) on create/update. Each `howItWorks.steps[]` entry that includes `stepNumber` must use an integer ≥ 1.

## Configuration

Plugin config in [config/plugins.js](config/plugins.js) is environment-aware:

- **SendGrid email** — only when `SENDGRID_API_KEY` is set
- **S3 upload** — only when `AWS_S3_BUCKET` is set
- **MCP plugin** — only when `NODE_ENV=development`

Production secrets live in AWS Secrets Manager (`{env}-strapi-*`), provisioned by [terraform/modules/strapi-secrets/](../terraform/modules/strapi-secrets/). The RDS master password is managed by RDS itself ([terraform/modules/strapi-rds/main.tf:50](../terraform/modules/strapi-rds/main.tf#L50)).

## Infrastructure

| Resource | Staging | Production |
|---|---|---|
| Admin domain | `cms-staging.myvoya.ai` | `cms.myvoya.ai` |
| Media CDN | `strapi-media-staging.myvoya.ai` | `strapi-media.myvoya.ai` |
| ECR repo | `myvoya-staging-strapi` | `myvoya-production-strapi` |
| ECS service | `staging-strapi` | `production-strapi` |
| Deploy trigger | Push to `main` (auto) | Tag `strapi-vX.Y.Z` (manual) |

Terraform modules: [strapi/](../terraform/modules/strapi/), [strapi-rds/](../terraform/modules/strapi-rds/), [strapi-media/](../terraform/modules/strapi-media/), [strapi-secrets/](../terraform/modules/strapi-secrets/).

## Troubleshooting

- **Content-Type Builder is missing in admin sidebar** — you're connected to a non-dev instance. The builder only appears in `strapi develop`.
- **Schema changes don't appear after restart** — check `cms/src/api/{name}/content-types/{name}/schema.json` exists and is valid JSON.
- **Local image uploads break after restart** — the dev container mounts source code but uses a Docker volume for `node_modules`. Uploads go to `cms/public/uploads/` which is committed via [public/uploads/.gitkeep](public/uploads/.gitkeep).
- **`db_name "strapi" already exists`** on first apply — RDS module uses a fresh DB; check that the `strapi_admin` user has access in the parameter group.

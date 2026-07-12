# CI/CD Guide

GitHub Actions CI/CD pipeline and workflows for the Voya platform.

## Pipeline Overview

The project uses GitHub Actions for automated testing and quality checks. The CI pipeline runs on every push and pull request to `main` and `feature/**` branches.

## Workflow Structure

Location: `.github/workflows/ci.yml`

### Job Dependencies
```
lint ──┐
       ├──> test-backend
type   │
       │
security┘
```

**Parallel Jobs** (run simultaneously):
- lint
- type-check
- security
- test-backend

## CI Jobs

### 1. Lint & Format Check
- Runs Ruff linting on Python backend code
- Checks code formatting compliance
- Fast feedback on code style issues
- **Duration**: < 1 minute

### 2. Type Check
- Runs MyPy static type checking on Python backend
- Ensures type hints are correct and consistent
- Caches `.mypy_cache` for faster subsequent runs
- **Duration**: ~5 minutes (first run), ~2 minutes (cached)

### 3. Security Scan
- Runs Bandit security scanner on Python backend
- Detects common security vulnerabilities
- Configured via `pyproject.toml` for low-severity filtering
- **Duration**: < 2 minutes

### 4. Backend Tests
- Runs pytest unit tests with coverage reporting (XML, JSON, terminal)
- Minimum 80% coverage required for new code
- **Duration**: ~3-5 minutes

### 5. Coverage Report (PR only)
- Runs after frontend and backend test jobs (even if they fail)
- Posts a sticky PR comment with overall coverage for both stacks
- Shows coverage specifically for **changed files** in the PR
- Includes commit SHA to prevent confusion from stale comments

## Environment Configuration

- **Python Version**: 3.12 (matches production)
- **Node.js Version**: 20.x (matches production)
- **Runner**: `ubuntu-latest` (GitHub-hosted)
- **Timeout**: 30 minutes per workflow
- **Caching**: pip packages, npm packages, Playwright browsers, MyPy cache

## Running CI Locally

Before pushing code, run the same checks locally:

### Backend Checks
```bash
cd backend_python
ruff check .                    # Linting
ruff format --check .           # Format check
mypy app/                       # Type checking
bandit -r app/ -ll -c pyproject.toml  # Security scan
pytest tests/unit_tests/ --cov=app    # Unit tests
```

### Frontend Checks
```bash
cd frontend-v2
npm ci                          # Clean install
npm run test                    # Vitest
npm run build                   # Production build
```

### E2E Tests
```bash
cd testing
docker compose -f ../compose.test.yaml up -d
npm run test:all
docker compose -f ../compose.test.yaml down -v
```

## Caching Strategy

CI uses aggressive caching to speed up builds:

### Backend Caching
- **pip packages**: `~/.cache/pip`
- **MyPy cache**: `backend_python/.mypy_cache`
- **Ruff cache**: `.ruff_cache`

### Frontend Caching
- **npm packages**: `~/.npm`

### E2E Caching
- **Playwright browsers**: `~/.cache/ms-playwright`

### Clear Local Caches
```bash
# Python caches
rm -rf backend_python/.mypy_cache
rm -rf backend_python/.pytest_cache
pip cache purge

# Node caches
rm -rf frontend-v2/node_modules
rm -rf testing/node_modules
npm cache clean --force
```

## Checking CI Status

### Using GitHub CLI

**View PR status**:
```bash
gh pr status
```

**View detailed PR checks**:
```bash
gh pr checks
```

**List recent workflow runs**:
```bash
gh run list --limit 10
```

**View specific run**:
```bash
gh run view <run-id>
gh run view --log  # View logs
```

**Watch running workflow**:
```bash
gh run watch
```

**Re-run failed jobs**:
```bash
gh run rerun --failed
```

### Workflow Run Examples

**List runs for current branch**:
```bash
gh run list --branch $(git branch --show-current)
```

**Check if latest run passed**:
```bash
gh run list --limit 1 --json conclusion --jq '.[0].conclusion'
# Output: "success" or "failure"
```

**Download artifacts**:
```bash
gh run download <run-id>
```

## Pre-commit Hooks

The project uses pre-commit hooks to catch issues before committing.

**Complete Policy**: See root `CLAUDE.md` → Pre-commit Hooks section for Boy Scout Rule, bypass guidelines, and proper workflow.

### Install Hooks
```bash
pip install pre-commit
pre-commit install                      # Commit hooks (ruff, basic checks)
pre-commit install --hook-type pre-push # Push hooks (mypy, bandit)
```

### Hook Strategy
- **Commit hooks**: Fast checks (< 10s) - ruff format, ruff check
- **Push hooks**: Thorough checks (< 60s) - mypy, bandit
- This prevents slow commits while maintaining quality

### Run Hooks Manually
```bash
pre-commit run --all-files      # Run all hooks
pre-commit run ruff             # Run specific hook
```

## CI/CD Best Practices Applied

### Reproducible Builds
- Uses `npm ci` instead of `npm install`
- Pins action versions to commit SHAs
- Consistent environment across runs

### Performance Optimization
- Aggressive caching of dependencies and build artifacts
- Parallel job execution where possible
- Fail fast: Linting runs first, tests only if linting passes

### Testing Isolation
- E2E tests use separate database (`voya_test`)
- Dedicated test services (ports 3001/8001/27018/8026)
- Complete cleanup after tests (even on failure)

### Security
- GitHub Secrets for sensitive data
- Minimal token permissions
- No secrets in code or logs

### Reliability
- 30-minute workflow timeout prevents hanging jobs
- Always cleanup (test environment torn down even if tests fail)
- Artifact retention: Test reports kept for 30 days

## Viewing CI Results

### Pull Requests
- CI status shown directly in PR checks
- Click "Details" to view full logs
- See which specific checks failed

### Actions Tab
- Full workflow logs available
- View job-specific output
- Download artifacts

### Artifacts
Available artifacts on failure:
- **Playwright reports**: `playwright-report/`
- **Test results**: `test-results/`
- **Screenshots**: `test-results/*/test-failed-*.png`
- **Videos**: `test-results/*/video.webm`
- **Frontend coverage**: `coverage-summary.json` (vitest json-summary)
- **Backend coverage**: `coverage.json` (pytest-cov)

### Download Artifacts
```bash
gh run download <run-id>
# Downloads all artifacts to current directory
```

## Troubleshooting CI Failures

### Lint Failures
**Fix**: Run `ruff check --fix .` locally and commit

### Type Check Failures
**Fix**: Run `mypy app/` locally, fix errors, commit
- Check for missing type hints
- Verify Pydantic plugin is configured
- Clear MyPy cache if seeing stale errors

### Security Scan Failures
**Fix**: Run `bandit -r app/ -ll -c pyproject.toml` locally
- Review security issues
- Fix or add exclusions if false positives
- Never skip real security issues

### Test Failures
**Fix**: Run tests locally, check uploaded artifacts
- Download test results artifact
- Check screenshots for E2E failures
- Review error logs in CI output

### Build Failures
**Fix**: Run `npm run build` locally
- Check for missing dependencies
- Verify environment variables
- Check import/export errors

### E2E Failures
**Fix**:
1. Check service health logs in CI
2. Verify `compose.test.yaml` configuration
3. Download and review Playwright report artifact
4. Check screenshots/videos for failure details
5. Ensure services started correctly (health checks passed)

### Timeout Issues
**Fix**: Workflow times out after 30 minutes
- Check for hanging services
- Look for infinite loops
- Review test execution time
- Consider splitting into smaller jobs

## Coverage

### Thresholds
- **Backend**: 80% minimum coverage for new code
- **Frontend**: 80% minimum for new code (overall is lower due to legacy untested components)

### PR Coverage Comment
Every PR gets a sticky comment showing:
- **Overall**: full project coverage for both stacks
- **Changed files**: coverage of only the files touched in the PR
- **Commit SHA**: to identify which push the numbers correspond to

Frontend coverage includes all source files (`include: ['src/**/*.{ts,tsx}']`), not just files imported by tests. This gives honest numbers.

### Local Coverage
```bash
# Backend
cd backend_python && pytest tests/unit_tests/ --cov=app --cov-report=html

# Frontend
cd frontend-v2 && npx vitest run --project unit --coverage
```

## Useful Aliases

Add to your shell config:
```bash
alias ci-status='gh run list --limit 5'
alias ci-watch='gh run watch'
alias ci-checks='gh pr checks'
alias ci-logs='gh run view --log'
alias ci-rerun='gh run rerun --failed'
```

## Deployment Workflows

The project uses GitHub Actions for automated deployments to AWS ECS.

### Environments

| Environment | URL | Trigger | ECR Repository |
|-------------|-----|---------|----------------|
| Test | https://test.myvoya.ai | `deploy/test` branch push, or manual | `myvoya-test-fastapi-react` |
| Staging | https://staging.myvoya.ai | `main` branch (after CI passes) | `myvoya-staging-fastapi-react` |
| Production | https://prod.myvoya.ai | Git tag `v*.*.*` | `myvoya-production-fastapi-react` |

### Deployment Workflows

**`deploy-test.yml`** - Deploy to test environment
- **Trigger**: Push to `deploy/test` branch, or manual dispatch
- **No CI gate**: Deploys immediately (useful for rapid iteration)
- **Use case**: Testing new features, debugging, integration testing

**`deploy-staging.yml`** - Deploy to staging environment
- **Trigger**: After CI passes on `main` branch (`workflow_run` on CI Pipeline)
- **CI gated**: Only deploys if all CI checks pass
- **Use case**: Pre-production testing, stakeholder demos
- **Post-deploy**: Purges CloudFlare cache for `staging.myvoya.ai`

**`deploy-prod.yml`** - Deploy to production environment
- **Trigger**: Push tag matching `v[0-9]*.[0-9]*.[0-9]*` (e.g., `v2026.2.6`)
- **No CI gate**: Assumes tagged commits have already passed CI on main
- **Use case**: Production releases
- **Post-deploy**: Purges CloudFlare cache for `prod.myvoya.ai` and `app.myvoya.ai`

### Deployment Process

All deployment workflows follow the same process:

1. **Build**: Docker image built with build args (see [Build Arguments](#docker-build-arguments))
2. **Push**: Image pushed to ECR with version tag + `latest`
3. **Deploy**: ECS task definition downloaded, updated with new image, re-registered, service updated
4. **Stabilize**: Wait for ECS service stability + old tasks to drain
5. **Cache purge**: CloudFlare cache purged for the relevant domain(s)
6. **Summary**: Deployment status written to GitHub Step Summary

### Docker Build Arguments

The Dockerfile accepts these build arguments, passed during CI builds:

| Build Arg | Purpose | Staging Value | Production Value |
|-----------|---------|---------------|------------------|
| `COMMIT_HASH` | Git commit SHA for `/health` endpoint | Commit SHA (8 chars) | `$GITHUB_SHA` |
| `GIT_VERSION` | Version string from `git describe` | Auto-generated | Auto-generated |
| `VITE_ENV` | Frontend environment mode | `staging` | `production` |
| `VITE_GOOGLE_CLIENT_ID` | Google OAuth client ID (baked into JS) | From GitHub Secret | From GitHub Secret |
| `VITE_GOOGLE_MAPS_API_KEY` | Google Maps JavaScript API (client-side maps) | From GitHub Secret | From GitHub Secret |
| `VITE_STRAPI_URL` | Strapi CMS base URL (landing / home content) | `VITE_STRAPI_URL_STAGING` | `VITE_STRAPI_URL_PROD` |
| `VITE_STRAPI_API_TOKEN` | Strapi read-only API token (public in bundle) | `VITE_STRAPI_API_TOKEN_STAGING` | `VITE_STRAPI_API_TOKEN_PROD` |

**Important**: `VITE_*` args are inlined into the frontend JavaScript bundle at build time by Vite. They cannot be changed at runtime, only by rebuilding the Docker image.

### Commit Hash & Version in /health

The `/health` endpoint includes the deployed version for traceability:

```json
{
  "status": "OK",
  "service": "Voya API",
  "version": "2026.2.6",
  "commit": "abc1234d",
  "database": "connected"
}
```

Set via:
1. **Dockerfile**: `ARG COMMIT_HASH=unknown`, `ARG GIT_VERSION=unknown`
2. **CI build**: `--build-arg COMMIT_HASH=... --build-arg GIT_VERSION=...`
3. **Backend config**: `settings.GIT_COMMIT_HASH`, `settings.GIT_VERSION`

### Deploying to Test Environment

**Via Git (recommended)**:
```bash
# From any branch, push to deploy/test
git push origin HEAD:deploy/test
```

**Via GitHub Actions UI**:
1. Go to Actions > "Deploy to Test"
2. Click "Run workflow", select branch, click "Run workflow"

### Deploying to Staging

Staging deploys automatically when CI passes on `main`:
```bash
git checkout main && git merge feature/your-branch && git push origin main
# CI passes → automatic staging deploy
```

### Deploying to Production

Production deploys are triggered by pushing a version tag:
```bash
# Tag convention: v{year}.{month}.{deployment_number}[.p{patch}]
git tag v2026.2.6
git push origin v2026.2.6

# Patch release (hotfix on existing release):
git tag v2026.2.6.p1
git push origin v2026.2.6.p1
```

### Monitoring Deployments

```bash
# Check deployment status
gh run list --workflow=deploy-staging.yml
gh run list --workflow=deploy-prod.yml

# Watch running deployment
gh run watch

# Check deployed version
curl -s https://staging.myvoya.ai/health | jq '{version, commit}'
curl -s https://prod.myvoya.ai/health | jq '{version, commit}'
```

### AWS Infrastructure

| Resource | Test | Staging | Production |
|----------|------|---------|------------|
| ECS Cluster | `test-cluster` | `staging-cluster` | `production-cluster` |
| ECS Service | `test-fastapi-react-service` | `staging-fastapi-react-service` | `production-fastapi-react-service` |
| Task Definition | `test-fastapi-react` | `staging-fastapi-react` | `production-fastapi-react` |
| ECR Repository | `myvoya-test-fastapi-react` | `myvoya-staging-fastapi-react` | `myvoya-production-fastapi-react` |

**Note**: Infrastructure is managed via Terraform (manual apply with `voya-admin` profile). GitHub Actions only has ECR/ECS permissions via `GitHubActionsDeployRole`.

### Troubleshooting Deployments

**Deployment fails at build**:
- Check Docker build logs in GitHub Actions
- Verify Dockerfile syntax and dependencies
- Check ECR login succeeded

**Deployment fails at ECS update**:
- Check task definition is valid
- Verify IAM role has necessary permissions
- Check ECS service events: `aws ecs describe-services --cluster <cluster> --services <service>`

**Service doesn't stabilize**:
- Check container health check is passing
- Review CloudWatch logs
- Check container can connect to MongoDB and other services

**Wrong commit hash in /health**:
- Verify `--build-arg COMMIT_HASH` was passed
- Check ECS service completed rollout (old tasks may still be draining)

---

## Adding New Environment Variables & Configuration

When adding a new configuration value to the application, you need to update multiple places depending on the type of variable. This section serves as a checklist.

### Types of Configuration

There are four types of configuration, each with different propagation paths:

| Type | Example | Build-time or Runtime | Where It Lives |
|------|---------|----------------------|----------------|
| **Vite build arg** | `VITE_ENV`, `VITE_GOOGLE_*`, `VITE_STRAPI_*` | Build-time (baked into JS) | Dockerfile + CI workflow |
| **Backend env var (non-secret)** | `ENVIRONMENT`, `DEBUG`, `FRONTEND_URL` | Runtime | ECS task definition (Terraform) |
| **Backend env var (secret)** | `SECRET_KEY`, `MONGODB_URI`, `SENDGRID_API_KEY` | Runtime | AWS Secrets Manager (Terraform) |
| **GitHub Actions secret** | `REACT_APP_GOOGLE_CLIENT_ID_*`, `VITE_GOOGLE_MAPS_API_KEY_*`, `VITE_STRAPI_URL_*`, `VITE_STRAPI_API_TOKEN_*` | Build-time (CI only) | GitHub repo settings |

### Checklist: Adding a Vite Build Arg (Frontend)

Vite build args (`VITE_*`) are inlined into the JavaScript bundle at build time. They **cannot** be changed at runtime.

1. **Dockerfile** (`Dockerfile`, in the `frontend-build-npm` stage):
   ```dockerfile
   ARG VITE_MY_NEW_VAR=""
   ENV VITE_MY_NEW_VAR=$VITE_MY_NEW_VAR
   ```

2. **CI deploy workflows** (add `--build-arg` to Docker build command):
   - `.github/workflows/deploy-staging.yml` — set staging value
   - `.github/workflows/deploy-prod.yml` — set production value
   - `.github/workflows/deploy-test.yml` — set test value (if applicable)
   ```yaml
   docker build \
     --build-arg VITE_MY_NEW_VAR=${{ secrets.MY_NEW_VAR }} \
     ...
   ```

3. **GitHub Secrets** (if the value is sensitive or per-environment):
   - Add secret in GitHub repo Settings > Secrets and variables > Actions
   - Use naming convention: `MY_NEW_VAR_STAGING`, `MY_NEW_VAR_PROD`

4. **Local development** (`frontend-v2/.env` or `frontend-v2/.env.local`):
   ```
   VITE_MY_NEW_VAR=local-value
   ```

5. **Docker Compose** (`compose.dev.yaml`, `compose.test.yaml` if needed):
   ```yaml
   build:
     args:
       VITE_MY_NEW_VAR: "dev-value"
   ```

### Checklist: Adding a Backend Environment Variable (Non-Secret)

Non-secret backend env vars are set in the ECS task definition via Terraform.

1. **Backend config** (`backend_python/app/core/config.py`):
   ```python
   MY_NEW_VAR: str = "default-value"
   ```

2. **Terraform ECS task definition** (`terraform/modules/ecs/main.tf`):
   Add to the container definition's `environment` block:
   ```hcl
   { name = "MY_NEW_VAR", value = var.my_new_var }
   ```

3. **Terraform variables** (propagate through environment modules):
   - `terraform/modules/ecs/variables.tf` — declare the variable
   - `terraform/environments/prod/main.tf` — set the production value
   - `terraform/environments/staging/main.tf` — set the staging value

4. **Local development** (`backend_python/.env`):
   ```
   MY_NEW_VAR=local-value
   ```

5. **Docker Compose** (`compose.dev.yaml`, `compose.test.yaml`):
   ```yaml
   environment:
     MY_NEW_VAR: "dev-value"
   ```

### Checklist: Adding a Backend Secret

Secrets are stored in AWS Secrets Manager and injected into ECS containers at runtime.

1. **Backend config** (`backend_python/app/core/config.py`):
   ```python
   MY_SECRET: str = ""
   ```

2. **AWS Secrets Manager** — add the secret value:
   ```bash
   aws secretsmanager create-secret --name prod/voya/MY_SECRET --secret-string "value" --profile voya-admin
   ```

3. **Terraform secrets module** (`terraform/modules/secrets/main.tf`):
   Add to `local.secrets` with a description, then add to the ECS task definition `secrets` block in `terraform/modules/ecs/main.tf`:
   ```hcl
   { name = "MY_SECRET", valueFrom = var.secret_arns["MY_SECRET"] }
   ```
   Example: `PASSENGER_ENCRYPTION_KEY` (Fernet key for passenger PII encryption).

4. **Terraform apply** (manual, with `voya-admin` profile):
   ```bash
   cd terraform/environments/prod && terraform plan -var="aws_profile=voya-admin" -out=tfplan
   terraform apply tfplan
   ```

5. **Local development** (`backend_python/.env`):
   ```
   MY_SECRET=local-dev-value
   ```

### Checklist: Adding a GitHub Actions Secret

GitHub Actions secrets are used for values needed during CI builds (not at runtime).

1. **GitHub repo settings**: Settings > Secrets and variables > Actions > New repository secret
2. **Reference in workflow**: `${{ secrets.MY_SECRET_NAME }}`
3. **Naming convention**: Use `_STAGING`, `_PROD` suffixes for per-environment values

### Quick Decision Guide

```
Is this a frontend value?
  └─ Yes → Is it a VITE_* build arg? → Follow "Vite Build Arg" checklist
  └─ No → Is it sensitive (API key, password, token)?
       └─ Yes → Follow "Backend Secret" checklist
       └─ No → Follow "Backend Env Var" checklist

Is it only needed during CI builds (not at runtime)?
  └─ Yes → Follow "GitHub Actions Secret" checklist
```

### Common Pitfalls

- **Vite vars not updating**: `VITE_*` variables are baked in at Docker build time. Restarting the container won't pick up changes, you need to rebuild the image and redeploy.
- **Missing from one environment**: Always update all three deploy workflows (test, staging, prod) when adding a build arg.
- **Terraform not applied**: Adding a var to Terraform files does nothing until you run `terraform apply`. GitHub Actions cannot apply Terraform, this must be done manually.
- **Secret not in Secrets Manager**: ECS will fail to start if a `secrets` entry references a non-existent secret ARN.

## Related Documentation

- **Testing**: See `docs/TESTING.md` for test strategies
- **Code Quality**: See `docs/CODE_QUALITY.md` for linting/formatting
- **Local Development**: See `docs/LOCAL_DEVELOPMENT.md` for setup

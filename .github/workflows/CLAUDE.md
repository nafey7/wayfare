# GitHub Actions Workflows

**📖 For comprehensive CI/CD documentation, see `docs/CI_CD.md` at the project root.**

## Quick Reference

This directory contains CI/CD workflows for the Voya platform.

### Main Workflow

**`ci.yml`** - Main CI pipeline that runs on push/PR to `main` and `feature/**` branches

**Jobs**: Lint → Type Check → Security → Backend Tests

**Environment**: Python 3.12, Node.js 20.x, Ubuntu latest

## Testing Locally

Run the same checks CI runs:

```bash
# Backend checks
cd backend_python
ruff check . && ruff format . && mypy app/ && bandit -r app/ -ll

# E2E tests
docker compose -f compose.test.yaml up -d
cd testing && npm run test:all
docker compose -f compose.test.yaml down -v
```

## Checking CI Status

```bash
gh pr checks        # Current PR status
gh run list         # Recent workflow runs
gh run view --log   # View logs
gh run watch        # Watch running workflow
```

## Documentation

See `docs/CI_CD.md` for:
- Complete workflow documentation
- Job dependencies and caching strategy
- E2E testing setup with Docker
- Troubleshooting guide
- Best practices and modification guidelines

---

**See `docs/CI_CD.md` for comprehensive CI/CD documentation.**

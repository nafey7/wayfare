# Voya Release Process

This document describes how to release new versions to production.

## Versioning Scheme

### Git Tags

**Format**: `v{YEAR}.{MONTH}.{INCREMENT}[.p{PATCH}]` (with `v` prefix)

#### Regular Releases
- `v2025.12.1` - First release of December 2025
- `v2025.12.2` - Second release of December 2025
- `v2025.12.3` - Third release of December 2025

The increment resets each month.

#### Hotfix/Patch Releases
When a hotfix is needed after a release, append `.p{N}`:
- `v2025.12.4` - Original release
- `v2025.12.4.p1` - First hotfix to v2025.12.4
- `v2025.12.4.p2` - Second hotfix to v2025.12.4

**Important**: Never move existing tags. Always create a new patch version for hotfixes.

### Docker Image Tags

**Format**: Multiple tags per image (without `v` prefix for versions)

| Tag | Format | Example | Purpose |
|-----|--------|---------|---------|
| Version | `{YEAR}.{MONTH}.{INCREMENT}` | `2025.12.7` | Immutable release identifier |
| Commit SHA | `<7-char-sha>` | `d807052` | Traceability to exact commit |
| Latest | `latest` | `latest` | Most recent build |

**Convention**: Git tags use `v` prefix, Docker tags omit it.

```bash
# Git tag
git tag -a v2025.12.7 -m "Production deployment 2025-12-29"

# Docker tags (same image, 3 tags)
docker tag app:local $ECR_REPO:2025.12.7    # Version (no v prefix)
docker tag app:local $ECR_REPO:d807052      # Commit SHA (7 chars)
docker tag app:local $ECR_REPO:latest       # Latest
```

### Environment Tag Strategies

| Environment | ECR Repository | Tag Strategy |
|-------------|----------------|--------------|
| Production | `myvoya-prod-fastapi-react` | `YYYY.MM.N`, `<7-char-sha>`, `latest` |
| Staging | `myvoya-staging-fastapi-react` | `<8-char-sha>`, `latest` (via CI) |
| Test | `myvoya-test-fastapi-react` | `<8-char-sha>`, `latest` (via CI) |

## Pre-Release Checklist

- [ ] All PRs merged to `main`
- [ ] CI pipeline passing on `main`
- [ ] Staging environment tested
- [ ] No critical bugs in staging

## Release Steps

### 1. Identify Changes Since Last Release

```bash
# Find the last release tag
git tag -l 'v*' --sort=-v:refname | head -5

# List commits since last release
git log v2025.12.3..main --oneline --first-parent

# List merged PRs
git log v2025.12.3..main --oneline --merges
```

### 2. Check for Environment Variable Changes

```bash
# Check terraform changes
git diff v2025.12.3..main -- 'terraform/**/*.tf' --stat

# Check for new env vars in settings
git diff v2025.12.3..main -- 'backend_python/app/core/settings.py'

# Check dependency changes
git diff v2025.12.3..main -- 'backend_python/requirements.txt'
```

### 3. Create Release Notes

Create a release notes file:

```bash
# Create releases directory if needed
mkdir -p docs/releases

# Create release notes (use previous as template)
cp docs/releases/v2025.12.3.md docs/releases/v2025.12.4.md
```

Include:
- Summary of changes
- Detailed changelog per PR
- Environment variable changes
- Production deployment checklist
- QA testing guide

### 4. Build and Push Docker Image

```bash
# Set variables
VERSION="2025.12.7"  # Without v prefix for Docker
COMMIT_SHA=$(git rev-parse --short=7 HEAD)  # e.g., d807052
ECR_REPO="155304839180.dkr.ecr.us-east-1.amazonaws.com/myvoya-prod-fastapi-react"

# Build the image (no REACT_APP_API_URL for prod - uses relative URLs)
docker build -t myvoya-prod-fastapi-react:$VERSION --platform linux/amd64 .

# Tag for ECR (3 tags: version, commit SHA, latest)
docker tag myvoya-prod-fastapi-react:$VERSION $ECR_REPO:$VERSION
docker tag myvoya-prod-fastapi-react:$VERSION $ECR_REPO:$COMMIT_SHA
docker tag myvoya-prod-fastapi-react:$VERSION $ECR_REPO:latest

# Login to ECR
AWS_PROFILE=voya-admin aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $ECR_REPO

# Push all tags to ECR
docker push $ECR_REPO:$VERSION
docker push $ECR_REPO:$COMMIT_SHA
docker push $ECR_REPO:latest
```

### 5. Deploy to ECS

```bash
# Download current task definition
AWS_PROFILE=voya-admin aws ecs describe-task-definition \
  --task-definition fastapi-react \
  --region us-east-1 \
  --query 'taskDefinition' > task-def.json

# Update image tag to version (use jq)
ECR_REPO="155304839180.dkr.ecr.us-east-1.amazonaws.com/myvoya-prod-fastapi-react"
VERSION="2026.1.4"

jq --arg IMG "$ECR_REPO:$VERSION" \
  'del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .compatibilities, .registeredAt, .registeredBy) |
   .containerDefinitions[0].image = $IMG' \
  task-def.json > new-task-def.json

# To also add/update environment variables (e.g., feature flags):
jq '.containerDefinitions[0].image = "155304839180.dkr.ecr.us-east-1.amazonaws.com/myvoya-prod-fastapi-react:2026.1.4" |
    .containerDefinitions[0].environment += [{"name": "VOYA_FEATURE_FLAG_NEW_FEATURE", "value": "true"}] |
    del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .compatibilities, .registeredAt, .registeredBy)' \
  task-def.json > new-task-def.json

# Register new task definition revision
AWS_PROFILE=voya-admin aws ecs register-task-definition \
  --cli-input-json file://new-task-def.json \
  --region us-east-1

# Get the new revision number
NEW_REVISION=$(AWS_PROFILE=voya-admin aws ecs describe-task-definition \
  --task-definition fastapi-react \
  --region us-east-1 \
  --query 'taskDefinition.revision' --output text)

# Update service with new task definition
AWS_PROFILE=voya-admin aws ecs update-service \
  --cluster myvoya_prod_cluster \
  --service fastapi-react-service-f3hmdaii \
  --task-definition fastapi-react:$NEW_REVISION \
  --force-new-deployment \
  --region us-east-1

# Wait for stability (up to 10 minutes)
AWS_PROFILE=voya-admin aws ecs wait services-stable \
  --cluster myvoya_prod_cluster \
  --services fastapi-react-service-f3hmdaii \
  --region us-east-1

# Verify deployment
AWS_PROFILE=voya-admin aws ecs describe-services \
  --cluster myvoya_prod_cluster \
  --services fastapi-react-service-f3hmdaii \
  --region us-east-1 \
  --query 'services[0].deployments[?status==`PRIMARY`]'
```

### 6. Create Git Tag

```bash
# Get the commit SHA to tag (usually HEAD of main)
git log --oneline -1

# Create and push tag (use annotated tag with message)
git tag -a v2026.1.4 -m "Production deployment YYYY-MM-DD: Brief description"
git push origin v2026.1.4
```

### 7. Post-Deployment Verification

1. **Health check**: Visit https://app.myvoya.ai/health
2. **Login flow**: Test login at https://app.myvoya.ai
3. **Chat functionality**: Send a test message
4. **Check logs**:
   ```bash
   AWS_PROFILE=voya-admin aws logs tail /ecs/myvoya-prod --follow --region us-east-1
   ```

## Hotfix Process

If a critical bug is found after release:

### 1. Fix and Commit

```bash
# Fix the issue on main
git commit -m "fix: description of hotfix"
git push origin main
```

### 2. Rebuild and Redeploy

Follow steps 4-5 above (Build and Push Docker Image, Deploy to ECS).

### 3. Create Patch Tag

**Never move existing tags.** Create a new patch version:

```bash
# Get the hotfix commit SHA
git log --oneline -1

# Create patch tag (e.g., v2025.12.4.p1)
git tag v2025.12.4.p1 <hotfix-commit-sha>
git push origin v2025.12.4.p1
```

### 4. Update Release Notes

Add hotfix section to the existing release notes or create a new patch release doc:

```markdown
## Hotfix v2025.12.4.p1

**Commit**: `abc1234`
**Issue**: Brief description of the bug
**Fix**: What was changed
```

## Rollback Process

If deployment fails or critical issues are found:

### Quick Rollback (Previous Task Definition)

```bash
# List recent task definitions
AWS_PROFILE=voya-admin aws ecs list-task-definitions \
  --family-prefix fastapi-react \
  --sort DESC \
  --region us-east-1

# Update service to previous revision (e.g., :25 instead of :26)
AWS_PROFILE=voya-admin aws ecs update-service \
  --cluster myvoya_prod_cluster \
  --service fastapi-react-service-f3hmdaii \
  --task-definition fastapi-react:25 \
  --region us-east-1
```

### Full Rollback (Previous Git Tag)

```bash
# Checkout previous release
git checkout v2025.12.3

# Rebuild and deploy
docker build -t myvoya-prod-fastapi-react:latest .
# ... follow deploy steps
```

## Environment Details

### Production

| Resource | Value |
|----------|-------|
| ECS Cluster | `myvoya_prod_cluster` |
| ECS Service | `fastapi-react-service-f3hmdaii` |
| Task Definition | `fastapi-react` |
| ECR Repository | `myvoya-prod-fastapi-react` |
| URL | https://app.myvoya.ai |
| AWS Region | us-east-1 |
| AWS Profile | voya-admin |

### Staging

| Resource | Value |
|----------|-------|
| ECS Cluster | `staging-cluster` |
| ECS Service | `staging-fastapi-react-service` |
| ECR Repository | `myvoya-staging-fastapi-react` |
| URL | https://staging.myvoya.ai |
| Deployment | Automatic on merge to `main` (via GitHub Actions) |

## Important Notes

### Frontend API URLs

- **Production**: Uses relative URLs (no `REACT_APP_API_URL` build-arg)
- **Staging**: Uses `REACT_APP_API_URL=https://staging.myvoya.ai/api`

Do NOT set `REACT_APP_API_URL` for production builds - this causes CORS errors.

### Docker Build Args

```bash
# Production (relative URLs)
docker build -t myvoya-prod-fastapi-react:latest .

# Staging (absolute URLs)
docker build -t myvoya-staging-fastapi-react:latest \
  --build-arg REACT_APP_API_URL=https://staging.myvoya.ai/api .
```

### Release Tags

- Always tag the deployed commit
- **Never move existing tags** - use patch versions for hotfixes (`.p1`, `.p2`, etc.)
- Use annotated tags for major releases: `git tag -a v2025.12.4 -m "Release v2025.12.4"`
- Keep release notes in `docs/releases/`

## Automation (Future)

Currently production deployments are manual. Future improvements:

- [ ] Create `deploy-prod.yml` GitHub Actions workflow
- [ ] Add manual approval gate for prod deploys
- [ ] Tag images with commit SHA (like staging does)
- [ ] Automated release notes generation

---

**Last Updated**: January 2026

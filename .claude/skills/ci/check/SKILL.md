---
name: ci:check
description: Check GitHub Actions CI pipeline status, view workflow runs, logs, and re-run failed jobs. Use when user asks about CI, build status, or pipeline.
allowed-tools: Bash(gh:*)
argument-hint: [pr-number|run-id]
---

# Check CI Pipeline Status

@docs/CI_CD.md

Check GitHub Actions CI/CD pipeline status for $ARGUMENTS

## Quick Status Check

### Check current PR status
```bash
gh pr status
```

### View detailed PR checks
```bash
gh pr checks
```

### List recent workflow runs
```bash
gh run list --limit 10
```

### View logs for latest run
```bash
gh run view --log
```

### Watch a running workflow
```bash
gh run watch
```

## Common Actions

### Re-run failed jobs
```bash
gh run rerun --failed
```

### Download test artifacts
```bash
gh run download <run-id>
# Includes: playwright-report/, test-results/, coverage reports
```

### Check if latest run passed
```bash
gh run list --limit 1 --json conclusion --jq '.[0].conclusion'
```

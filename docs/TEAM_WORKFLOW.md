# Team Workflow Guide

This guide explains how to contribute to the Voya project using pull requests and CI/CD.

## Prerequisites

### GitHub CLI Setup
```bash
# Install GitHub CLI

# For Ubuntu:
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
  sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" |
  sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
  sudo apt update
  sudo apt install gh

# Then authenticate:
gh auth login
```

### Local Development Setup
```bash
# Clone the repository
git clone git@github.com:myvoya/voya.git
cd voya

# Set up pre-commit hooks (recommended)
pip install pre-commit
pre-commit install

# Start development environment
docker compose up -d
```

## Daily Development Workflow

### 1. Create Feature Branch
```bash
# Always start from main
git checkout main
git pull origin main

# Create feature branch with descriptive name
git checkout -b feature/fix-undefined-names
# or
git checkout -b bugfix/password-reset-security
# or
git checkout -b docs/update-api-documentation
```

### 2. Make Changes
Work on your changes locally. The pre-commit hooks will automatically run when you commit.

### 3. Run Tests Locally (Optional but Recommended)

#### Backend Tests
```bash
cd backend_python
python -m pytest tests/ --verbose
```

#### Linting & Formatting
```bash
cd backend_python
ruff check .          # Check for issues
ruff check --fix .    # Auto-fix issues
ruff format .         # Format code
mypy app/             # Type checking
bandit -r app/        # Security scan
```

#### End-to-End Tests
```bash
# Start test environment
docker compose -f compose.test.yaml up -d

# Run tests
cd testing
npm run test:all

# View results
npm run test:report
```

### 4. Push and Create PR
```bash
# Push your branch
git push -u origin feature/fix-undefined-names

# Create pull request using GitHub CLI
gh pr create --title "Fix undefined names in user display" --body "
## Changes
- Fixed snake_case to camelCase conversion in user profile
- Updated API response mapping
- Added test for name display

## Testing
- [x] Backend tests pass
- [x] Frontend builds successfully
- [x] Manual testing on local environment

Closes #123
"

# Or create PR through GitHub web interface
gh pr view --web
```

### 5. Code Review Process
- **Automatic checks**: CI will run all tests automatically
- **Required approval**: 1 team member must approve
- **Review guidelines**: See [Code Review Guide](CODE_REVIEW.md) for checklist and test requirements
- **Self-review first**: Always review your own diff before requesting review
- **Review team**: Roel, Martijn can approve
- **Self-review alone allowed for**: Documentation-only changes, minor config fixes

> **Infrastructure reminder**: If your PR adds or changes environment variables,
> secrets, or feature flags, you must also update the Terraform configuration
> (`terraform/environments/`) for all environments (staging, test, prod).
> Manual AWS changes will be overwritten on the next Terraform apply or deploy.
> See the Infrastructure checklist in [Code Review Guide](CODE_REVIEW.md).

### 6. Merge and Cleanup
```bash
# After PR is approved and merged
git checkout main
git pull origin main
git branch -d feature/fix-undefined-names  # Delete local branch
git remote prune origin                    # Clean up remote tracking
```

## Local Development Commands

### Pre-commit Hooks
```bash
# Install (one-time setup)
pre-commit install

# Run manually on all files
pre-commit run --all-files

# Skip pre-commit hooks (if needed)
git commit --no-verify -m "WIP: debugging issue"
```

### Testing Commands

#### Python Backend
```bash
cd backend_python

# Run all tests
python -m pytest tests/ --verbose

# Run specific test file
python -m pytest tests/unit_tests/test_auth.py -v

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=html

# Run only unit tests
python -m pytest tests/unit_tests/ -m unit

# Run integration tests
python -m pytest tests/ -m integration
```

#### Frontend
```bash
cd frontend-v2

# Run tests
npm run test

# Run tests with coverage (CI-style)
npm run test:coverage

# Build
npm run build
```

#### End-to-End Tests
```bash
cd testing

# Run all tests
npm run test:all

# Run specific test suite
npm run test:auth           # Authentication tests
npm run test:diagnostics    # System health checks

# Run in headed mode (see browser)
npm run test:headed

# Debug mode
npm run test:debug

# View test report
npm run test:report
```

### Docker Commands
```bash
# Development environment
docker compose up -d              # Start all services
docker compose logs -f backend    # View backend logs
docker compose down               # Stop all services

# Test environment (isolated)
docker compose -f compose.test.yaml up -d
docker compose -f compose.test.yaml down

# Rebuild after dependency changes
docker compose up -d --build
```

## CI/CD Pipeline

### What Runs Automatically
When you create a PR, GitHub Actions will automatically:

1. **Backend Tests**: Run all Python tests (60+ test files)
2. **Frontend Build**: Ensure React app builds successfully
3. **Admin Build**: Ensure admin dashboard builds
4. **Linting**: Run ruff, mypy, bandit on Python code
5. **E2E Tests**: Run full Playwright test suite (85% pass rate)

### Check Results
```bash
# View PR status
gh pr status

# View detailed checks
gh pr checks

# View specific run logs
gh run list
gh run view <run-id>
```

## Team Coordination

### Current Team
- **Roel**: Admin, can approve PRs and deploy
- **Martijn**: Admin, can approve PRs and deploy
- **Marijke**: Admin, can approve PRs and deploy
- **AI Prompt Contributor**: Can create PRs, focus on prompt improvements

### Communication
- **PR Reviews**: Use GitHub PR comments for technical discussion
- **Urgent Issues**: Direct communication + GitHub Issues
- **Documentation**: Update this file for workflow changes

### Emergency Procedures
- **Hotfixes**: Can be merged with admin override if reviewer unavailable
- **Production Issues**: Direct fix to main with immediate PR for review
- **CI Failures**: Check logs, fix locally, push fix

## GitHub Labels System

### Label Structure

Voya uses a prefix-based label system organized into four groups. Labels serve two purposes:
1. **Type classification**: What kind of work is this?
2. **Pipeline status**: Where is this ticket in the workflow?

### Group 1: status/ — Pipeline Position

These labels track where a ticket is in the agentic pipeline. **Only one `status/` label should be active on a ticket at a time.** Each transition removes the previous `status/` label as the new one is added (see the Lifecycle Example below).

| Label | Meaning |
|-------|---------|
| `status/needs-clarification` | Blocked — ticket-creator flagged missing info, human must resolve |
| `status/ready-to-split` | Ticket-creator done, waiting for ticket-splitter |
| `status/ready-to-code` | Ticket-splitter done, ready for coding agent |
| `status/in-progress` | Coding agent is currently working this |
| `status/in-review` | PR raised, review agent running |
| `status/ready-to-promote` | Passed review, can be promoted from test → staging |
| `status/blocked` | Depends on another ticket that isn't done yet |

### Group 2: source/ — Origin

Where did this ticket come from? **Only one `source/` label should be active on a ticket at a time** — they describe origin, which is a single fact. Specifically: when the ticket-creator acts on a session-originated trigger issue, the **trigger** issue keeps `source/session` and each **derived** issue the agent files gets `source/agent` (not both). The lineage from derived → trigger is preserved through the "Context" section of the derived issue's body, not through duplicated labels.

| Label | Meaning |
|-------|---------|
| `source/session` | Holds the transcript of a Ross frontend session (trigger issue for ticket-creator runs) |
| `source/agent` | Filed by an agent (ticket-creator or splitter) |
| `source/manual` | Created by a human directly |
| `source/review` | Raised by the review agent during PR review |

### Group 3: area/ — System Component

What part of the system does this affect? The "Deprecated equivalent" column lists the unprefixed labels the `area/*` scheme supersedes — those should be removed from the repo when encountered.

| Label | Deprecated equivalent |
|-------|-----------------------|
| `area/frontend` | frontend |
| `area/backend` | backend |
| `area/infrastructure` | infrastructure |
| `area/ci-cd` | ci, automated |
| `area/testing` | testing |
| `area/security` | security |
| `area/observability` | trace-review |
| `area/documentation` | documentation |

### Group 4: type/ — Work Type

What kind of work is it? The "Deprecated equivalent" column lists the unprefixed labels the `type/*` scheme supersedes.

| Label | Deprecated equivalent |
|-------|-----------------------|
| `type/bug` | bug |
| `type/feature` | enhancement |
| `type/task` | task |
| `type/technical-debt` | technical-debt |
| `type/needs-rewrite` | (new — from ticket-creator classification) |
| `type/dependency` | (new — from ticket-splitter, implement first) |

### Universal Labels (No Prefix)

These are standard GitHub conventions and intentionally kept unprefixed:
- `duplicate`
- `wontfix`
- `invalid`
- `good first issue`
- `help wanted`
- `question`

> **Note on priority:** there is no `priority/*` group today. If the team decides priority tracking is needed, introduce it as a dedicated prefix group (`priority/low`, `priority/medium`, `priority/high`, `priority/critical`) rather than mixing unprefixed priority labels into the universal set.

### Retired Labels

The following labels should be removed:
- `resolved` — GitHub issue closing is sufficient
- `questionable` — Replace with `status/needs-clarification` or `wontfix`
- `admin` — Too vague, use appropriate `area/` or `type/` labels

### Using Labels in Workflow

```bash
# Create issue with labels
gh issue create --label "type/bug,area/backend,status/ready-to-code"

# Add labels to existing issue
gh issue edit 123 --add-label "status/in-review"

# List issues by status
gh issue list --label "status/ready-to-code"

# View all labels
gh label list
```

### Label Lifecycle Example

Each transition **replaces** the previous `status/` label with the new one (status labels are mutually exclusive — see Group 1). `source/`, `area/`, and `type/` labels generally persist for the life of the ticket. Labels in **bold** are the ones changing at that step.

A typical ticket lifecycle looks like this:

```
Trigger issue (holds the session transcript, stays open as a reference)
  source/session + status/needs-triage

  → human comments "@claude create-tickets" →

Derived issue (a new issue filed by ticket-creator)
  source/agent + status/ready-to-split + area/frontend + type/needs-rewrite

  → ticket-splitter runs →
  Sub-tickets (filed by ticket-splitter, one per atomic unit of work)
  source/agent + status/ready-to-code + area/frontend + type/needs-rewrite

  → coding agent runs, PR raised →
  status/ready-to-code → status/in-review

  → review passes, merged, deployed to test →
  status/in-review → status/ready-to-promote
```

## Troubleshooting

### Common Issues
```bash
# Pre-commit hook failures
pre-commit run --all-files         # Fix all at once
git add .                          # Stage fixes
git commit -m "Fix linting issues" # Commit again

# Docker issues
docker compose down
docker system prune -f             # Clean up
docker compose up -d --build       # Rebuild

# Test failures
docker compose -f compose.test.yaml down  # Reset test env
docker compose -f compose.test.yaml up -d --wait
cd testing && npm run test:all             # Re-run

# Merge conflicts
git checkout main
git pull origin main
git checkout feature/my-branch
git rebase main                     # Resolve conflicts
git push --force-with-lease origin feature/my-branch
```

### Getting Help
1. Check this documentation
2. Look at recent PRs for examples
3. Ask team members
4. Check GitHub Actions logs for specific errors

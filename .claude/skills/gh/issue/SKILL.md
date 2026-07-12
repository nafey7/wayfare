---
name: gh:issue
description: Create and manage GitHub issues using project templates (task, bug, feature). Use when user asks to create issues, report bugs, or file feature requests.
disable-model-invocation: true
allowed-tools: Bash(gh issue:*), Bash(gh api:*)
argument-hint: [task|bug|feature] [title]
---

# Create GitHub Issue

Create a GitHub issue using project templates for $ARGUMENTS

## Quick Issue Creation

### Create task issue
```bash
gh issue create --template task.yml
```

### Create bug report
```bash
gh issue create --template bug_report.yml
```

### Create feature request
```bash
gh issue create --template feature_request.yml
```

## Issue Templates

The project has three standardized templates in `.github/ISSUE_TEMPLATE/`:

### Task Template (`task.yml`)
**Purpose**: General tasks, technical work, refactoring, documentation

**Required Fields**:
- Task Title
- Current behavior
- Expected behavior
- Context & Motivation
- Task Description
- Acceptance Criteria
- Task Type (Documentation, Refactoring, Frontend, Backend, etc.)

**Optional Fields**:
- Effort Estimate (XS–XL)

### Bug Report Template (`bug_report.yml`)
**Purpose**: Report bugs, issues, system problems

**Required Fields**:
- Bug Summary
- Business Impact
- Current behavior
- Expected behavior
- Reproduction Steps
- Technical Details
- Severity (Critical to Low)
- Frequency
- Fix Success Criteria

**Form field IDs (automation / webhooks):** The bug template uses `current-behavior` for “what happens today.” Older versions of the template used `actual-behavior` for that slot—update any scripts or integrations that referenced the old id.

### Feature Request Template (`feature_request.yml`)
**Purpose**: New features, enhancements, major functionality

**Required Fields**:
- Feature Title
- Current behavior
- Expected behavior
- Business Context
- Business Value
- User Story
- Technical Implementation
- Acceptance Criteria
- Success Criteria
- Priority
- Effort Estimate

## Direct Creation (Skip Template)

### Quick issue without template
```bash
gh issue create --title "[TASK] Your task title" --body "Description..."
```

### With labels
```bash
gh issue create \
  --title "[BUG] Login fails with OAuth" \
  --label "bug,high-priority" \
  --body "Bug description..."
```

### Assign to someone
```bash
gh issue create \
  --title "[FEATURE] Add export functionality" \
  --assignee @me \
  --template feature_request.yml
```

## Issue Management

### List all open issues
```bash
gh issue list
```

### List issues by label
```bash
gh issue list --label "bug"
gh issue list --label "high-priority"
```

### View specific issue
```bash
gh issue view 123
```

### Close issue
```bash
gh issue close 123 --reason "completed"
```

## Issue Naming Conventions

Use prefixes for clarity:
- **[TASK]** - `[TASK] Add personal information fields to profile page`
- **[BUG]** - `[BUG] Flight search returns incorrect airports`
- **[FEATURE]** - `[FEATURE] Implement real-time chat notifications`
- **[DOCS]** - `[DOCS] Update API authentication guide`

## Mandatory Requirements

All issues must include:

**Testing Requirements**:
- Add unit tests for new functionality
- Verify existing tests still pass
- Add regression tests for bug fixes

**Documentation Requirements**:
- Update CLAUDE.md with relevant changes
- Document new API endpoints
- Include configuration updates

## Search & Filter Issues

### Find issues by text
```bash
gh issue list --search "authentication"
```

### Filter by state
```bash
gh issue list --state open
gh issue list --state closed
gh issue list --state all
```

### Filter by assignee
```bash
gh issue list --assignee @me
```

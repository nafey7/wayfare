# Code Review Guide

Code review ensures quality, catches bugs early, and spreads knowledge across the team. Every PR should be reviewed before merging.

---

## Test Requirements Policy

### Standard Policy (All PRs)

| Change Type | Test Requirement |
|-------------|------------------|
| New functionality | Unit tests required |
| Bug fix | Regression test required (reproduces the bug) |
| Changed behavior | Updated tests required |
| Refactoring | Existing tests must still pass |

**Coverage Requirements:**
- Minimum: 80% for new code
- Critical paths: 100% (auth, payments, bookings)

See [Testing Standards](../backend_python/docs/TESTING_STANDARDS.md) for patterns.

### Urgent Bugfix Exception

For **critical production issues only**:

1. Merge the fix with reviewer approval
2. Create follow-up issue for missing tests (reference the PR)
3. Tests must be added within 1 week

**To use this exception:**
- State in PR description: "Urgent bugfix - follow-up issue for tests: #XXX"
- Reviewer must explicitly acknowledge the exception

### No Exceptions (Always Require Tests)

These changes **always** need tests before merge:
- Security fixes
- Payment/booking code
- Authentication/authorization changes
- Data migration scripts

---

## Review Checklist

### Testing (Check First)

- [ ] Tests exist for new/changed code
- [ ] Bug fixes have regression tests that would have caught the bug
- [ ] Tests cover success AND failure paths
- [ ] CI passes (all checks green)

### Functionality

- [ ] Code does what the PR description claims
- [ ] Edge cases handled (empty inputs, nulls, errors)
- [ ] Error handling is appropriate (not swallowed silently)

### Code Quality

- [ ] Type hints on public functions (Python)
- [ ] No blocking operations in async functions
- [ ] No hardcoded secrets or magic strings
- [ ] Follows existing patterns in the codebase
- [ ] No unnecessary complexity or over-engineering

### Security

- [ ] User input validated (Pydantic for Python)
- [ ] No sensitive data in logs
- [ ] SQL/NoSQL injection prevented
- [ ] Authentication/authorization checked where needed

### Infrastructure / Terraform

- [ ] New environment variables added to Terraform for **all environments** (staging, test, prod)
- [ ] New secrets added to the secrets module and wired into ECS task definitions
- [ ] Feature flags consistent across environments (unless intentionally different)
- [ ] Terraform changes applied or noted as pending in PR description

### Documentation

- [ ] Complex logic has explanatory comments
- [ ] CHANGELOG.md updated (user-facing changes)
- [ ] CLAUDE.md updated (if patterns or architecture changed)
- [ ] API docs updated (new/changed endpoints)

---

## How to Review

### Before Starting
1. Read the PR description and linked issue
2. Understand the context and intent

### During Review
1. Read the diff completely - don't skim
2. Check CI status (must pass before approval)
3. Verify test coverage matches changes
4. For complex changes, pull locally and test

### Approval Decisions

| Decision | When to Use |
|----------|-------------|
| **Approve** | All checklist items pass |
| **Approve with suggestions** | Minor improvements that are non-blocking |
| **Request changes** | Missing tests, security issues, broken functionality |

### Writing Review Comments

- Be specific and actionable ("Add null check on line 42" not "Handle edge cases")
- Explain *why*, not just *what* ("This could throw if user is null because...")
- Mark blocking vs non-blocking: use "Suggestion:" or "Nit:" for non-blocking
- Acknowledge good work when you see it

---

## PR Author Responsibilities

### Before Requesting Review
- [ ] **Self-review your own diff thoroughly** (read every changed line as if reviewing someone else's code)
- [ ] Ensure CI passes
- [ ] Write clear PR description with context
- [ ] Link related issues

### During Review
- Respond to all feedback (even if just acknowledging)
- Ask for clarification if feedback is unclear
- Don't take feedback personally - it's about the code

### After Review
- Create follow-up issues for deferred work
- Update PR based on feedback
- Re-request review after addressing changes

---

## Quick Reference

```
PR Ready for Merge?
├── CI passes? ─────────────────── No → Fix CI first
├── Tests for changes? ─────────── No → Add tests (or use urgent exception)
├── Reviewer approved? ─────────── No → Address feedback
├── All feedback addressed? ────── No → Respond to comments
└── Yes to all → Merge!
```

---

## References

- [Testing Standards](../backend_python/docs/TESTING_STANDARDS.md) - Unit test patterns, mocking, coverage
- [Coding Standards](../backend_python/docs/CODING_STANDARDS.md) - Full code review checklist (30+ items)
- [Team Workflow](TEAM_WORKFLOW.md) - Git workflow, PR process
- [CI/CD](CI_CD.md) - Pipeline details, troubleshooting

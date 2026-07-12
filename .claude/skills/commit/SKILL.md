---
name: commit
description: Create git commits with Conventional Commits format and optionally push to remote. Use when user asks to commit changes.
disable-model-invocation: true
allowed-tools: Bash(git:*)
argument-hint: [type] [scope] [description] [--push]
---

# /commit - Git Commit & Push Command

Execute a git commit with Conventional Commits format and push to remote.
All files should be committed (new and modified).

## Usage
```
/commit [type] [scope] [description] [--push]
```

## Parameters
- `type`: Type of change (feat, fix, docs, style, refactor, test, chore, etc.)
- `scope`: Component/area affected (optional)
- `description`: Brief description of changes
- `--push`: Also push to remote after commit

## Commit Types
- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation only
- **style**: Formatting, no code change
- **refactor**: Code restructuring
- **perf**: Performance improvement
- **test**: Adding tests
- **build**: Build system changes
- **ci**: CI configuration
- **chore**: Maintenance
- **revert**: Revert previous commit

## Message Format
```
<type>(<scope>): <description>
```
or without scope:
```
<type>: <description>
```

## Best Practices
- Atomic commits (one logical change)
- Present tense ("add" not "added")
- Imperative mood ("fix bug" not "fixes bug")
- No period at the end
- Reference issue numbers when relevant

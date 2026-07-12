---
name: lint
description: Run linting and formatting checks for backend (ruff, mypy, bandit) and frontend (eslint). Use when user asks to lint, format, or check code quality.
allowed-tools: Bash(ruff:*), Bash(mypy:*), Bash(bandit:*), Bash(npm run lint:*)
argument-hint: [backend|frontend|all]
---

# Run Linting & Formatting

@docs/CODE_QUALITY.md

Execute code quality checks for $ARGUMENTS

## Quick Lint All

### Backend (Python)
```bash
cd backend_python
ruff check --fix . && ruff format . && mypy app/ && bandit -r app/ -ll -c pyproject.toml
```

### Frontend (Vite)
```bash
cd frontend-v2
npm run lint
```

## Common Quick Fixes

### Auto-fix Backend Issues
```bash
cd backend_python
ruff check --fix .     # Auto-fix linting issues
ruff format .          # Format code
```

### Clear MyPy Cache
```bash
cd backend_python
rm -rf .mypy_cache && mypy app/
```

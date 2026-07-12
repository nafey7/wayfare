# Code Quality Guide

Code quality tools, linting, formatting, and type checking for the Voya platform.

## Tools Overview

### Backend (Python)
- **Ruff**: Fast linting & formatting (replaces flake8, isort, black)
- **MyPy**: Static type checking with strict mode
- **Bandit**: Security vulnerability scanning
- **Pre-commit**: Automated hooks for quality checks

### Frontend (React)
- **ESLint**: JavaScript/React linting
- **Prettier**: Code formatting (via ESLint)
- **Pre-commit**: Basic checks

## Ruff - Python Linting & Formatting

### Check for Issues
```bash
cd backend_python
ruff check .
```

### Auto-fix Issues
```bash
cd backend_python
ruff check --fix .
```

### Format Code
```bash
cd backend_python
ruff format .
```

### Check Formatting (CI mode)
```bash
cd backend_python
ruff format --check .
```

### Output for CI
```bash
cd backend_python
ruff check . --output-format=github
```

### Performance
- **10-100x faster** than Black + isort + flake8 combined
- Typically completes in < 1 second
- Single tool replaces multiple tools

## MyPy - Type Checking

### Full Type Check
```bash
cd backend_python
mypy app/
```

### With Caching (faster subsequent runs)
```bash
cd backend_python
mypy app/ --cache-dir=.mypy_cache
# First run: ~30s, subsequent: ~5s
```

### Specific Module
```bash
cd backend_python
mypy app/ai/intent_recognizer.py
```

### Clear Cache (if seeing stale errors)
```bash
cd backend_python
rm -rf .mypy_cache
mypy app/
```

## Bandit - Security Scanning

### Security Scan
```bash
cd backend_python
bandit -r app/
```

### With Config (skip low severity)
```bash
cd backend_python
bandit -r app/ -ll -c pyproject.toml
```

### JSON Output
```bash
cd backend_python
bandit -r app/ -f json -o bandit-report.json
```

## Frontend Linting

### ESLint
```bash
cd frontend-v2
npm run lint
```

### Auto-fix
```bash
cd frontend-v2
npm run lint -- --fix
```

### Specific File
```bash
cd frontend-v2
npx eslint src/features/chat/components/ChatBot.tsx
```

## Pre-commit Hooks

### Install Hooks
```bash
pip install pre-commit
pre-commit install                      # Commit hooks (fast: ruff, basic checks)
pre-commit install --hook-type pre-push # Push hooks (mypy, bandit - slower)
```

### Run All Hooks
```bash
pre-commit run --all-files
```

### Run Specific Hook
```bash
pre-commit run ruff        # Linting
pre-commit run mypy        # Type checking
pre-commit run bandit      # Security
```

### Hook Strategy
- **Commit hooks**: Fast checks (ruff format, ruff check) - runs in seconds
- **Push hooks**: Thorough checks (mypy, bandit) - runs before push
- This prevents slow commits while maintaining quality

## Configuration

### Python (pyproject.toml)
```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]

[tool.bandit]
exclude_dirs = ["tests", ".venv"]
skips = ["B101"]  # Skip assert warnings in tests
```

### Frontend (eslint.config.js)
frontend-v2 uses ESLint flat config with TypeScript, react-hooks, and react-refresh. See `frontend-v2/eslint.config.js`.

## Linting Standards

### Python
- **Line length**: 100 characters
- **Target**: Python 3.12
- **Rules**: Security, type hints, naming conventions, complexity
- **Import order**: stdlib → third-party → local (alphabetically)

### JavaScript/React
- **Config**: ESLint flat config (frontend-v2/eslint.config.js)
- **Plugins**: typescript-eslint, react-hooks, react-refresh
- **Rules**: React hooks, accessibility, best practices

## Common Issues & Fixes

### Ruff

**Import sorting**:
```bash
ruff check --select I --fix .
```

**Unused imports**:
```bash
ruff check --select F401 --fix .
```

**Show what would change**:
```bash
ruff check --diff .
```

### MyPy

**Ignore specific error**:
```python
result = api_call()  # type: ignore[attr-defined]
```

**Pydantic plugin** (already configured):
```toml
[tool.mypy]
plugins = ["pydantic.mypy"]
```

### ESLint

**Disable specific rule**:
```javascript
/* eslint-disable react-hooks/exhaustive-deps */
useEffect(() => {
  // ...
}, []);
/* eslint-enable react-hooks/exhaustive-deps */
```

## CI/CD Integration

Code quality checks run automatically in CI:

**Backend Jobs**:
1. Ruff linting & format check
2. MyPy type checking (with cache)
3. Bandit security scan

**Frontend checks**: Run locally with `cd frontend-v2 && npm run lint && npm run build`.

See `docs/CI_CD.md` for full CI configuration.

## Quick Quality Check

### Backend
```bash
cd backend_python
ruff check --fix . && ruff format . && mypy app/ && bandit -r app/ -ll -c pyproject.toml
```

### Frontend
```bash
cd frontend-v2
npm run lint && npm run build
```

## Performance Tips

### Ruff Speed
```bash
cd backend_python
time ruff check . && ruff format .
# Typically: < 1 second
```

### MyPy Caching
```bash
cd backend_python
mypy app/ --cache-dir=.mypy_cache
# First run: ~30s
# Subsequent runs: ~5s
```

### Pre-commit Optimization
- Fast checks on commit (< 10s)
- Thorough checks on push (< 60s)

**Policy**: See root `CLAUDE.md` → Pre-commit Hooks section for Boy Scout Rule and bypass guidelines.

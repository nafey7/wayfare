# Python Backend for Voya

**📖 For complete documentation, see `CLAUDE.md` in this directory.**

## Quick Start

```bash
cd backend_python
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Development
uvicorn app.main:app --reload --port 8000

# Quality checks
ruff check --fix . && ruff format . && mypy app/
```

## Documentation

See `CLAUDE.md` for:
- Complete setup instructions (Poetry, pip, Docker)
- Development commands and quality assurance
- Testing standards and coverage requirements
- API documentation and developer tools
- Pre-commit hooks and CI/CD integration
- Python coding standards and patterns

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/api/docs
- **API Tester**: http://localhost:8000/dev/api-tester.html (interactive testing)
- **OpenAPI JSON**: http://localhost:8000/openapi.json

---

**See `CLAUDE.md` for comprehensive backend documentation.**

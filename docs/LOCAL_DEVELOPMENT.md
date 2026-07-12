# Local Development Setup

Quick reference for daily development commands and troubleshooting.

**For initial setup and project overview, see [Root CLAUDE.md](../CLAUDE.md)**

## One-Time Setup

### 1. Install Pre-commit Hooks
```bash
# Install pre-commit (if not already installed)
pip install pre-commit

# Install the hooks (from project root)
pre-commit install

# Test the setup
pre-commit run --all-files
```

### 2. Environment Setup
```bash
# Copy environment template
cp .env.example .env
# Edit .env with your local configuration

# Start development environment (includes mock FlightLogic API)
docker compose up -d

# Verify services are running
docker compose ps
```

### 3. IDE Setup

The project uses `.editorconfig` for consistent code style across IDEs. Most modern editors support this automatically.

**Code Style Configuration**:
- ✅ **`.editorconfig`** - Auto-applied by most IDEs (VSCode, JetBrains, Sublime, etc.)
- ✅ **Pre-commit hooks** - Enforces Python (Ruff), YAML, JSON formatting
- 📋 **Standards**:
  - Python: 4 spaces, max line 120 chars
  - JavaScript/TypeScript: 2 spaces, max line 100 chars
  - Terraform/YAML/JSON: 2 spaces

**JetBrains IDEs (PyCharm, IntelliJ, WebStorm)**:
- `.idea/` directory is **NOT tracked** in git (user-specific settings)
- EditorConfig plugin is enabled by default
- Your local `.idea/` settings won't be deleted when pulling changes

**VSCode**:
- Install EditorConfig extension: `editorconfig.editorconfig`
- Python/JavaScript formatting handled by extensions + pre-commit hooks

**Important**: When you pull git changes that remove `.idea/` from tracking, your local `.idea/` directory will NOT be deleted. Git only removes tracking, not local files.

## FlightLogic Mock Server Setup

The project uses **mock FlightLogic API by default** for local development.

### Default Configuration

**Configuration Files**:
- ✅ **`.env`** (root) - Main configuration for all developers
- ❌ **`backend_python/.env`** - NOT NEEDED for most developers

No special configuration needed! The backend automatically uses `http://flightlogic-mock:8002` for flight searches.

### Using Real FlightLogic API

If you need to test against the real FlightLogic API:

**Option 1: Environment Variable Override** (Temporary)
```bash
FLIGHTLOGIC_API_URL=https://travelnext.works/api/aeroVE5 \
FLIGHTLOGIC_USER_ID=your_user_id \
FLIGHTLOGIC_PASSWORD=your_password \
  docker compose up -d backend
```

**Option 2: Local .env File** (Persistent)
```bash
# Create backend_python/.env with:
FLIGHTLOGIC_API_URL=https://travelnext.works/api/aeroVE5
FLIGHTLOGIC_USER_ID=your_user_id
FLIGHTLOGIC_PASSWORD=your_password
FLIGHTLOGIC_ACCESS_TYPE=Test
FLIGHTLOGIC_IP_ADDRESS=your_ip

# ⚠️  IMPORTANT: Remove these lines from root .env to avoid conflicts:
# Comment out or remove FLIGHTLOGIC_API_URL, FLIGHTLOGIC_ACCESS_TYPE, FLIGHTLOGIC_API_KEY
```

### Switching Between Mock and Real API

**Method 1: Edit backend_python/.env**
```bash
# To use MOCK (recommended):
# Remove or comment out all FLIGHTLOGIC_* variables from backend_python/.env

# To use REAL API:
# Add FLIGHTLOGIC_* variables to backend_python/.env as shown above

# Restart
docker compose restart backend
```

**Method 2: Shell Override**
```bash
# Override for single session (real API)
FLIGHTLOGIC_API_URL=https://travelnext.works/api/aeroVE5 docker compose up -d backend

# Revert to mock
docker compose restart backend
```

### Environment Variable Precedence

Docker Compose loads variables in this order (highest to lowest priority):

1. **Shell environment** - `FLIGHTLOGIC_API_URL=... docker compose up`
2. **`backend_python/.env`** - Loaded via `env_file` in compose
3. **Root `.env`** - Project defaults

**Key Points**:
- If `backend_python/.env` has `FLIGHTLOGIC_API_URL`, it overrides root `.env`
- To use mock server: Remove FlightLogic vars from `backend_python/.env`
- To use real API: Keep vars in `backend_python/.env`

### Verifying Configuration

```bash
# Check which FlightLogic URL backend is using
docker compose exec backend env | grep FLIGHTLOGIC_API_URL

# Should show:
# Mock:  FLIGHTLOGIC_API_URL=http://flightlogic-mock:8002/api/aeroVE5
# Real:  FLIGHTLOGIC_API_URL=https://travelnext.works/api/aeroVE5
```

## Stripe Payment Integration Setup

The project uses **Stripe** for payment processing with test mode for local development.

### Required Environment Variables

**Backend** (`.env` in root):
```bash
# Stripe API Keys (Test Mode)
STRIPE_SECRET_KEY=sk_test_51...
STRIPE_PUBLISHABLE_KEY=pk_test_51...

# Webhook Secret (for local webhook testing)
STRIPE_WEBHOOK_SECRET=whsec_...

# Stripe Connect Toggle
STRIPE_USE_CONNECT_TRANSFERS=true
```

### Getting Stripe API Keys

**Step 1: Create Stripe Account**
1. Sign up at https://stripe.com (if you don't have an account)
2. Verify email address
3. Complete account setup

**Step 2: Get Test API Keys**
1. Go to https://dashboard.stripe.com/test/apikeys
2. Copy **Publishable key** (starts with `pk_test_`)
3. Reveal and copy **Secret key** (starts with `sk_test_`)
4. Add both to `.env` file

**Step 3: Get Webhook Secret** (for webhook testing)

See [WEBHOOKS.md](WEBHOOKS.md) for complete webhook setup guide.

**Quick setup**:
1. Start ngrok: `cd backend_python && ./test_webhook_with_ngrok.sh`
2. Create webhook: `python test_webhook_setup.py create-local-webhook https://YOUR-NGROK-URL.ngrok.io`
3. Copy secret from output and add to `.env`
4. Restart backend

### Testing Payments Locally

**Option 1: Demo Mode** (No Stripe account needed)
1. Open http://localhost:8000/dev/flight-booker/
2. Search and select flight
3. Fill passenger data
4. Select "Demo Mode (Checkbox)" payment
5. Check "I confirm payment" and complete booking

**Option 2: Stripe Test Mode** (Requires Stripe account)
1. Configure Stripe keys in `.env` (see above)
2. Open flight-booker or API tester
3. Select "Stripe Mode" payment
4. Use Stripe test cards:
   - **Success**: `4242 4242 4242 4242`
   - **Decline**: `4000 0000 0000 0002`
   - Expiry: Any future date, CVC: Any 3 digits
5. Complete payment and booking

### Stripe Connect Configuration

**What is Stripe Connect?**
- Splits payments between platform (Voya) and suppliers (e.g., FlightLogic)
- Automatically calculates 5% platform fee
- Transfers 95% to supplier account

**Setup** (Already configured for development):
- Platform account: `acct_1SIqE7PD9V3ngpza` (Voya)
- Supplier account: `acct_1SIqFwAcjtxA6BLd` (FlightLogic)
- Platform fee: 5% (configured in `app/domains/payment/constants.py`)

**Testing Without Connect** (Optional):
```bash
# Disable Connect transfers for testing
echo "STRIPE_USE_CONNECT_TRANSFERS=false" >> .env
docker compose restart backend

# All funds go to platform account, fee tracked in metadata only
```

### Verifying Stripe Configuration

```bash
# Check Stripe keys are loaded
docker compose exec backend env | grep STRIPE

# Should show:
# STRIPE_SECRET_KEY=sk_test_...
# STRIPE_PUBLISHABLE_KEY=pk_test_...
# STRIPE_WEBHOOK_SECRET=whsec_... (if configured)
# STRIPE_USE_CONNECT_TRANSFERS=true
```

### Stripe Resources

- **Test Dashboard**: https://dashboard.stripe.com/test/dashboard
- **API Keys**: https://dashboard.stripe.com/test/apikeys
- **Webhooks**: https://dashboard.stripe.com/test/webhooks
- **Payments Log**: https://dashboard.stripe.com/test/payments
- **Test Cards**: https://stripe.com/docs/testing#cards
- **Voya Payment Docs**: [PAYMENTS.md](PAYMENTS.md)
- **Webhook Setup**: [WEBHOOKS.md](WEBHOOKS.md)

## Daily Commands

### Linting & Testing

#### Python Backend (Automatic with pre-commit)
```bash
cd backend_python

# Manual linting
ruff check .              # Check for issues
ruff check --fix .        # Auto-fix issues
ruff format .             # Format code

# Type checking
mypy app/                 # Type check

# Security scanning
bandit -r app/            # Security scan

# Testing
python -m pytest tests/ --verbose           # All tests
python -m pytest tests/unit_tests/ -v       # Unit tests only
python -m pytest tests/ -m integration      # Integration tests only
```

#### Frontend
```bash
cd frontend-v2

# Development server
npm run dev               # Hot reload at localhost:3002

# Testing
npm run test              # Vitest interactive
npm run test:coverage     # Run once with coverage

# Building
npm run build             # Production build (outputs to dist/)
```

#### End-to-End Tests
```bash
# Start isolated test environment
docker compose -f compose.test.yaml up -d

cd testing

# Install Playwright browsers (first time)
npx playwright install

# Run tests
npm run test:all          # All tests
npm run test:auth         # Auth tests only
npm run test:diagnostics  # System checks

# View results
npm run test:report       # HTML report at localhost:9323

# Debug mode
npm run test:headed       # See browser
npm run test:debug        # Step through
```

### Docker Management

#### Development Environment
```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f                    # All services
docker compose logs -f backend           # Backend only
docker compose logs -f frontend-vite          # Frontend only

# Restart specific service
docker compose restart backend

# Stop everything
docker compose down

# Rebuild after changes
docker compose up -d --build
```

#### Test Environment
```bash
# Start test stack (isolated)
docker compose -f compose.test.yaml up -d --wait

# Check test services
docker compose -f compose.test.yaml ps

# Stop test stack
docker compose -f compose.test.yaml down
```

#### Cleanup
```bash
# Remove stopped containers
docker container prune -f

# Remove unused images
docker image prune -f

# Remove everything (nuclear option)
docker system prune -af
```

### Git Workflow

#### Pre-commit Hooks
```bash
# Manual run (if hooks aren't working)
pre-commit run --all-files

# Skip hooks (emergency only)
git commit --no-verify -m "Emergency fix"

# Update hooks
pre-commit autoupdate
```

#### Branch Management
```bash
# Start new feature
git checkout main
git pull origin main
git checkout -b feature/my-feature

# Push and create PR
git push -u origin feature/my-feature
gh pr create --title "My Feature" --body "Description"

# After merge, cleanup
git checkout main
git pull origin main
git branch -d feature/my-feature
```

## Service URLs

### Development
- **Frontend**: http://localhost:3002
- **Backend API**: http://localhost:8000/api
- **API Docs**: http://localhost:8000/api/docs
- **Database Admin**: http://localhost:8081
- **Email Testing**: http://localhost:8025

### Testing (when test stack running)
- **Test (Backend serves SPA)**: http://localhost:8001
- **Test Backend**: http://localhost:8001/api
- **Test Database**: http://localhost:8082
- **Test Email**: http://localhost:8026
- **Test Reports**: http://localhost:9323

## Troubleshooting

### Common Issues

#### Pre-commit Hooks Not Running
```bash
# Reinstall hooks
pre-commit uninstall
pre-commit install

# Check hook status
pre-commit --version
ls -la .git/hooks/
```

#### Docker Port Conflicts
```bash
# Check what's using ports
lsof -i :3000
lsof -i :8000

# Stop conflicting services
docker compose down
# Kill specific processes if needed
```

#### Python Import Errors
```bash
cd backend_python

# Check Python path
python -c "import sys; print(sys.path)"

# Install in development mode
pip install -e .
```

#### Frontend Build Failures
```bash
cd frontend-v2

# Clear cache
rm -rf node_modules package-lock.json
npm install

# Check Node version
node --version  # Should be 20.x
```

#### Frontend-v2 (Vite) in Docker: Missing npm package

When you add or change dependencies in `frontend-v2/package.json` (e.g. `npm install @revolut/checkout` on your machine), the **Docker** dev container uses a **named volume** for `node_modules`, so it does not see your host’s `node_modules`. Install inside the container so the volume is updated:

```bash
# One-off: install deps in the container (updates the node_modules volume)
docker compose run --rm frontend-vite npm install

# Restart the dev server so it picks up the new modules
docker compose up -d frontend-vite
```

If the container is already running:

```bash
docker compose exec frontend-vite npm install
# Then restart the service (or restart the container)
docker compose restart frontend-vite
```

**When to rebuild the image:** Rebuild when the Dockerfile or base Node version changes: `docker compose build frontend-vite && docker compose up -d frontend-vite`. For dependency-only changes, `npm install` in the container (above) is enough and faster.

#### Test Database Issues
```bash
# Reset test database
docker compose -f compose.test.yaml down
docker volume prune -f
docker compose -f compose.test.yaml up -d --wait

# Check database connection
docker compose -f compose.test.yaml exec mongodb-test mongosh --eval "db.adminCommand('ping')"
```

#### Backend Still Using Real API
```bash
# 1. Verify backend_python/.env is removed/empty
cat backend_python/.env 2>/dev/null || echo "File doesn't exist (good!)"

# 2. Check root .env has mock settings
grep FLIGHTLOGIC .env
# Should show: FLIGHTLOGIC_API_URL=http://flightlogic-mock:8002/api/aeroVE5

# 3. Recreate backend container
docker compose up -d --force-recreate backend
```

#### Mock Server Not Responding
```bash
# 1. Check mock server is running
docker compose ps flightlogic-mock

# 2. Check health
curl http://localhost:8002/health

# 3. Restart mock server
docker compose restart flightlogic-mock
```

### Performance Tips

#### Faster Testing
```bash
# Run specific test files only
python -m pytest tests/unit_tests/test_auth.py
npx playwright test auth/login.spec.js

# Run with multiple workers
python -m pytest tests/ -n auto  # (requires pytest-xdist)
```

#### Faster Docker Builds
```bash
# Use BuildKit
export DOCKER_BUILDKIT=1

# Build with cache
docker compose build --parallel
```

#### Pre-commit Performance
```bash
# Run only on changed files (default)
pre-commit run

# Skip slow checks during development
git commit --no-verify -m "WIP"
# Then run full check before PR
pre-commit run --all-files
```

## Profile photos / S3 (MinIO locally)

User profile photos are stored in a private S3 bucket. **Locally, MinIO** stands in for AWS — no credentials, no network, no real cloud bucket.

```bash
# Bring up dev stack (includes minio + minio-init)
docker compose up -d

# Open the MinIO web console
open http://localhost:9001      # creds: voya-local / voya-local-secret

# Inspect the bucket
mc alias set local http://localhost:9000 voya-local voya-local-secret
mc ls local/myvoya-local-photos
```

The `minio-init` one-shot container creates the bucket on every boot — wiping with `docker compose down -v` is safe (the bucket is recreated; user `photo_key` strings will then 404 through imgproxy and the frontend falls back to initials).

`compose.test.yaml` runs an isolated `minio-test` on ports `9002`/`9003`, so dev and test can run side-by-side without clashing.

# Voya Documentation

**📖 Main navigation hub: See root `CLAUDE.md` for role-based quick starts**

## Purpose

This directory contains comprehensive technical documentation for the Voya travel platform. For quick navigation and getting started, see the root `CLAUDE.md` file.

## Documentation Structure

### Architecture & Design
- **ARCHITECTURE.md** (12K) - System design, DDD structure, sticky intents, data flow
- **DOCUMENTATION_MAP.md** (16K) - Complete navigation guide with role-based paths

### Infrastructure & Deployment
- **TERRAFORM.md** (490 lines) - Complete Terraform setup, infrastructure management
- **DEPLOYMENT.md** (418 lines) - Deployment runbook, rollback procedures, monitoring

### Development Guides
- **docker-mock-server.md** - FlightLogic mock server setup, Docker environment variables
- **FRONTEND_BACKEND_COLLABORATION.md** - API contracts, integration patterns, snake_case ↔ camelCase
- **LOCAL_DEVELOPMENT.md** (5.4K) - Environment setup, tools, troubleshooting
- **TEAM_WORKFLOW.md** (6.6K) - Git workflow, collaboration, code review

### Quality & Testing
- **CODE_QUALITY.md** (4.9K) - Linting, type checking, security tools (Ruff, MyPy, Bandit)
- **TESTING.md** (4.3K) - E2E testing with Playwright, test environment setup
- **CI_CD.md** (8.4K) - GitHub Actions workflows, debugging failed builds

### Features & Troubleshooting
- **FLIGHT_FEATURES.md** (5.9K) - Advanced flight search, booking, NLP features
- **TROUBLESHOOTING.md** (16K) - Common issues, recent fixes, debug strategies

## Quick Navigation by Role

### 🐍 Backend Developer
Start here:
1. Root `CLAUDE.md` → Backend quick start
2. `backend_python/CLAUDE.md` → Backend patterns
3. `ARCHITECTURE.md` → System design
4. `backend_python/docs/CODING_STANDARDS.md` → Python standards

### ⚛️ Frontend Developer
Start here:
1. Root `CLAUDE.md` → Frontend quick start
2. `docs/FRONTEND_BACKEND_COLLABORATION.md` → React/API patterns
3. `FRONTEND_BACKEND_COLLABORATION.md` → API integration
4. `ARCHITECTURE.md` → Data flow

### 🧪 QA/Testing Developer
Start here:
1. Root `CLAUDE.md` → Testing quick start
2. `testing/CLAUDE.md` → Playwright patterns
3. `TESTING.md` → Testing strategy
4. `backend_python/docs/TESTING_STANDARDS.md` → Unit tests

### 🔧 Full-stack Developer
Start here:
1. Root `CLAUDE.md` → Complete overview
2. `ARCHITECTURE.md` → System design
3. `DOCUMENTATION_MAP.md` → Full navigation
4. All CLAUDE.md files in subdirectories

### 🚀 DevOps/Infrastructure
Start here:
1. `TERRAFORM.md` → Infrastructure setup and management
2. `DEPLOYMENT.md` → Deployment procedures and monitoring
3. `../terraform/README.md` → Quick reference
4. `../terraform/environments/staging/README.md` → Environment configuration

## Documentation Principles

- **Single Source of Truth**: Each concept documented in exactly one place
- **Progressive Disclosure**: Quick start → Detailed guide → Reference
- **Role-Based**: Navigation tailored to developer responsibilities
- **Concise**: Avoid bloat, link to deeper docs instead of duplicating

---

**Start with root `CLAUDE.md` for your role-based quick start guide.**

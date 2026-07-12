# Voya - AI-Powered Travel Platform

Your intelligent travel agent for seamless trip planning and booking with production-ready testing infrastructure.

## 🎯 **Quick Start with Docker (Recommended)**

The fastest way to get Voya running with complete environment isolation:

```bash
# Clone and start all services
git clone <repository-url>
cd voya
docker compose up -d

# Access the application
open http://localhost:3002
```

**Service URLs:**
- 🌐 **Frontend**: http://localhost:3002
- 🔧 **Backend API**: http://localhost:8000/api
- 📖 **API Documentation**: http://localhost:8000/api/docs
- 🗄️ **Database Admin**: http://localhost:8081 (Mongo Express)
- 📧 **Email Testing**: http://localhost:8025 (MailHog)

## 🚀 **Features**

- **🤖 AI Chatbot**: Powered by Google Gemini for intelligent travel recommendations
- **✈️ Advanced Flight Search**: Smart date parsing, natural language support, and curated results (see `docs/FLIGHT_FEATURES.md`)
- **📅 Trip Planning**: Complete itinerary management with calendar integration
- **🔐 Google OAuth**: Secure authentication with Google Sign-In
- **💬 Real-time Chat**: Persistent conversation history with sound notifications
- **🧪 Production-Ready Testing**: Complete environment isolation with comprehensive test coverage

## 🏗️ **Architecture**

### **Frontend** (`/frontend-v2`)
- **React 18.2** with Material-UI components (Vite)
- **Redux Toolkit** state management
- **Google Maps & OAuth** integration
- **Real-time AI chat** with context management

### **Backend** (`/backend_python`)
- **Python FastAPI** with MongoDB (Motor ODM)
- **Google Gemini AI** integration
- **FlightLogic API** for travel data
- **JWT authentication** with secure token management
- **Email system** with MailHog (dev) and SendGrid (prod)

### **Testing Infrastructure** (`/testing`)
- **Playwright** end-to-end testing (Chrome + Firefox)
- **Complete test isolation** with dedicated database and services
- **Email integration testing** with MailHog
- **Comprehensive test coverage** with automated reporting

## 🧪 **Testing & Quality Assurance**

### **Run Tests**
```bash
cd testing
npm run test:all        # All tests
npm run test:auth       # Authentication tests
npm run test:report     # View HTML report with screenshots
```

### **Test Environment Features**
- ✅ **Complete Isolation**: Separate `voya_test` database and `voya-test-` containers
- ✅ **Email Testing**: Full MailHog integration with link extraction
- ✅ **Database Cleanup**: Automatic test data cleanup between runs
- ✅ **Cross-Browser**: Chrome and Firefox with screenshot capture
- ✅ **Environment Detection**: Automatic dev/test configuration switching

## 🛠️ **Development Setup**

### **Prerequisites**
- **Docker & Docker Compose** (recommended)
- **Node.js 18+** (for local frontend development)
- **Python 3.12+** (for local backend development)

### **Environment Configuration**

Create environment files from examples:
```bash
# Main environment (required for Docker)
cp .env.example .env

# Backend-specific environment
cp backend_python/.env.example backend_python/.env

# Testing environment (for test isolation)
cp .env.testing.example .env.testing
```

### **Docker Development (Recommended)**

#### **Start Development Stack**
```bash
docker compose up -d                    # Start all services
docker compose logs -f frontend-vite         # View frontend logs
docker compose logs -f backend          # View backend logs
docker compose down                     # Stop all services
```

#### **Start Test Stack (Isolated)**
```bash
docker compose -f compose.test.yaml up -d
```

**Test Environment Ports:**
| Service | Port |
|---------|------|
| Backend (SPA) | 8001 |
| Backend API | 8001 |
| MongoDB | 27018 |
| Mongo Express | 8082 |
| MailHog | 8026 |
| FlightLogic Mock | 8004 |

> **Note**: Test environment uses production-style builds (root Dockerfile) vs dev's hot-reload volumes.

### **Local Development Setup**

#### **Frontend**
```bash
cd frontend-v2
npm install
npm run dev                 # http://localhost:3002
npm run build               # Production build (outputs to dist/)
```

#### **Backend (Python)**
```bash
cd backend_python

# Option 1: Poetry (recommended)
poetry install
poetry run python run.py

# Option 2: Virtual environment + pip
python -m venv .venv
source .venv/bin/activate    # Linux/macOS
# .venv\Scripts\activate     # Windows
pip install -r requirements.txt
python run.py
```

## 🔐 **Security Features**

### **Production-Ready Security**
- **Token Generation**: Cryptographically secure token generation using `secrets.token_urlsafe(32)` (256-bit entropy)
- **JWT Authentication**: Secure token-based authentication with proper expiration handling
- **Environment Isolation**: Complete separation of test/dev data preventing cross-contamination
- **Email Security**: MailHog prevents accidental email sends in development
- **Database Security**: Proper authentication and environment-specific access controls

## 🎨 **Build System**

### **Docker Build Options**

**Fast pip build (default):**
```bash
docker compose up -d --build
```

**Poetry build (for dependency changes):**
```bash
USE_POETRY=true docker compose up -d --build
```

### **Cross-Platform Support**
- ✅ **Windows, macOS, Linux** compatible
- ✅ **Poetry or pip** dependency management
- ✅ **Cross-platform scripts** replacing Windows-specific tools
- ✅ **Docker standardization** for consistent environments

## 📊 **Project Status**

### **✅ Production Ready**
- **Authentication**: Complete Google OAuth + JWT flow
- **AI Integration**: Gemini API with structured responses
- **Testing Infrastructure**: Comprehensive test coverage with full isolation
- **Docker Infrastructure**: Complete containerization with test separation
- **Email System**: MailHog (dev) + SendGrid (prod) integration

### **⚠️ In Development**
- **Trip Management**: Backend CRUD operations (frontend UI complete)
- **Settings Persistence**: Frontend-backend integration
- **Flight Integration**: Connecting search to trip planning workflow

### **📋 Known Issues**
- **"undefined undefined" names**: Backend snake_case vs frontend camelCase mapping
- **404 routes**: Missing `/inspirations` route for "Explore More" button
- **Mock data**: Some frontend components show placeholder data

## 🚀 **Deployment**

**For complete deployment and configuration details, see [CLAUDE.md](./CLAUDE.md) → Environment Variables**

### **Quick Docker Deployment**
```bash
# Configure environment variables (see CLAUDE.md for details)
cp .env.example .env

# Start production services
docker compose up -d

# Verify health
curl http://localhost:8000/health
```

## 🔧 **Troubleshooting**

### **Common Issues**
- **Port conflicts**: Ensure ports 3000, 8000, 8081, 27017 are available
- **Database connection**: Check MongoDB container status with `docker compose ps`
- **Test isolation**: Use separate test environment to avoid data conflicts
- **Email testing**: Verify MailHog is running at http://localhost:8025

### **Development Commands**
```bash
# Check service status
docker compose ps

# View all logs
docker compose logs

# Restart specific service
docker compose restart backend

# Clean rebuild
docker compose down && docker compose up -d --build
```

## 📚 **Documentation**

### **Getting Started**
- **[CLAUDE.md](./CLAUDE.md)** - Main documentation hub with role-based quick starts

### **Technical Documentation**
- **[docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)** - System design, DDD, and sticky intents
- **[docs/FLIGHT_FEATURES.md](./docs/FLIGHT_FEATURES.md)** - Advanced flight search features
- **[docs/TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[docs/CI_CD.md](./docs/CI_CD.md)** - GitHub Actions workflows

### **Development Guides**
- **[backend_python/CLAUDE.md](./backend_python/CLAUDE.md)** - Python/FastAPI development
- **[docs/FRONTEND_BACKEND_COLLABORATION.md](./docs/FRONTEND_BACKEND_COLLABORATION.md)** - React/API integration
- **[testing/CLAUDE.md](./testing/CLAUDE.md)** - E2E testing with Playwright

## 🤝 **Contributing**

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Run tests**: `cd testing && npm run test:all`
4. **Commit changes**: `git commit -m 'Add amazing feature'`
5. **Push to branch**: `git push origin feature/amazing-feature`
6. **Open Pull Request**

### **Development Workflow**
- ✅ Use **Docker Compose** for consistent environments
- ✅ Run **tests** before committing (`npm run test:all`)
- ✅ Follow **commit conventions** from recent strategic organization
- ✅ Document **security considerations** for any auth/token changes

---

**🎉 Voya features production-ready testing infrastructure with complete environment isolation and comprehensive Docker development workflow!**

*Built with ❤️ for seamless travel planning*

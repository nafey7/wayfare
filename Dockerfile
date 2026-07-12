# -------------------------------------------------
# 1️⃣  Build the Vite front‑end (frontend-v2)
# -------------------------------------------------
FROM node:20-alpine AS frontend-build-npm
WORKDIR /app/frontend-v2

# Google OAuth client ID (public, embedded in frontend JS bundle)
ARG VITE_GOOGLE_CLIENT_ID=""
ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID

# Google Maps API key (client-side map rendering)
ARG VITE_GOOGLE_MAPS_API_KEY=""
ENV VITE_GOOGLE_MAPS_API_KEY=$VITE_GOOGLE_MAPS_API_KEY

# Google Maps Map ID (required for AdvancedMarker on hotels/itinerary maps)
ARG VITE_GOOGLE_MAPS_MAP_ID=""
ENV VITE_GOOGLE_MAPS_MAP_ID=$VITE_GOOGLE_MAPS_MAP_ID

# Environment (development|staging|production) - drives Revolut payment mode, logging, etc.
ARG VITE_ENV=""
ENV VITE_ENV=$VITE_ENV

# Strapi CMS (landing / home content). Token is public in the bundle — scope read-only in Strapi.
ARG VITE_STRAPI_URL=""
ENV VITE_STRAPI_URL=$VITE_STRAPI_URL
ARG VITE_STRAPI_API_TOKEN=""
ENV VITE_STRAPI_API_TOKEN=$VITE_STRAPI_API_TOKEN

# API base URL baked into the frontend bundle. Empty/unset is the common case
# for prod/staging/test because the frontend is served from the same origin as
# the API (backend serves SPA) — baseApi.ts then falls back to '/api'
# (same-origin relative). Override this only for dev when Vite is served on a
# different port than the backend.
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL

# Copy only the files needed for a clean install
COPY frontend-v2/package.json frontend-v2/package-lock.json* .

# Install deps
RUN npm install

# Copy everything else and build (tsc + vite build → dist/)
COPY frontend-v2/ .
RUN npm run build

# -------------------------------------------------
# 2️⃣  Runtime image
# -------------------------------------------------
FROM python:3.12-alpine
WORKDIR /app/backend

# Accept build arguments
ARG USE_POETRY=false
ARG COMMIT_HASH=unknown
ARG GIT_VERSION=unknown

# Install system dependencies including cairo for xhtml2pdf/pycairo
RUN apk add --no-cache \
    curl \
    gcc musl-dev \
    cairo-dev pango-dev gdk-pixbuf-dev \
    pkgconfig

# Install dependencies based on USE_POETRY flag
# Poetry path: Install Poetry and use pyproject.toml + poetry.lock
RUN if [ "$USE_POETRY" = "true" ]; then \
        pip install --no-cache-dir poetry; \
    fi

# Copy dependency files
COPY backend_python/requirements.txt .
COPY backend_python/pyproject.toml* backend_python/poetry.lock* ./

# Install dependencies using Poetry or pip
RUN if [ "$USE_POETRY" = "true" ]; then \
        # Configure Poetry for container use (no virtual env) \
        poetry config virtualenvs.create false && \
        # Install only main dependencies (exclude dev group) \
        poetry install --only=main --no-interaction --no-ansi; \
    else \
        # Traditional pip install from pinned requirements.txt \
        pip install --no-cache-dir -r requirements.txt; \
    fi

# Copy source code
COPY backend_python/ .

# Copy the compiled static front‑end (Vite outputs to dist/)
COPY --from=frontend-build-npm /app/frontend-v2/dist ./static

# Install uvicorn explicitly (and any other missing CLI tools)
RUN pip install --no-cache-dir uvicorn

# Environment vars (use a .env in prod)
ENV DATABASE_NAME=voya \
    ADMIN_EMAILS=admin@myvoya.ai,dev@myvoya.ai \
    SENDGRID_FROM_EMAIL=no-reply@myvoya.ai \
    PORT=80 \
    ENVIRONMENT=production \
    DEBUG=False \
    FRONTEND_URL=https://app.myvoya.ai \
    ENABLE_DEV_TOOLS=true \
    GIT_COMMIT_HASH=${COMMIT_HASH} \
    GIT_VERSION=${GIT_VERSION}

EXPOSE ${PORT}

# Health‑check
HEALTHCHECK --interval=30s --timeout=5s \
  CMD curl -f http://localhost:${PORT}/health || exit 1

# Start the app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]

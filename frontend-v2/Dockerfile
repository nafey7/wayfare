# Frontend v2 Dockerfile for Vite development
FROM node:20-alpine

# Install additional tools for development
RUN apk add --no-cache git wget

# Create app directory first as root
WORKDIR /app

# Set up proper permissions - create directories that will be written to
RUN mkdir -p /app/node_modules /app/.npm /app/dist && \
    chown -R node:node /app

# Switch to node user (UID 1000, GID 1000)
USER node

# Copy package files with correct ownership
COPY --chown=node:node package*.json ./

# Install dependencies with fallback for sync issues
RUN npm ci --cache /app/.npm --prefer-offline --loglevel=warn || \
    (echo "npm ci failed due to lock file sync, using npm install..." && \
     rm -rf node_modules package-lock.json && \
     npm cache clean --force && \
     npm install --cache /app/.npm --loglevel=warn)

# Copy source code with correct ownership
COPY --chown=node:node . .

# Expose port 3002 (configured via docker compose)
EXPOSE 3002

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=15s --start-period=90s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3002 || exit 1

# Start Vite development server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3002"]

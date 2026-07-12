# Stage 1: Install dependencies
FROM node:20-alpine AS deps

RUN apk add --no-cache build-base gcc autoconf automake zlib-dev libpng-dev vips-dev

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install

# Stage 2: Development target (used by docker compose)
# Runs `strapi develop` with hot reload and Content-Type Builder enabled
FROM deps AS dev

COPY . .
ENV NODE_ENV=development
EXPOSE 1337
CMD ["npm", "run", "develop"]

# Stage 3: Production build
FROM deps AS build

COPY . .

# Backend URL must be set at build time (baked into admin panel static assets)
ARG STRAPI_ADMIN_BACKEND_URL
ENV STRAPI_ADMIN_BACKEND_URL=${STRAPI_ADMIN_BACKEND_URL}

RUN NODE_ENV=production npm run build

# Stage 4: Production runtime
FROM node:20-alpine

RUN apk add --no-cache vips-dev curl

RUN addgroup -g 1001 -S strapi && \
    adduser -S strapi -u 1001 -G strapi

WORKDIR /app
COPY --from=build --chown=strapi:strapi /app ./

# Strapi needs write access to these directories at runtime
RUN mkdir -p /app/database/migrations /app/.tmp /app/.cache /app/public/uploads && \
    chown -R strapi:strapi /app/database /app/.tmp /app/.cache /app/public

USER strapi

ENV NODE_ENV=production
ENV HOST=0.0.0.0
ENV PORT=1337

EXPOSE 1337

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
  CMD curl -f http://localhost:1337/_health || exit 1

CMD ["npm", "start"]

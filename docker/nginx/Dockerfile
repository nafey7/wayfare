FROM nginx:alpine

# Copy nginx configuration
COPY flightlogic-proxy.conf /etc/nginx/conf.d/default.conf

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:8080/health || exit 1

# Expose proxy port
EXPOSE 8080

# Labels
LABEL description="FlightLogic API reverse proxy with request logging"
LABEL maintainer="DevOps Team"

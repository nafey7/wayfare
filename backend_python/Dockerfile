FROM python:3.12-alpine

WORKDIR /app

# Install system dependencies including cairo for xhtml2pdf/pycairo
RUN apk add --no-cache \
    curl \
    gcc musl-dev \
    cairo-dev pango-dev gdk-pixbuf-dev \
    pkgconfig

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir uvicorn

# Copy source code
COPY . .

# Create static directory for frontend files
RUN mkdir -p static

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:80/health').read()" || exit 1

# Start the application with auto-reload for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80", "--reload"]

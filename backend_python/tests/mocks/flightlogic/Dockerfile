# Dockerfile for FlightLogic Mock Server
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir fastapi==0.115.6 uvicorn[standard]==0.34.0

# Copy mock server code
COPY tests/mocks/flightlogic/ /app/tests/mocks/flightlogic/
COPY tests/mocks/__init__.py /app/tests/mocks/

# Copy fixtures for request-keyed deterministic responses
COPY tests/fixtures/ /app/tests/fixtures/

# Create __init__.py files for proper Python package structure
RUN touch /app/tests/__init__.py

# Expose port
EXPOSE 8002

# Run mock server
CMD ["python", "-m", "tests.mocks.flightlogic.server", "--host", "0.0.0.0", "--port", "8002"]

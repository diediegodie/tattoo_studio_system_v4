# Multi-stage Dockerfile for Tattoo Studio System
# Supports development, production, and testing environments

# Base stage with common dependencies
FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        gcc \
        python3-dev \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory to where the app code will be
WORKDIR /app/backend

# Copy and install Python dependencies
COPY ../requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./backend/app ./app

# Copy frontend assets for Flask templates
COPY ../frontend/templates ./frontend/templates
COPY ../frontend/assets ./frontend/assets

# Create non-root user for security
RUN adduser --disabled-password --gecos '' appuser \
    && chown -R appuser:appuser /app
USER appuser

# Set working directory to the app directory for proper Python path resolution
# WORKDIR /app/app

# Expose port
EXPOSE 5000

# Development stage
FROM base AS development

# Install additional development dependencies
USER root
COPY ../requirements.txt /tmp/requirements.txt
# Reinstall full requirements to ensure all packages are available in development
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && pip install --no-cache-dir flask[dev] pytest pytest-cov
USER appuser

# Set Flask environment for development
ENV FLASK_ENV=development \
    FLASK_DEBUG=1

# Health check for development
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Command for development (Flask CLI)
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]

# Production stage
FROM base AS production

# Install production WSGI server
USER root
RUN pip install --no-cache-dir gunicorn
USER appuser

# Set production environment
ENV FLASK_ENV=production

# Health check for production
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Command for production (Gunicorn)
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120"]

# Test stage
FROM base AS test

# Install test dependencies
USER root
RUN pip install --no-cache-dir pytest pytest-cov pytest-flask
USER appuser

# Set test environment
ENV FLASK_ENV=testing

# Copy test configuration
COPY ../pytest.ini /app/pytest.ini
COPY ./tests /app/tests

# Set working directory back to /app for test execution
WORKDIR /app

# Default command for testing
CMD ["pytest", "--tb=short", "-v"]

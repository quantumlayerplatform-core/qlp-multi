# Multi-stage Dockerfile for Quantum Layer Platform
# This creates a single image that can run any service based on SERVICE_NAME env var

FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    netcat-traditional \
    postgresql-client \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with docker access
RUN useradd -m -u 1000 qlp && usermod -aG docker qlp

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=qlp:qlp . .

# Create directories for runtime
RUN mkdir -p /app/logs /app/capsule_versions && \
    chown -R qlp:qlp /app/logs /app/capsule_versions

# Switch to non-root user
USER qlp

# Environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV SERVICE_NAME=orchestrator
ENV PORT=8000

# Add startup script
COPY --chown=qlp:qlp docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose all possible ports (actual port used depends on SERVICE_NAME)
EXPOSE 8000 8001 8002 8003 8004

# Use entrypoint script to start the appropriate service
ENTRYPOINT ["docker-entrypoint.sh"]
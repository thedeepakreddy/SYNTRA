# Multi-stage Dockerfile for SYNTRA Platform
# SYNTRA: Synchronized Intelligence for Autonomous Engineering
# Base image with Python 3.12 and uv
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install dependencies first for optimal Docker layer caching
COPY pyproject.toml README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv /app/.venv && \
    uv pip install --python /app/.venv ".[dev]"

# Copy source code and build editable wheel
COPY src/ /app/src/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --python /app/.venv -e .

# Final runtime image
FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app

# Install runtime system packages (git, curl)
RUN apt-get update && \
    apt-get install -y --no-install-recommends git curl && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -g 1000 syntra && \
    useradd -u 1000 -g syntra -s /bin/bash -m syntra

# Copy virtualenv and application from builder
COPY --from=builder --chown=syntra:syntra /app/.venv /app/.venv
COPY --from=builder --chown=syntra:syntra /app/src /app/src
COPY --from=builder --chown=syntra:syntra /app/pyproject.toml /app/pyproject.toml
COPY --from=builder --chown=syntra:syntra /app/README.md /app/README.md

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV SYNTRA_HOST=0.0.0.0
ENV SYNTRA_PORT=8000

# Directory for sandboxes and databases
RUN mkdir -p /app/.syntra/sandboxes && chown -R syntra:syntra /app/.syntra

USER syntra

EXPOSE 8000

# Container health check
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Default command starts the API and WebSocket server
CMD ["uvicorn", "syntra.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

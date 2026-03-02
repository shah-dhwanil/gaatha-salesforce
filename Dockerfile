# Use Python 3.12 slim image as base
FROM python:3.12-slim AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # uv specific
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# -----------------------------------------------------------------------------
# Builder stage: Install dependencies
# -----------------------------------------------------------------------------
FROM base AS builder

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen --no-dev --no-install-project

# -----------------------------------------------------------------------------
# Runtime stage: Final image
# -----------------------------------------------------------------------------
FROM base AS runtime

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY . .

# Copy config.toml (ensure it's present)
COPY config_prod.toml ./config.toml

# Set PATH to include virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Expose port (default from config.toml is 9000)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "-m", "api.main"]

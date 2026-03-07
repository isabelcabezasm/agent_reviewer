# Multi-stage build for Agent Reviewer
# Published to: ghcr.io/isabelcabezasm/agent_reviewer

# ── Stage 1: Builder ─────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for caching
COPY pyproject.toml uv.lock README.md ./

# Install dependencies
ENV UV_LINK_MODE=copy
RUN uv sync --frozen --no-dev --no-install-project

# Copy source code
COPY src/ src/
COPY .env.template .env.template
COPY action-entrypoint.sh action-entrypoint.sh

# Install the project itself
RUN uv sync --frozen --no-dev

# ── Stage 2: Runtime ─────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Install git (needed for diff operations on mounted repos)
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment and source from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/pyproject.toml /app/pyproject.toml
COPY --from=builder /app/.env.template /app/.env.template

# Put venv on PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# No ENTRYPOINT — use CMD so it can be overridden by Container Apps
# Default: run the web API server
CMD ["uvicorn", "src.web.app:app", "--host", "0.0.0.0", "--port", "8000"]

# Health check for web mode
HEALTHCHECK --interval=30s --timeout=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# Multi-stage Docker build with UV package manager
# Source: https://docs.astral.sh/uv/guides/integration/docker/

# --- Build stage ---
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Dependencies layer (cached until lock changes)
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

# Application layer
COPY src/ src/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# --- Runtime stage ---
FROM python:3.12-slim

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY src/ /app/src/

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# Shell-form CMD required for Railway $PORT expansion
CMD uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers

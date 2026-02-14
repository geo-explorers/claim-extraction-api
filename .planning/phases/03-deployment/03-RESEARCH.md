# Phase 3: Deployment - Research

**Researched:** 2026-02-14
**Domain:** Docker containerization + Railway PaaS deployment
**Confidence:** HIGH

## Summary

Phase 3 requires two deliverables: a Dockerfile using `python:3.12-slim` with UV for dependency management, and a `railway.toml` configuration file. The scope is narrow and well-understood -- this is standard Python container deployment to a PaaS platform.

The existing application is well-prepared for containerization. It already reads PORT from environment variables (via `Settings.port` with default 8000), has a `/health` endpoint returning `{"status": "ok"}`, and handles missing `GEMINI_API_KEY` gracefully (starts up fine, returns 503 on `/generate` endpoints). The `fastapi[standard]` dependency already includes uvicorn. UV is available on the development machine (v0.6.6) and the project already uses `uv.lock` and `pyproject.toml`.

**Primary recommendation:** Use a multi-stage Dockerfile with `python:3.12-slim` base, copy the UV binary from the official distroless image, install dependencies in a cached layer, and add `railway.toml` with Dockerfile builder and `/health` health check path.

## Standard Stack

### Core
| Component | Version/Value | Purpose | Why Standard |
|-----------|---------------|---------|--------------|
| python:3.12-slim | 3.12-slim-bookworm | Base Docker image | Matches project's `requires-python = ">=3.12"`, slim variant is ~150MB vs ~1GB full |
| ghcr.io/astral-sh/uv | latest (pin to specific tag in practice) | Package installer in build stage | 10-100x faster than pip, project already uses uv.lock |
| uvicorn | 0.40.0 (via fastapi[standard]) | ASGI server | Already a dependency, no additional install needed |
| railway.toml | N/A | Railway deployment config | Config-as-code, overrides dashboard settings |

### Supporting
| Component | Purpose | When to Use |
|-----------|---------|-------------|
| .dockerignore | Minimize build context | Always -- prevents .venv, .git, __pycache__ from bloating context |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| python:3.12-slim | python:3.12-alpine | Alpine uses musl libc, can cause compatibility issues with some Python packages; slim is safer |
| Multi-stage build | Single-stage | Single stage is simpler but includes UV binary and cache in final image (~50MB waste) |
| `railway.toml` | `railway.json` | Equivalent functionality, TOML is more readable for simple configs |
| Shell-form CMD | Exec-form CMD | Exec form is preferred for signal handling but cannot expand `$PORT`; shell form is required for Railway's dynamic PORT |

## Architecture Patterns

### Files to Create
```
claim-api/
├── Dockerfile          # Multi-stage build with UV
├── .dockerignore       # Exclude dev/build artifacts from context
└── railway.toml        # Railway deployment configuration
```

### Pattern 1: Multi-Stage Docker Build with UV
**What:** Two-stage Dockerfile -- build stage installs dependencies with UV, runtime stage copies only the virtualenv and application code.
**When to use:** Always for production Python images.

```dockerfile
# Source: https://docs.astral.sh/uv/guides/integration/docker/
# Stage 1: Build
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Install dependencies (cached layer -- only rebuilds when lock changes)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

# Copy application code and install project
COPY src/ src/
COPY README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# Stage 2: Runtime
FROM python:3.12-slim

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY src/ /app/src/

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# Shell form required for Railway $PORT expansion
CMD uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

### Pattern 2: Railway Config-as-Code
**What:** `railway.toml` at project root defines builder and deployment settings.
**When to use:** Any Railway deployment.

```toml
# Source: https://docs.railway.com/reference/config-as-code
[build]
builder = "DOCKERFILE"

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

### Pattern 3: .dockerignore for Minimal Context
**What:** Exclude non-essential files from the Docker build context.

```
.venv/
.git/
.gitignore
.env
.env.example
__pycache__/
*.pyc
.mypy_cache/
.pytest_cache/
.ruff_cache/
*.egg-info/
dist/
build/
htmlcov/
.coverage
tests/
.planning/
.claude/
submodules/
README.md
```

Note: `README.md` can be excluded from .dockerignore IF the project's `pyproject.toml` references it and `uv sync` needs it during the build stage. In this project, `pyproject.toml` has `readme = "README.md"` so it IS needed during `uv sync` in the build stage. Include it in the build stage COPY, but it does not need to be in the runtime stage.

### Anti-Patterns to Avoid
- **Exec-form CMD with $PORT:** `CMD ["uvicorn", "src.main:app", "--port", "$PORT"]` does NOT expand the variable. Railway injects PORT dynamically, so shell form is required.
- **Installing dev dependencies in production image:** Always use `--no-dev` flag with `uv sync` to exclude pytest, ruff, mypy from the container.
- **COPY . . in runtime stage:** Only copy what is needed (`src/` directory). Avoid copying tests, docs, config files into production.
- **Running as root without justification:** For this simple deployment, running as root in the container is acceptable for Railway, but a non-root user is better practice. Railway containers are isolated anyway.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Health check endpoint | New health endpoint | Existing `/health` route | Already returns `{"status": "ok"}`, Railway needs HTTP 200 |
| Process management | Supervisor, multiple processes | Single uvicorn process | Railway handles scaling at platform level |
| HTTPS/TLS | certbot, TLS config | Railway's built-in TLS | Railway terminates TLS at the edge automatically |
| Log aggregation | File-based logging | stdout/stderr (already configured) | Railway captures stdout/stderr automatically |
| Port configuration | Hardcoded port | `$PORT` env var with `Settings.port` default | Railway injects PORT, app already reads it via pydantic-settings |

**Key insight:** Railway handles TLS, domains, scaling, and log capture. The Dockerfile only needs to run the app on the correct port.

## Common Pitfalls

### Pitfall 1: PORT Variable Not Expanding in Dockerfile CMD
**What goes wrong:** App binds to literal string "$PORT" or default 8000, ignoring Railway's assigned port. Deployment health check fails.
**Why it happens:** Docker exec-form CMD (`CMD ["uvicorn", ..., "--port", "$PORT"]`) does not invoke a shell, so environment variables are not expanded.
**How to avoid:** Use shell-form CMD: `CMD uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}`
**Warning signs:** "Invalid value for '--port': '$PORT' is not a valid integer" in deploy logs, or health check timeout.

### Pitfall 2: Missing .venv in .dockerignore
**What goes wrong:** Local `.venv/` (Linux-specific) gets copied into Docker build context, potentially overwriting the container's virtualenv or causing platform mismatches.
**Why it happens:** `.venv/` contains platform-specific binaries that differ between host and container.
**How to avoid:** Add `.venv/` to `.dockerignore`. The UV docs explicitly call this out.
**Warning signs:** Unexpectedly large Docker build context, or import errors in the container.

### Pitfall 3: Forgetting --host 0.0.0.0
**What goes wrong:** Uvicorn defaults to `127.0.0.1`, which is only accessible inside the container. Railway's health check and all external traffic is rejected.
**Why it happens:** Localhost binding is the uvicorn default for safety in development.
**How to avoid:** Always specify `--host 0.0.0.0` in the CMD.
**Warning signs:** Health check timeout with no access logs in the container.

### Pitfall 4: uv.lock or pyproject.toml Missing README.md Reference
**What goes wrong:** `uv sync` in the build stage fails because `pyproject.toml` has `readme = "README.md"` but the file is not available.
**Why it happens:** If README.md is excluded from the COPY or .dockerignore, UV cannot resolve the project metadata.
**How to avoid:** COPY README.md into the build stage alongside pyproject.toml and uv.lock. It does not need to persist into the runtime stage.
**Warning signs:** `uv sync` error mentioning missing file during `docker build`.

### Pitfall 5: Including tests/ and dev files in production image
**What goes wrong:** Image size bloats, potential security exposure of test fixtures.
**Why it happens:** Using `COPY . .` without .dockerignore.
**How to avoid:** Use explicit COPY commands for only `src/` in the runtime stage, and a thorough `.dockerignore`.
**Warning signs:** Image size over 300MB for a simple API.

### Pitfall 6: Health Check Timeout Too Short
**What goes wrong:** Railway marks deployment as failed even though the app would start successfully given more time.
**Why it happens:** Default is 300 seconds which should be plenty for this lightweight app, but cold starts with slow package compilation could take time.
**How to avoid:** Set `UV_COMPILE_BYTECODE=1` in the build stage to pre-compile .pyc files. Keep the default 300s timeout. This app should start in <5 seconds.
**Warning signs:** Deployment marked as "failed" with no error logs from the application.

## Code Examples

### Complete Dockerfile (Recommended)
```dockerfile
# Source: https://docs.astral.sh/uv/guides/integration/docker/
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

# --- Runtime ---
FROM python:3.12-slim

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY src/ /app/src/

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000

CMD uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

### Complete railway.toml (Recommended)
```toml
# Source: https://docs.railway.com/reference/config-as-code
[build]
builder = "DOCKERFILE"

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

### Complete .dockerignore (Recommended)
```
.venv/
.git/
.gitignore
.env
.env.example
__pycache__/
*.pyc
.mypy_cache/
.pytest_cache/
.ruff_cache/
*.egg-info/
dist/
build/
htmlcov/
.coverage
tests/
.planning/
.claude/
submodules/
```

### Local Docker Testing Commands
```bash
# Build the image
docker build -t claim-api .

# Run without GEMINI_API_KEY (health check works, /generate returns 503)
docker run --rm -p 8000:8000 claim-api

# Run with GEMINI_API_KEY
docker run --rm -p 8000:8000 -e GEMINI_API_KEY=your-key-here claim-api

# Test health endpoint
curl http://localhost:8000/health

# Test with custom port (simulating Railway)
docker run --rm -p 3000:3000 -e PORT=3000 claim-api
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pip install in Dockerfile | UV with cache mounts | 2024-2025 | 10-100x faster builds, lockfile-based reproducibility |
| tiangolo/uvicorn-gunicorn-fastapi image | Build from python:3.x-slim | 2024 | Official FastAPI docs now recommend against the old base image |
| Nixpacks (Railway default) | Dockerfile builder | Ongoing | Dockerfile gives full control; Nixpacks is convenient but less predictable |
| railway.json | railway.toml or railway.json | Both supported | TOML is more readable, JSON has schema validation via `$schema` |

**Deprecated/outdated:**
- `tiangolo/uvicorn-gunicorn-fastapi` base image: FastAPI official docs explicitly say to build from scratch using official Python image
- `Nixpacks` builder: Still supported but Railway now defaults to `Railpack`. Using explicit Dockerfile avoids both.

## Open Questions

1. **UV version pinning in Dockerfile**
   - What we know: Using `ghcr.io/astral-sh/uv:latest` works but is non-reproducible across builds
   - What's unclear: Whether to pin to a specific version (e.g., `ghcr.io/astral-sh/uv:0.6.6`)
   - Recommendation: Use `latest` for simplicity in this small project. Pin if reproducibility becomes important.

2. **Non-root user in container**
   - What we know: Best practice is to run as non-root; Railway containers are isolated
   - What's unclear: Whether the app needs write access to any directory
   - Recommendation: Skip non-root for now (app is stateless, read-only filesystem access). Can add later if needed.

3. **`--proxy-headers` flag for uvicorn**
   - What we know: Railway terminates TLS at the edge and proxies to the container. FastAPI docs recommend `--proxy-headers` when behind a reverse proxy.
   - What's unclear: Whether Railway sends standard proxy headers (X-Forwarded-For, etc.) and whether this matters for this app
   - Recommendation: Add `--proxy-headers` to the CMD as a low-risk best practice. It has no downside if proxy headers are absent.

## Sources

### Primary (HIGH confidence)
- [UV Docker Guide](https://docs.astral.sh/uv/guides/integration/docker/) - Complete Docker integration guide with multi-stage build patterns, environment variables, cache mounts. Updated within last week.
- [Railway Config-as-Code Reference](https://docs.railway.com/reference/config-as-code) - All `railway.toml` fields: builder, healthcheckPath, healthcheckTimeout, restartPolicyType.
- [Railway Dockerfile Builds](https://docs.railway.com/builds/dockerfiles) - Dockerfile detection, build-time env vars, cache mount support.
- [Railway Health Checks](https://docs.railway.com/deployments/healthchecks) - Default 300s timeout, HTTP 200 required, PORT injection.
- [FastAPI Docker Deployment](https://fastapi.tiangolo.com/deployment/docker/) - Official Dockerfile patterns, exec-form CMD recommendation, deprecated base image warning.

### Secondary (MEDIUM confidence)
- [Railway FastAPI Guide](https://docs.railway.com/guides/fastapi) - Deployment steps, start command examples.
- [Depot: Optimal Python UV Dockerfile](https://depot.dev/docs/container-builds/how-to-guides/optimal-dockerfiles/python-uv-dockerfile) - Production multi-stage pattern with non-root user.
- [Hynek: Production Python Docker with UV](https://hynek.me/articles/docker-uv/) - Detailed rationale for multi-stage patterns and environment variables.

### Tertiary (LOW confidence)
- [Railway Help Station: PORT variable issues](https://station.railway.com/questions/how-to-expose-a-fast-api-backend-service-a1712631) - Community reports confirming shell-form CMD requirement for PORT expansion.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official UV docs and Railway docs are clear, well-documented, and recently updated
- Architecture: HIGH - Multi-stage Docker with UV is the documented standard pattern from Astral's own docs
- Pitfalls: HIGH - PORT expansion issue is well-documented across multiple Railway community posts and guides

**Research date:** 2026-02-14
**Valid until:** 2026-03-14 (30 days -- Docker and Railway patterns are stable)

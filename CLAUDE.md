# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Stateless claim extraction API and web UI. Takes source text (articles, papers, etc.), extracts topics via Gemini, then extracts atomic claims organized by topic. Built for the Geo Curator Program. No database — claims are generated on-demand and returned to the client.

## Commands

```bash
# Install dependencies (uses UV package manager)
uv sync

# Run dev server (hot reload)
uv run uvicorn src.main:app --reload --port 8000

# Run all tests
uv run pytest

# Run single test file
uv run pytest tests/test_routers/test_generate.py -v

# Run single test function
uv run pytest tests/test_routers/test_generate.py::test_generate_claims_success -v

# Lint
uv run ruff check .

# Lint with auto-fix
uv run ruff check --fix .

# Format
uv run ruff format .

# Type check (strict mode)
uv run mypy src/

# Run all checks
uv run ruff check . && uv run mypy src/ && uv run pytest
```

## Architecture

**Two-step extraction pipeline:**
```
Source Text → TopicExtractor (Gemini) → topic list
           → ClaimExtractor (Gemini, with topics) → claims by topic
           → flatten to [{claim_topic, claim}, ...]
```

**Layered structure:**

- `src/routers/` — FastAPI route handlers (`/health`, `/generate/claims`, `/` web UI)
- `src/services/claim_generation.py` — Orchestrates the two-step pipeline
- `src/extraction/` — `TopicExtractor` and `ClaimExtractor` wrapping Gemini API calls
- `src/config/settings.py` — Pydantic settings from env vars
- `src/config/prompts/` — LLM prompt templates (string `.format()` substitution)
- `src/schemas/` — Pydantic models for requests, responses, and Gemini structured outputs
- `src/exceptions.py` — Custom exception hierarchy extending `HTTPException`
- `src/dependencies.py` — FastAPI `Depends()` providers from `app.state`

**Key patterns:**

- Services are constructed during FastAPI lifespan and stored on `app.state`
- Dependency injection via `Depends()` retrieves services from `app.state`
- App starts without `GEMINI_API_KEY` (graceful degradation — `/generate` returns 503)
- Retry with exponential backoff (tenacity) on Gemini 429/5xx errors
- Gemini structured outputs via Pydantic schemas (`.parsed` with `.text` fallback)
- All Gemini safety filters set to `BLOCK_NONE` (supports political/health content for curation)
- All tests mock the Gemini client — no real API calls in tests

## Code Style

- Python 3.12+, strict mypy, ruff with rules: E, F, I, N, UP, B, A, SIM, TCH
- Line length: 99 characters
- Async throughout (endpoints, extractors, service methods)
- `from __future__ import annotations` and `TYPE_CHECKING` blocks for type imports

## Environment

Copy `.env.example` to `.env`. Only `GEMINI_API_KEY` is required for full functionality. Config is loaded via `pydantic-settings`.

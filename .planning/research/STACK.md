# Stack Research

**Domain:** Stateless LLM-powered claim extraction API
**Researched:** 2026-02-14
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | >=3.12 | Runtime | Modern type hints (`X | None`, `list[str]`), consistent with extraction-api. No reason to require 3.13 — 3.12 is the sweet spot for compatibility and features. |
| FastAPI | >=0.121.0 | Web framework | Async-native, Pydantic-first, auto-generates OpenAPI docs, serves static files for the frontend. Proven in extraction-api at 0.121.2. The `fastapi[standard]` extra bundles uvicorn, httpx, and other essentials. |
| google-genai | >=1.50.0 | Gemini SDK | The **new** unified Google GenAI SDK (`from google import genai`). Supports `response_schema` with Pydantic models directly — the core of this project. Proven in extraction-api at 1.52.0. Do NOT confuse with the deprecated `google-generativeai` package. |
| Pydantic | >=2.10.0 | Data validation & LLM schemas | Dual role: (1) API request/response validation via FastAPI, (2) Gemini structured output schemas via `response_schema=MyModel`. V2 required for `model_validate_json()` and `model_json_schema()`. Proven at 2.12.3. |
| pydantic-settings | >=2.10.0 | Configuration | Loads settings from `.env` files and environment variables with type validation. Proven pattern in extraction-api for managing `GEMINI_API_KEY`, `GEMINI_MODEL`, `PORT`, etc. Proven at 2.11.0. |
| UV | latest | Package manager | Fast, Rust-based Python package manager. Handles venv creation, dependency resolution, and lockfile (`uv.lock`). Proven in extraction-api Dockerfile with `uv sync --frozen`. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| uvicorn[standard] | >=0.34.0 | ASGI server | Always — runs FastAPI in production. The `[standard]` extra adds uvloop and httptools for performance. Bundled with `fastapi[standard]` but pin separately for clarity. Proven at 0.38.0. |
| python-dotenv | >=1.0.0 | .env file loading | Always — pydantic-settings uses this under the hood for `.env` file support. Proven at 1.1.1. |
| httpx | >=0.27.0 | HTTP client | For testing — FastAPI's `TestClient` uses httpx internally. Also useful if the API ever needs to make outbound HTTP calls. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Ruff | Linting + formatting | Single tool replaces flake8, black, isort, pyflakes, and dozens of others. Configure in `pyproject.toml` under `[tool.ruff]`. Use `ruff check --fix` and `ruff format`. |
| mypy | Static type checking | Use strict mode (`strict = true` in `pyproject.toml`). Catches type errors before runtime. Critical because Pydantic models serve as both API contracts and LLM schemas — type correctness is non-negotiable. |
| pytest | Testing | Standard Python test framework. Use with `pytest-asyncio` for async endpoint tests and `pytest-cov` for coverage reporting. |
| pytest-asyncio | Async test support | Required for testing async Gemini calls and FastAPI async endpoints. Use `asyncio_mode = "auto"` in config. |

## Installation

```bash
# Initialize project with UV
uv init --name claim-api --python ">=3.12"

# Core dependencies
uv add "fastapi[standard]>=0.121.0" "google-genai>=1.50.0" "pydantic>=2.10.0" "pydantic-settings>=2.10.0" "python-dotenv>=1.0.0"

# Dev dependencies
uv add --dev "ruff>=0.9.0" "mypy>=1.14.0" "pytest>=8.0.0" "pytest-asyncio>=0.23.0" "pytest-cov>=6.0.0"
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `google-genai` | `google-generativeai` | Never — `google-generativeai` is the deprecated predecessor. The new `google-genai` SDK is the official replacement with cleaner API, native Pydantic `response_schema` support, and active development. |
| `google-genai` | `langchain-google-genai` | Never for this project — LangChain adds unnecessary abstraction for direct Gemini calls. The reference extraction-api has it as a dependency but does not use it for the premium pipeline. Direct SDK gives more control over structured outputs. |
| FastAPI | Flask | Never for this project — Flask lacks native async, auto-generated OpenAPI docs, and Pydantic integration. FastAPI is the standard for modern Python APIs. |
| FastAPI | Litestar | If you need more opinionated framework conventions. Litestar is viable but FastAPI has vastly larger ecosystem, more examples, better Gemini integration patterns. |
| Pydantic v2 | dataclasses | Never for Gemini structured outputs — Gemini `response_schema` accepts Pydantic models directly. Dataclasses require manual schema conversion. |
| UV | pip + venv | If team is unfamiliar with UV. But UV is 10-100x faster, has deterministic lockfiles, and is proven in the extraction-api Docker builds. |
| UV | Poetry | Never — Poetry is slower, more complex, and UV has won the Python packaging war. |
| Ruff | flake8 + black + isort | Never — Ruff replaces all three, is 10-100x faster (Rust-based), and configures in a single `[tool.ruff]` section. |
| mypy | pyright | Either works. mypy is recommended for consistency with broader Python ecosystem and easier CI integration. Pyright is faster but has different strictness defaults. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `google-generativeai` | Deprecated SDK — replaced by `google-genai`. Different import path (`import google.generativeai as genai` vs `from google import genai`). Will stop receiving updates. | `google-genai` |
| LangChain | Massive dependency tree, unnecessary abstraction layer for direct Gemini calls with structured outputs. Adds latency and complexity without value for this simple pipeline. | Direct `google-genai` SDK |
| DSPy | Overkill for this project. DSPy is for training/optimizing LLM pipelines with labeled data. This project has fixed prompts and structured outputs — no optimization loop needed. | Direct `google-genai` SDK |
| Jinja2 templates | Over-engineered for a simple HTML page. Plain HTML served via `StaticFiles` is simpler, has no template compilation step, and the frontend is entirely client-side JS. | `fastapi.staticfiles.StaticFiles` |
| SQLAlchemy / any ORM | Project is explicitly stateless with no database. Adding persistence violates the architectural constraint. | Nothing — stateless by design |
| `requests` library | Synchronous HTTP client, blocks the event loop in async FastAPI. | `httpx` (async-native, used by FastAPI's TestClient) |
| Black / isort / flake8 | Replaced by Ruff. Running multiple tools is slower and requires coordinating configs. | Ruff (single tool) |

## Stack Patterns by Variant

**For Gemini structured outputs (core pattern):**
- Use `response_schema=PydanticModel` (pass the class itself, not an instance)
- Set `response_mime_type="application/json"` alongside it
- Parse with `PydanticModel.model_validate_json(response.text)`
- This is the cleaner pattern used in extraction-api's premium extractor
- Do NOT use `response_json_schema=Model.model_json_schema()` (the dict-based approach) — it's more verbose and loses Pydantic class-level validation hints

**For the synchronous Gemini SDK in async FastAPI:**
- The `google-genai` SDK's `client.models.generate_content()` is synchronous
- Wrap in `asyncio.get_event_loop().run_in_executor(None, lambda: ...)` for async contexts
- This is the proven pattern from extraction-api's `gemini_service.py`
- Alternative: use `client.aio.models.generate_content()` if the SDK version supports async natively (check docs at implementation time)

**For Railway deployment:**
- Read `PORT` from environment variable (Railway sets this)
- Use `0.0.0.0` as host (required for container networking)
- `railway.toml` with `builder = "DOCKERFILE"` and `startCommand = "uv run python -m src.api.server"`
- Health check on `/docs` (auto-generated by FastAPI)

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| fastapi>=0.121.0 | pydantic>=2.10.0 | FastAPI 0.100+ requires Pydantic v2. All modern FastAPI versions work with Pydantic 2.10+. |
| google-genai>=1.50.0 | pydantic>=2.5.0 | The `response_schema` parameter accepts Pydantic v2 models. Verified working at google-genai 1.52.0 + pydantic 2.12.3. |
| pydantic-settings>=2.10.0 | pydantic>=2.10.0 | pydantic-settings major version tracks pydantic major version. Both must be v2. |
| pytest-asyncio>=0.23.0 | pytest>=8.0.0 | pytest-asyncio 0.23+ supports `asyncio_mode = "auto"` config. |
| ruff>=0.9.0 | Python 3.12+ | Ruff 0.9+ has mature rule sets. New versions release frequently — pin to a minimum, not exact. |

## Gemini Model Recommendations

| Model | Use Case | Why |
|-------|----------|-----|
| `gemini-2.5-flash` | Default for claim extraction | Fast, cheap, excellent structured output compliance. The extraction-api uses this for guest/keyword extraction. Good enough for topic + claim extraction. |
| `gemini-2.5-pro` | Premium/fallback if Flash quality is insufficient | Higher quality but slower and more expensive. The extraction-api uses this for premium claim extraction. Only upgrade if Flash output quality is demonstrably worse. |

**Start with `gemini-2.5-flash` and only upgrade to `gemini-2.5-pro` if claim quality is insufficient.** Model selection should be configurable via environment variable (`GEMINI_MODEL`).

## Key SDK Pattern: Pydantic as Gemini Response Schema

This is the most important pattern in the entire stack. The `google-genai` SDK accepts a Pydantic model class directly as `response_schema`, and Gemini constrains its output to match that schema. This eliminates JSON parsing errors and freeform output handling.

```python
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

class TopicResult(BaseModel):
    topics: list[str] = Field(description="Extracted topic labels")

class ClaimWithTopic(BaseModel):
    topic: str = Field(description="Topic label")
    claims: list[str] = Field(description="Claims under this topic")

class ClaimExtractionResult(BaseModel):
    claim_topics: list[ClaimWithTopic] = Field(description="Claims organized by topic")

client = genai.Client(api_key=api_key)

# Step 1: Extract topics
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config=types.GenerateContentConfig(
        temperature=0.2,
        response_mime_type="application/json",
        response_schema=TopicResult,  # Pass the CLASS, not an instance
    ),
)
result = TopicResult.model_validate_json(response.text)

# Step 2: Extract claims mapped to topics
# ... same pattern with ClaimExtractionResult
```

## Sources

- **extraction-api reference implementation** (`submodules/extraction-api/`) — PRIMARY SOURCE. All version numbers verified against `uv.lock` (locked versions: google-genai 1.52.0, fastapi 0.121.2, pydantic 2.12.3, pydantic-settings 2.11.0, uvicorn 0.38.0, pytest 8.4.2, python-dotenv 1.1.1, httpx 0.28.1). HIGH confidence.
- **extraction-api `premium_claim_extractor.py`** — Verified Gemini structured output pattern using `response_schema=PydanticModel` with `response_mime_type="application/json"`. HIGH confidence.
- **extraction-api `gemini_service.py`** — Verified async wrapper pattern using `run_in_executor` for synchronous Gemini SDK calls. HIGH confidence.
- **extraction-api `settings.py`** — Verified pydantic-settings pattern with `SettingsConfigDict(env_file=".env")`. HIGH confidence.
- **extraction-api `Dockerfile`** — Verified UV-based Docker build pattern with `uv sync --frozen`. HIGH confidence.
- **extraction-api `railway.toml`** — Verified Railway deployment configuration. HIGH confidence.

### Confidence Notes

- All versions are from the extraction-api's `uv.lock` file, which represents a **proven, working combination** as of the most recent lock. These are minimum version floors, not pinned maximums.
- Ruff and mypy versions are based on training data (LOW confidence on exact latest versions). The minimum floors (`ruff>=0.9.0`, `mypy>=1.14.0`) are conservative and safe.
- Gemini model names (`gemini-2.5-flash`, `gemini-2.5-pro`) are from the extraction-api settings. Model availability may change; make model selection configurable via environment variable.
- The `google-genai` async API (`client.aio.models.generate_content()`) availability is LOW confidence — verify at implementation time whether the SDK version supports native async, or use the `run_in_executor` pattern from extraction-api.

---
*Stack research for: Stateless claim extraction API with Gemini structured outputs*
*Researched: 2026-02-14*

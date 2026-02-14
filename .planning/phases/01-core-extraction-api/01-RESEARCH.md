# Phase 1: Core Extraction API - Research

**Researched:** 2026-02-14
**Domain:** FastAPI + Gemini structured outputs for claim extraction from generic source text
**Confidence:** HIGH

## Summary

Phase 1 delivers a working API that accepts source text and returns topic-organized, self-contained claims. The entire technical approach is proven by the reference extraction-api codebase (`submodules/extraction-api/`), which implements the same Gemini structured output pipeline for podcast transcripts. This phase adapts that proven pipeline for generic source text (news articles, research papers, essays).

The core pattern is a two-step sequential LLM pipeline: (1) extract topics from source text, (2) extract claims mapped to those topics. Both steps use Gemini's `response_schema` with Pydantic models to guarantee structured JSON output. The google-genai SDK (v1.63.0 latest) natively supports async via `client.aio.models.generate_content()` and automatic Pydantic parsing via `response.parsed`, both improvements over the patterns in the reference implementation.

**Primary recommendation:** Use `client.aio.models.generate_content()` for native async (no `run_in_executor` needed), `response.parsed` for automatic Pydantic parsing, `response_schema=PydanticModel` for all Gemini calls, and tenacity for retry logic. Adapt prompts to remove all podcast-specific language before writing any extraction code.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | >=3.12 | Runtime | Modern type hints (`X \| None`, `list[str]`), consistent with extraction-api. 3.12 is the compatibility sweet spot. |
| FastAPI | >=0.121.0 | Web framework | Async-native, Pydantic-first, auto-generates OpenAPI docs. `fastapi[standard]` bundles uvicorn, httpx. Proven at 0.121.2 in extraction-api. |
| google-genai | >=1.50.0 | Gemini SDK | The unified Google GenAI SDK (`from google import genai`). Native `response_schema` with Pydantic models. Native async via `client.aio`. Latest: 1.63.0. Do NOT use deprecated `google-generativeai`. |
| Pydantic | >=2.10.0 | Data validation + LLM schemas | Dual role: API request/response validation AND Gemini structured output schemas. V2 required. Proven at 2.12.3. |
| pydantic-settings | >=2.10.0 | Configuration | Loads settings from `.env` and environment variables with type validation. Proven at 2.11.0. |
| UV | latest | Package manager | Rust-based, 10-100x faster than pip. Deterministic lockfile. Proven in extraction-api. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tenacity | >=9.0.0 | Retry with backoff | Gemini API calls -- handles 429/503 with exponential backoff. Cleaner than hand-rolled retry loops. |
| python-dotenv | >=1.0.0 | .env loading | Always -- pydantic-settings uses this under the hood. |
| uvicorn[standard] | >=0.34.0 | ASGI server | Always -- runs FastAPI. Bundled with `fastapi[standard]`. |
| httpx | >=0.27.0 | HTTP client (testing) | FastAPI's `TestClient` uses httpx internally. |

### Development Tools
| Tool | Version | Purpose | Notes |
|------|---------|---------|-------|
| Ruff | >=0.9.0 | Linting + formatting | Replaces flake8, black, isort. Configure in `pyproject.toml` under `[tool.ruff]`. |
| mypy | >=1.14.0 | Static type checking | Use `strict = true`. Add `pydantic.mypy` plugin for proper Pydantic support. |
| pytest | >=8.0.0 | Testing | Standard Python test framework. |
| pytest-asyncio | >=0.24.0,<1.0.0 | Async test support | Use `asyncio_mode = "auto"` in config. Pin below 1.0.0 to avoid breaking changes from the May 2025 release (event_loop fixture removal). |
| pytest-cov | >=6.0.0 | Coverage reporting | Optional but recommended. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| tenacity | Hand-rolled retry loop | extraction-api has a hand-rolled version in `gemini_service.py`. Tenacity is cleaner, more configurable, supports async natively, and handles edge cases (jitter, custom stop conditions). Use tenacity. |
| `client.aio.models.generate_content()` | `run_in_executor()` wrapper | extraction-api wraps sync SDK in `run_in_executor()`. The google-genai SDK now has native async via `client.aio`. Use native async -- it is cleaner, avoids thread pool exhaustion, and supports cancellation. |
| `response.parsed` | `Model.model_validate_json(response.text)` | extraction-api uses manual parsing. The SDK now automatically parses into typed Pydantic instances via `response.parsed`. Use `response.parsed` as primary, with `model_validate_json(response.text)` as fallback if `parsed` is None. |

**Installation:**
```bash
# Initialize project with UV
uv init --name claim-api --python ">=3.12"

# Core dependencies
uv add "fastapi[standard]>=0.121.0" "google-genai>=1.50.0" "pydantic>=2.10.0" "pydantic-settings>=2.10.0" "python-dotenv>=1.0.0" "tenacity>=9.0.0"

# Dev dependencies
uv add --dev "ruff>=0.9.0" "mypy>=1.14.0" "pytest>=8.0.0" "pytest-asyncio>=0.24.0,<1.0.0" "pytest-cov>=6.0.0"
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── main.py                     # FastAPI app, lifespan, CORS, exception handlers
├── config/
│   ├── __init__.py
│   ├── settings.py             # Pydantic BaseSettings (GEMINI_API_KEY, model, temp, port)
│   └── prompts/
│       ├── __init__.py
│       ├── topic_extraction.py # Topic extraction prompt template
│       └── claim_extraction.py # Claim extraction prompt template
├── schemas/
│   ├── __init__.py
│   ├── requests.py             # API request models (ClaimGenerationRequest)
│   ├── responses.py            # API response models (ClaimGenerationResponse, ErrorResponse)
│   └── llm.py                  # LLM structured output schemas (TopicResult, ClaimWithTopicResult)
├── routers/
│   ├── __init__.py
│   ├── generate.py             # POST /generate/claims endpoint
│   └── health.py               # GET /health endpoint
├── services/
│   ├── __init__.py
│   └── claim_generation.py     # ClaimGenerationService (orchestrates pipeline)
├── extraction/
│   ├── __init__.py
│   ├── topic_extractor.py      # TopicExtractor (Gemini call #1)
│   └── claim_extractor.py      # ClaimExtractor (Gemini call #2)
├── exceptions.py               # Typed exceptions (ExtractionError, LLMProviderError, etc.)
├── dependencies.py             # FastAPI dependency injection (Gemini client, service instances)
tests/
├── conftest.py                 # Fixtures (mock Gemini client, sample texts)
├── test_routers/
│   ├── test_generate.py        # Endpoint integration tests
│   └── test_health.py          # Health endpoint tests
├── test_services/
│   └── test_claim_generation.py # Service unit tests
└── test_extraction/
    ├── test_topic_extractor.py  # Extractor unit tests with mocked Gemini
    └── test_claim_extractor.py  # Extractor unit tests with mocked Gemini
pyproject.toml                  # UV project config, ruff, mypy, pytest settings
.env.example                    # Template for environment variables
```

### Pattern 1: Native Async Gemini Calls with Pydantic Parsing
**What:** Use `client.aio.models.generate_content()` for native async and `response.parsed` for automatic Pydantic parsing.
**When to use:** Every Gemini call in this project. This is the primary pattern.
**Example:**
```python
# Source: google-genai SDK docs (https://googleapis.github.io/python-genai/)
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

class TopicResult(BaseModel):
    topics: list[str] = Field(
        description="List of concise topic labels (3-10 words) extracted from source text."
    )

client = genai.Client(api_key=api_key)

response = await client.aio.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config=types.GenerateContentConfig(
        temperature=0.2,
        response_mime_type="application/json",
        response_schema=TopicResult,
    ),
)

# Primary: use response.parsed (typed Pydantic instance)
result: TopicResult | None = response.parsed
if result is None:
    # Fallback: manual parsing
    result = TopicResult.model_validate_json(response.text)
```

### Pattern 2: Retry with Tenacity on Gemini Calls
**What:** Wrap Gemini calls with tenacity for exponential backoff on 429/503.
**When to use:** Every Gemini call. Never call Gemini without retry logic.
**Example:**
```python
# Source: tenacity docs (https://tenacity.readthedocs.io/)
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((ResourceExhausted, ServiceUnavailable)),
    reraise=True,
)
async def _call_gemini(self, prompt: str) -> TopicResult:
    response = await self.client.aio.models.generate_content(
        model=self.model,
        contents=prompt,
        config=self._config,
    )
    result = response.parsed
    if result is None:
        raise ValueError("Gemini returned unparseable response")
    return result
```

### Pattern 3: Typed Exception Hierarchy for Error Propagation
**What:** Define specific exception types that map to HTTP status codes. Never swallow errors.
**When to use:** All error paths. The extraction-api's pattern of catching exceptions and returning empty lists is explicitly forbidden.
**Example:**
```python
# Source: extraction-api exceptions.py (adapted -- remove silent failures)
from fastapi import HTTPException, status

class ExtractionError(HTTPException):
    """Base for extraction failures."""
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)

class LLMProviderError(ExtractionError):
    """Gemini API call failed after retries."""
    def __init__(self, detail: str = "LLM provider error after retries exhausted"):
        super().__init__(detail=detail)

class SafetyFilterError(ExtractionError):
    """Gemini blocked content due to safety filters."""
    def __init__(self, detail: str = "Content blocked by safety filters"):
        super().__init__(detail=detail)

class InputValidationError(HTTPException):
    """Invalid source text input."""
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

class ProcessingTimeoutError(HTTPException):
    """Extraction exceeded timeout."""
    def __init__(self, timeout: int):
        super().__init__(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Extraction timed out after {timeout} seconds",
        )
```

### Pattern 4: Pydantic BaseSettings for Configuration
**What:** Load all configuration from environment variables with type validation and defaults.
**When to use:** Always. Fail fast at startup if required vars are missing.
**Example:**
```python
# Source: extraction-api config/settings.py (simplified for this project)
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    gemini_api_key: str = Field(description="Google Gemini API key")
    gemini_model: str = Field(default="gemini-2.5-flash", description="Gemini model name")
    gemini_temperature: float = Field(default=0.2, description="Generation temperature")
    port: int = Field(default=8000, description="API server port (Railway sets via PORT)")
    log_level: str = Field(default="INFO", description="Logging level")

settings = Settings()
```

### Pattern 5: Safety Settings Configuration
**What:** Configure Gemini to not block content about politics, health, violence.
**When to use:** All Gemini calls. Default safety settings for Gemini 2.5+ models are already Off, but configure explicitly for defense in depth.
**Example:**
```python
# Source: Google AI safety settings docs (https://ai.google.dev/gemini-api/docs/safety-settings)
from google.genai import types

safety_settings = [
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
]

config = types.GenerateContentConfig(
    temperature=0.2,
    response_mime_type="application/json",
    response_schema=TopicResult,
    safety_settings=safety_settings,
)
```

### Anti-Patterns to Avoid
- **Silent empty returns on LLM failure:** The extraction-api catches exceptions and returns `[]` or `{}`. For a user-facing API, this is terrible UX. Always propagate errors as typed exceptions with appropriate HTTP status codes.
- **Mixing LLM schemas with API schemas:** `TopicResult` (what Gemini returns) and `ClaimGenerationResponse` (what the API returns) serve different purposes. Keep them in separate files (`schemas/llm.py` vs `schemas/responses.py`). The service layer transforms between them.
- **Synchronous Gemini calls in async endpoints:** Do NOT call `client.models.generate_content()` directly in async route handlers. Use `client.aio.models.generate_content()` (native async).
- **Hardcoded prompts in extractor classes:** Store prompts in `config/prompts/` as module-level constants. Import into extractors. Prompts change frequently; isolating them makes iteration easy.
- **Using `response_json_schema` instead of `response_schema`:** The extraction-api inconsistently uses both. Standardize on `response_schema=PydanticModel` (pass the class). It is the newer, preferred approach that handles schema conversion internally.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry with backoff | Custom retry loop with `asyncio.sleep` | `tenacity` with `retry_if_exception_type` | Tenacity handles jitter, max attempts, backoff strategy, async support, and exception filtering. The extraction-api's hand-rolled retry in `gemini_service.py` is 15 lines that tenacity replaces with a decorator. |
| Input validation | Custom `if len(text) < 50` checks | Pydantic `Field(min_length=50, max_length=50000)` on request model | Pydantic validates at the schema level, generates OpenAPI docs automatically, returns structured 422 errors. |
| JSON parsing of Gemini responses | `json.loads()` + manual dict traversal | `response.parsed` (auto-Pydantic) or `Model.model_validate_json(response.text)` | The SDK handles JSON parsing, schema validation, and type coercion. Manual parsing loses type safety. |
| Configuration loading | `os.environ.get()` with manual defaults | `pydantic-settings` `BaseSettings` with `SettingsConfigDict(env_file=".env")` | Type-safe, validates at startup, auto-documents all settings, supports `.env` file loading. |
| ASGI server configuration | Custom server script | `uvicorn` with `fastapi[standard]` | Industry standard. Handles workers, reload, signal handling. |

**Key insight:** This project's complexity lives in prompt engineering and LLM integration, not infrastructure. Use libraries for infrastructure so attention stays on extraction quality.

## Common Pitfalls

### Pitfall 1: Prompt Brittleness to Non-Podcast Text
**What goes wrong:** The extraction-api prompts are deeply podcast-specific. Using them unchanged produces claims referencing "the episode," "the host," topics like "Overview of episode's key themes," and ad filtering that rejects legitimate news content.
**Why it happens:** The extraction-api was built exclusively for podcast transcripts. The prompts contain: "podcast transcript" terminology, "host"/"guest"/"episode" references, ad filtering for "sign up"/"subscribe"/"go to [URL]" (legitimate in news), "6-14 topics for typical episodes" (wrong for 500-word articles).
**How to avoid:**
- Replace ALL "transcript"/"podcast"/"episode" with "source text"
- Remove ad-filtering step entirely (or make it very conservative)
- Scale topic count guidance to text length: 2-5 topics for short texts, 5-10 for medium, 8-15 for long
- Remove "title" and "description" parameters from topic prompt (generic text does not have these)
- Keep self-containment rules (Shuffle Rule, pronoun replacement, attribution stripping) -- these are domain-agnostic
- Test adapted prompts against 3 text types before shipping: news article, research abstract, long essay
**Warning signs:** Claims referencing "the episode"/"the speaker", topic labels like "Overview of episode's key themes", legitimate URLs filtered as "promotional", short texts producing 0 topics.

### Pitfall 2: Silent Empty Responses on Gemini Failures
**What goes wrong:** Gemini returns empty results on API errors, and the service silently returns `{"claims": []}` with HTTP 200. Users see an empty table, no error message.
**Why it happens:** The extraction-api catches all exceptions in `premium_claim_extractor.py` (lines 120-124, 178-182) and returns empty lists as fallback. This was acceptable for a batch pipeline but is terrible for user-facing UX.
**How to avoid:**
- Never return empty results silently. Propagate errors as typed exceptions.
- Distinguish "no claims found" (valid, HTTP 200 with empty array) from "LLM failed" (error, HTTP 502/503/504).
- Check `response.candidates[0].finish_reason` after each call. If it is `SAFETY` instead of `STOP`, raise `SafetyFilterError`.
- If topic extraction fails, do NOT proceed to claim extraction. Fail fast.
**Warning signs:** Users report "it returned nothing" on texts with obvious claims. Logs show extraction errors but API returns 200.

### Pitfall 3: Gemini Rate Limits on Free Tier
**What goes wrong:** Each user request triggers 2 LLM calls. Free tier has low RPM (2 RPM for Pro, 15 RPM for Flash). Even 5 concurrent users can exhaust limits.
**Why it happens:** The extraction-api's premium extractor has NO retry logic -- it catches the exception and returns empty.
**How to avoid:**
- Use tenacity with exponential backoff on all Gemini calls (handles 429 `ResourceExhausted` and 503 `ServiceUnavailable`).
- Default to `gemini-2.5-flash` (higher rate limits: 30 RPM free, 2000 RPM paid).
- Set maximum input text length (50,000 chars) to prevent token cost explosion.
- Log token usage per request from Gemini response metadata.
**Warning signs:** `google.api_core.exceptions.ResourceExhausted: 429` in logs. Intermittent empty results that "work when you try again."

### Pitfall 4: Schema Design Matters for LLM Output Quality
**What goes wrong:** Overly complex nested Pydantic schemas confuse Gemini. Fields show up as null. Arrays are empty when they should not be.
**Why it happens:** Gemini's structured output support covers a JSON Schema subset. Complex validators, discriminated unions, and deeply nested models may not work correctly.
**How to avoid:**
- Keep LLM schemas simple: `str`, `int`, `float`, `bool`, `list[T]`, nested `BaseModel`.
- Use `Field(description="...")` to guide the LLM (descriptions become schema hints).
- Do NOT use `Optional` fields unless you genuinely want nullable output.
- Test schema changes against actual Gemini API, not just local Pydantic validation.
**Warning signs:** `ValidationError` from Pydantic when parsing Gemini responses. Fields showing up as `null` unexpectedly.

### Pitfall 5: Cascading Failure from Two-Step Pipeline
**What goes wrong:** If topic extraction returns garbage or an empty list, claim extraction produces garbage or fails. User waits for both calls (15-30+ seconds) and gets nothing.
**Why it happens:** Topic output quality directly determines claim quality. The two-step design doubles latency and creates a sequential failure chain.
**How to avoid:**
- Validate topic output before proceeding: if 0 topics returned, return an error immediately.
- Add per-step timeouts with `asyncio.wait_for()` (e.g., 30s for topics, 60s for claims).
- Use `gemini-2.5-flash` for both steps (fast, cheap) -- only upgrade to Pro if quality is demonstrably insufficient.
**Warning signs:** Average response time >20 seconds. Empty claims despite non-empty topic list.

### Pitfall 6: Missing Configuration Validation at Startup
**What goes wrong:** App starts successfully but fails on first request because `GEMINI_API_KEY` is missing or invalid.
**Why it happens:** Pydantic BaseSettings with default `None` for API key does not fail at startup. The error surfaces only when the Gemini client is first used.
**How to avoid:**
- Make `gemini_api_key` a required field (no default). App will fail fast at import time if missing.
- Validate the Gemini client can connect during FastAPI lifespan startup.
- Use `.env.example` to document all required variables.
**Warning signs:** App health check passes but extraction fails with "API key not set."

## Code Examples

### Two-Step Pipeline Orchestration
```python
# Source: Adapted from extraction-api ClaimGenerationService pattern
class ClaimGenerationService:
    def __init__(
        self,
        topic_extractor: TopicExtractor,
        claim_extractor: ClaimExtractor,
    ) -> None:
        self.topic_extractor = topic_extractor
        self.claim_extractor = claim_extractor

    async def generate_claims(self, source_text: str) -> ClaimGenerationResponse:
        # Step 1: Extract topics
        topics = await self.topic_extractor.extract(source_text)
        if not topics:
            raise ExtractionError("No topics could be extracted from the source text")

        # Step 2: Extract claims mapped to topics
        claims_by_topic = await self.claim_extractor.extract(source_text, topics)

        # Transform LLM output shape to API response shape
        claims = [
            ClaimResponse(claim_topic=topic, claim=claim_text)
            for item in claims_by_topic
            for claim_text in item.claim
        ]

        return ClaimGenerationResponse(claims=claims)
```

### LLM Schema Definitions (schemas/llm.py)
```python
# Source: Adapted from extraction-api premium_claim_extractor.py Pydantic models
from pydantic import BaseModel, Field

class TopicResult(BaseModel):
    """Gemini response schema for topic extraction (Step 1)."""
    topics: list[str] = Field(
        description="List of concise, descriptive topic labels (3-10 words) "
        "representing distinct segments of the source text in order of appearance."
    )

class ClaimWithTopicBaseResult(BaseModel):
    """A single topic with its extracted claims."""
    topic: str = Field(description="Topic label from the provided list")
    claim: list[str] = Field(
        description="List of factual, self-contained, atomic claims (5-32 words each) "
        "extracted from the source text under this topic."
    )

class ClaimWithTopicResult(BaseModel):
    """Gemini response schema for claim extraction (Step 2)."""
    claim_topic: list[ClaimWithTopicBaseResult] = Field(
        description="Claims organized by topic. Each topic contains a list of "
        "factual, verifiable, self-contained claims."
    )
```

### API Request/Response Schemas (schemas/requests.py, schemas/responses.py)
```python
# Request
from pydantic import BaseModel, Field

class ClaimGenerationRequest(BaseModel):
    source_text: str = Field(
        ...,
        min_length=50,
        max_length=50000,
        description="Source text to extract claims from (50-50,000 characters)",
    )

# Response
class ClaimResponse(BaseModel):
    claim_topic: str = Field(description="Topic category for this claim")
    claim: str = Field(description="Self-contained, atomic factual claim")

class ClaimGenerationResponse(BaseModel):
    claims: list[ClaimResponse] = Field(description="Extracted claims organized by topic")
```

### Health Check Endpoint
```python
# Source: Standard FastAPI pattern (no LLM dependency)
from fastapi import APIRouter

router = APIRouter(tags=["health"])

@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
```

### FastAPI App with Lifespan and Error Handling
```python
# Source: Adapted from extraction-api main.py (simplified, no database)
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config.settings import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: validate configuration
    logger.info(f"Starting Claim API on port {settings.port}")
    logger.info(f"Gemini model: {settings.gemini_model}")
    # Initialize Gemini client as singleton
    app.state.gemini_client = genai.Client(api_key=settings.gemini_api_key)
    yield
    # Shutdown
    logger.info("Shutting down Claim API")

app = FastAPI(
    lifespan=lifespan,
    title="Claim Extraction API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler for unexpected errors
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred", "type": type(exc).__name__},
    )
```

### pyproject.toml Configuration
```toml
[project]
name = "claim-api"
version = "0.1.0"
requires-python = ">=3.12"

[tool.ruff]
target-version = "py312"
line-length = 99

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "A", "SIM", "TCH"]

[tool.mypy]
strict = true
plugins = ["pydantic.mypy"]

[tool.pydantic-mypy]
init_forbid_extra = true
init_typed = true
warn_required_dynamic_aliases = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

## State of the Art

| Old Approach (extraction-api) | Current Approach (this project) | When Changed | Impact |
|-------------------------------|--------------------------------|--------------|--------|
| `client.models.generate_content()` sync + `run_in_executor()` | `client.aio.models.generate_content()` native async | google-genai SDK has supported `client.aio` since early releases | Eliminates thread pool overhead, cleaner async code, supports cancellation |
| `Model.model_validate_json(response.text)` manual parsing | `response.parsed` auto-Pydantic parsing | google-genai SDK auto-parse feature | Reduces boilerplate, the SDK handles JSON parsing and validation automatically |
| Hand-rolled retry loop in `gemini_service.py` | `tenacity` decorator with `retry_if_exception_type` | tenacity has been stable for years | Cleaner code, configurable backoff/jitter, built-in async support |
| `response_json_schema=Model.model_json_schema()` dict approach | `response_schema=PydanticModel` class approach | Both exist in SDK; class approach is preferred | Cleaner, SDK handles schema conversion internally, better Pydantic feature support |
| String-based safety categories `"HARM_CATEGORY_HATE_SPEECH"` | Enum-based `types.HarmCategory.HARM_CATEGORY_HATE_SPEECH` | google-genai SDK types module | Type-safe, IDE autocompletion, catches typos at development time |

**Deprecated/outdated:**
- `google-generativeai` package: Deprecated predecessor to `google-genai`. Different import path. Will stop receiving updates.
- `model.generate_content_async()`: Old SDK async pattern. Replaced by `client.aio.models.generate_content()` in new SDK.
- pytest-asyncio `event_loop` fixture: Removed in v1.0.0 (May 2025). Use `asyncio_mode = "auto"` instead. Pin pytest-asyncio below 1.0.0 to avoid migration overhead.

## Open Questions

1. **`response.parsed` reliability with complex schemas**
   - What we know: The SDK docs show `response.parsed` works with simple Pydantic models. The extraction-api uses `model_validate_json()`.
   - What is unclear: Whether `response.parsed` handles all edge cases reliably (e.g., empty responses, partial JSON, complex nested models like `ClaimWithTopicResult`).
   - Recommendation: Use `response.parsed` as primary path. Add fallback to `model_validate_json(response.text)` when `parsed` is None. Test both paths during implementation.

2. **google-genai exception types for retry targeting**
   - What we know: The extraction-api handles `Exception` broadly. Google API errors typically come from `google.api_core.exceptions` (e.g., `ResourceExhausted`, `ServiceUnavailable`).
   - What is unclear: The exact exception types raised by the `google-genai` SDK (vs the older `google-cloud` SDK) for rate limiting and service unavailability.
   - Recommendation: During implementation, test with an invalid API call to discover exact exception types. Start with broad retry, then narrow to specific types. Check `google.genai.errors` namespace.

3. **Optimal topic count guidance for varying text lengths**
   - What we know: extraction-api uses "6-14 topics" for podcast transcripts (1-2 hours of content). Short news articles (500 words) need 2-4 topics. Long research papers might need 8-15.
   - What is unclear: The exact breakpoints for topic count guidance relative to text length.
   - Recommendation: Start with simple heuristic in prompt: "Extract 2-5 topics for texts under 1000 words, 4-8 for 1000-5000 words, 6-12 for texts over 5000 words." Iterate based on extraction quality.

## Sources

### Primary (HIGH confidence)
- extraction-api `premium_claim_extractor.py` -- Gemini structured output pattern with `response_schema=PydanticModel`, Pydantic models for LLM responses (TopicDiscussionResult, ClaimWithTopicResult)
- extraction-api `gemini_service.py` -- Retry pattern, safety settings (BLOCK_NONE), `run_in_executor` async wrapper, response validation
- extraction-api `config/settings.py` -- Pydantic BaseSettings with `SettingsConfigDict(env_file=".env")`
- extraction-api `config/prompts/claim_extraction_prompt.py` -- Claim extraction prompt with self-containment rules, attribution stripping, topic iteration
- extraction-api `config/prompts/topics_of_discussion_extraction_prompt.py` -- Topic extraction prompt with chronological ordering, topic merging rules
- extraction-api `api/exceptions.py` -- Typed exception hierarchy with HTTP status code mapping
- extraction-api `api/main.py` -- FastAPI app structure with CORS, lifespan, routers, exception handlers
- [Google GenAI SDK docs](https://googleapis.github.io/python-genai/) -- `client.aio` async API, `response.parsed` auto-parsing, `response_schema` parameter
- [Google AI structured output docs](https://ai.google.dev/gemini-api/docs/structured-output) -- Supported JSON schema subset, schema restrictions
- [Google AI safety settings docs](https://ai.google.dev/gemini-api/docs/safety-settings) -- BLOCK_NONE configuration, harm categories, threshold enums

### Secondary (MEDIUM confidence)
- [google-genai PyPI](https://pypi.org/project/google-genai/) -- Latest version 1.63.0, released 2026-02-11, Python >=3.10
- [Tenacity docs](https://tenacity.readthedocs.io/) -- Async retry decorator, exponential backoff, exception filtering
- [pytest-asyncio migration guide](https://pytest-asyncio.readthedocs.io/en/latest/how-to-guides/migrate_from_0_23.html) -- v1.0.0 breaking changes (event_loop removal)
- [Pydantic mypy plugin docs](https://docs.pydantic.dev/latest/integrations/mypy/) -- `pydantic.mypy` plugin configuration

### Tertiary (LOW confidence)
- Exact exception types in `google.genai.errors` namespace -- needs verification at implementation time
- `response.parsed` behavior with complex nested Pydantic models -- needs testing
- Optimal topic count heuristics for varying text lengths -- needs empirical tuning

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all versions from extraction-api's `uv.lock` (proven working combination) plus verified SDK updates from PyPI/docs
- Architecture: HIGH -- direct reference implementation in extraction-api, adapted with modern SDK patterns (native async, response.parsed)
- Pitfalls: HIGH -- most pitfalls observed directly in extraction-api codebase (silent failures, podcast prompts, sync SDK), solutions verified against official docs
- Prompt adaptation: MEDIUM -- the extraction-api prompts are excellent starting points, but the generic-text adaptation requires empirical testing against multiple text types

**Research date:** 2026-02-14
**Valid until:** 2026-03-14 (30 days -- stack is stable, SDK versioning is the main moving target)

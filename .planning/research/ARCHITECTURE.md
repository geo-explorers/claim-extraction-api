# Architecture Research

**Domain:** Stateless LLM-powered text extraction API with web UI
**Researched:** 2026-02-14
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
                          Claim Service
 ================================================================

 ┌──────────────────────────────────────────────────────────────┐
 │                     Presentation Layer                       │
 │  ┌─────────────────────┐  ┌──────────────────────────────┐  │
 │  │  Static Frontend    │  │   FastAPI (Uvicorn)           │  │
 │  │  (HTML/JS)          │──│   POST /generate/claims       │  │
 │  │  - Textarea input   │  │   GET / (serves index.html)   │  │
 │  │  - Results table    │  │   Swagger at /docs             │  │
 │  │  - CSV export       │  │                                │  │
 │  └─────────────────────┘  └────────────┬───────────────────┘  │
 ├────────────────────────────────────────┼─────────────────────┤
 │                     Service Layer      │                     │
 │  ┌─────────────────────────────────────┴──────────────────┐  │
 │  │              ClaimGenerationService                     │  │
 │  │  - Orchestrates two-step extraction pipeline           │  │
 │  │  - Validates input, formats output                     │  │
 │  └──────────────┬─────────────────────┬──────────────────┘  │
 ├─────────────────┼─────────────────────┼──────────────────────┤
 │                 │  Extraction Layer    │                     │
 │  ┌──────────────┴───────┐  ┌──────────┴───────────────────┐  │
 │  │  TopicExtractor      │  │  ClaimExtractor              │  │
 │  │  - Gemini call #1    │  │  - Gemini call #2            │  │
 │  │  - TopicResult       │  │  - ClaimWithTopicResult      │  │
 │  │    Pydantic schema   │  │    Pydantic schema           │  │
 │  └──────────────────────┘  └──────────────────────────────┘  │
 ├──────────────────────────────────────────────────────────────┤
 │                     Infrastructure Layer                     │
 │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐  │
 │  │  GeminiClient│  │  Settings    │  │  Logger            │  │
 │  │  (google-    │  │  (Pydantic   │  │  (stdlib logging)  │  │
 │  │   genai SDK) │  │   BaseSettings│ │                    │  │
 │  └──────────────┘  └──────────────┘  └────────────────────┘  │
 └──────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴──────────┐
                    │  Gemini API        │
                    │  (External)        │
                    └────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| FastAPI app | HTTP routing, request validation, CORS, error handling, static file serving | Single `main.py` with lifespan, CORS middleware, exception handlers, static mount |
| Router (`/generate`) | Endpoint definition, request/response schema binding | `routers/generate.py` with `APIRouter` |
| Request/Response schemas | Input validation, output shape contract | Pydantic `BaseModel` classes in `schemas/` |
| ClaimGenerationService | Orchestrates the two-step extraction pipeline, converts extractor results to API response shape | Service class that calls TopicExtractor then ClaimExtractor in sequence |
| TopicExtractor | First Gemini call: source text in, topics out | Formats prompt, calls `client.models.generate_content` with `TopicResult` schema |
| ClaimExtractor | Second Gemini call: source text + topics in, claims-by-topic out | Formats prompt, calls `client.models.generate_content` with `ClaimWithTopicResult` schema |
| Pydantic response schemas (LLM) | Enforce structured output from Gemini | `TopicResult`, `ClaimWithTopicResult` models passed as `response_schema` to Gemini |
| Settings | Configuration from environment variables | Pydantic `BaseSettings` reading `.env` |
| Logger | Structured logging to console | Python `logging` module (simplified from extraction-api's Rich logger) |
| Static frontend | User interface for curators | Plain HTML + vanilla JS, served via `FastAPI.mount("/", StaticFiles(...))` |

## Recommended Project Structure

```
src/
├── main.py                     # FastAPI app, lifespan, CORS, exception handlers, static mount
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
│   ├── responses.py            # API response models (ClaimGenerationResponse)
│   └── llm.py                  # LLM structured output schemas (TopicResult, ClaimWithTopicResult)
├── routers/
│   ├── __init__.py
│   └── generate.py             # POST /generate/claims endpoint
├── services/
│   ├── __init__.py
│   └── claim_generation.py     # ClaimGenerationService (orchestrates pipeline)
├── extraction/
│   ├── __init__.py
│   ├── topic_extractor.py      # TopicExtractor (Gemini call #1)
│   └── claim_extractor.py      # ClaimExtractor (Gemini call #2)
├── infrastructure/
│   ├── __init__.py
│   └── logger.py               # Logging setup
static/
├── index.html                  # Single-page UI
├── style.css                   # Styles
└── app.js                      # Frontend logic (fetch, render table, CSV export)
tests/
├── conftest.py                 # Fixtures (mock Gemini client, sample texts)
├── test_routers/
│   └── test_generate.py        # Endpoint integration tests
├── test_services/
│   └── test_claim_generation.py # Service unit tests
└── test_extraction/
    ├── test_topic_extractor.py  # Extractor unit tests
    └── test_claim_extractor.py  # Extractor unit tests
Dockerfile
pyproject.toml
.env.example
```

### Structure Rationale

- **`src/config/prompts/`**: Prompts are long string templates that change independently of code logic. Isolating them makes prompt iteration easy without touching extraction logic. This pattern is proven in the reference implementation.
- **`src/schemas/` (separate from `extraction/`)**: API schemas (what the HTTP layer sees) are distinct from LLM schemas (what Gemini sees). Keeping them in one place prevents confusion about which Pydantic models are for API vs LLM.
- **`src/extraction/`**: The two extractors are the core domain logic. Separating them from the service layer means they can be tested independently with mocked Gemini responses.
- **`src/services/`**: The service layer orchestrates extractor calls in sequence and handles the data transformation between extraction results and API response format. This is where the pipeline logic lives.
- **`static/`**: Plain HTML/JS at project root (not inside `src/`) because it is not Python code. FastAPI mounts it as a static directory. No build step.
- **Flat router structure**: With only one endpoint (`POST /generate/claims`), a single router file is sufficient. Do not over-engineer with router groups.

## Architectural Patterns

### Pattern 1: Two-Step Sequential LLM Pipeline

**What:** Break extraction into two serial Gemini calls -- first extract topics, then extract claims mapped to those topics. The output of call #1 is an input to call #2.

**When to use:** Always. This is the core pattern. The reference implementation proves that topic-first extraction produces higher quality, better-organized claims than single-pass extraction.

**Trade-offs:**
- Pro: Better claim quality, natural organization, each call is simpler for the LLM
- Pro: Topics constrain the second call, reducing hallucination
- Con: Two API calls means ~2x latency and cost vs a single call
- Con: If step 1 fails (no topics), step 2 cannot proceed

**Example:**
```python
class ClaimGenerationService:
    def __init__(self, topic_extractor: TopicExtractor, claim_extractor: ClaimExtractor):
        self.topic_extractor = topic_extractor
        self.claim_extractor = claim_extractor

    async def generate_claims(self, source_text: str) -> ClaimGenerationResponse:
        # Step 1: Extract topics
        topics = await self.topic_extractor.extract(source_text)
        if not topics:
            return ClaimGenerationResponse(claims=[], topics=[])

        # Step 2: Extract claims mapped to topics
        claims_by_topic = await self.claim_extractor.extract(source_text, topics)

        # Transform to response format
        return self._build_response(topics, claims_by_topic)
```

### Pattern 2: Gemini Structured Outputs via Pydantic Schema

**What:** Pass a Pydantic model as `response_schema` to `client.models.generate_content` with `response_mime_type="application/json"`. Gemini constrains its output to match the schema. Parse the response with `Model.model_validate_json(response.text)`.

**When to use:** Every Gemini call in this project. This is not optional -- it is a project constraint.

**Trade-offs:**
- Pro: Guaranteed valid JSON structure, no parsing errors, no regex hacks
- Pro: Pydantic validation catches schema drift automatically
- Pro: Type safety flows from LLM response all the way to API response
- Con: Schema design matters -- overly complex nested schemas can confuse the model
- Con: Gemini may produce empty arrays or minimal data if the schema is too rigid

**Example:**
```python
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

class TopicResult(BaseModel):
    topics: list[str] = Field(
        description="List of concise topic labels (3-10 words) in chronological order."
    )

class TopicExtractor:
    def __init__(self, client: genai.Client, model: str, temperature: float):
        self.client = client
        self.model = model
        self.temperature = temperature

    async def extract(self, source_text: str) -> list[str]:
        prompt = TOPIC_PROMPT.format(source_text=source_text)
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=self.temperature,
                response_mime_type="application/json",
                response_schema=TopicResult,
            ),
        )
        result = TopicResult.model_validate_json(response.text)
        return result.topics
```

### Pattern 3: Stateless Request-Response (No Pipeline State)

**What:** Each API request is fully self-contained. No database, no session, no background jobs, no state between requests. Source text goes in, claims come out.

**When to use:** This entire service. Statelessness is a project constraint.

**Trade-offs:**
- Pro: Trivial horizontal scaling -- any instance can serve any request
- Pro: No database migrations, no connection pools, no data consistency issues
- Pro: Simple deployment (single container, no sidecars)
- Con: No caching of repeated extractions (same text = same Gemini cost every time)
- Con: No history or audit trail (curators cannot revisit past extractions in this service)
- Con: Long texts may hit request timeout before Gemini responds

## Data Flow

### Request Flow

```
[Curator Browser]
    │
    │  POST /generate/claims
    │  { "source_text": "..." }
    │
    ▼
[FastAPI Router]
    │
    │  Validate request (Pydantic)
    │
    ▼
[ClaimGenerationService]
    │
    │  Step 1: topic_extractor.extract(source_text)
    │
    ▼
[TopicExtractor] ──────► [Gemini API] ──────► TopicResult
    │                                           │
    │  topics: ["Topic A", "Topic B", ...]      │
    │◄──────────────────────────────────────────┘
    │
    │  Step 2: claim_extractor.extract(source_text, topics)
    │
    ▼
[ClaimExtractor] ──────► [Gemini API] ──────► ClaimWithTopicResult
    │                                           │
    │  claims_by_topic: {                       │
    │    "Topic A": ["claim 1", "claim 2"],     │
    │    "Topic B": ["claim 3"]                 │
    │  }                                        │
    │◄──────────────────────────────────────────┘
    │
    │  Transform to response format
    │
    ▼
[FastAPI Router]
    │
    │  200 OK
    │  { "claims": [{ "claim_topic": "...", "claim": "..." }, ...] }
    │
    ▼
[Curator Browser]
    │
    │  Render table, enable CSV export
    │
    ▼
[Done - no state persisted]
```

### Key Data Flows

1. **Source text to topics:** Raw source text is inserted into a prompt template. Gemini returns `TopicResult` (list of topic strings). No transformation needed beyond parsing.

2. **Topics + source text to claims:** Both the source text and the topic list are inserted into a second prompt template. Gemini returns `ClaimWithTopicResult` (list of `{ topic, claims[] }` objects). The service flattens this into `[{ claim_topic, claim }]` for the API response.

3. **Frontend to API:** Browser `fetch()` sends JSON body, receives JSON response. Frontend renders the `claims` array as an HTML table. CSV export iterates the same array client-side.

### Data Shape Transformations

```
Input (API):
  { source_text: string }

Internal (LLM step 1 output):
  { topics: string[] }

Internal (LLM step 2 output):
  { claim_topic: [{ topic: string, claim: string[] }] }

Output (API):
  { claims: [{ claim_topic: string, claim: string }] }
```

The key transformation is in the service layer: the nested `{ topic -> claims[] }` structure from the LLM is flattened into a flat array of `{ claim_topic, claim }` pairs. This flat structure is what the frontend table renders and what CSV export uses.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1-10 curators (current target) | Single Railway container. Uvicorn with 1 worker is fine. Gemini API calls are the bottleneck (~10-30s per request), not the server. |
| 10-50 concurrent users | Increase Uvicorn workers to 2-4. Add request queuing or rate limiting to avoid Gemini quota exhaustion. Consider adding a loading indicator with timeout. |
| 50+ concurrent users | Not a realistic scenario for this tool. If it happens: add a request queue, use background tasks with polling, or batch requests server-side. |

### Scaling Priorities

1. **First bottleneck: Gemini API latency.** Each request makes 2 sequential Gemini calls. With Gemini 2.5 Pro/Flash, expect 5-30 seconds per request depending on source text length. Mitigation: use Gemini 2.5 Flash (faster, cheaper) for the topic step, Gemini 2.5 Pro for the claim step. Or use Flash for both if latency is critical.
2. **Second bottleneck: Gemini API rate limits.** Google imposes per-minute request limits on Gemini API keys. With 2 calls per user request, 10 concurrent users = 20 Gemini calls. Mitigation: rate limiting middleware in FastAPI, or simply communicate expected wait times to curators.

## Anti-Patterns

### Anti-Pattern 1: Monolithic Extractor Class

**What people do:** Put all Gemini interaction, prompt formatting, response parsing, and pipeline orchestration into a single `ClaimExtractor` class (like the reference `PremiumClaimExtractor` does to some degree).

**Why it is wrong:** Violates single responsibility. Makes it impossible to test topic extraction independently from claim extraction. Makes prompt changes risky because they share a class.

**Do this instead:** Separate `TopicExtractor` and `ClaimExtractor` classes, each with one Gemini call. Service layer orchestrates them. Each can be unit tested with a mocked Gemini client.

### Anti-Pattern 2: Mixing LLM Schemas with API Schemas

**What people do:** Use the same Pydantic model for both the Gemini `response_schema` and the FastAPI response model.

**Why it is wrong:** LLM output shape and API output shape serve different purposes. The LLM schema is optimized for what Gemini can reliably produce (e.g., nested `{ topic, claims[] }`). The API schema is optimized for what the frontend needs (e.g., flat `{ claim_topic, claim }` pairs). Coupling them means changing one breaks the other.

**Do this instead:** Separate `schemas/llm.py` (Gemini response schemas) from `schemas/responses.py` (API response schemas). The service layer transforms between them.

### Anti-Pattern 3: Synchronous Gemini Calls in Async Endpoints

**What people do:** Call `client.models.generate_content()` directly in an `async def` endpoint handler, which blocks the event loop because the google-genai SDK's `generate_content` is synchronous.

**Why it is wrong:** Blocks the entire Uvicorn event loop while waiting for Gemini. Other requests cannot be served until the Gemini call completes (5-30 seconds).

**Do this instead:** Use `asyncio.get_event_loop().run_in_executor(None, ...)` to run the synchronous Gemini SDK call in a thread pool. The reference implementation's `GeminiService._call_gemini` demonstrates this pattern. Alternatively, if `google-genai` adds native async support, use `aio` variants.

### Anti-Pattern 4: Hardcoding Prompts in Extractor Classes

**What people do:** Write prompt strings directly in the extractor methods.

**Why it is wrong:** Prompts are iterated on frequently (wording changes, constraint additions, example updates). Burying them in code makes them hard to find, review, and compare versions.

**Do this instead:** Store prompts in `config/prompts/` as module-level string constants (following the reference implementation pattern). Import them into extractors. This makes prompt changes a single-file edit.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Gemini API (`generativelanguage.googleapis.com`) | `google-genai` SDK, synchronous `client.models.generate_content`, wrapped in `run_in_executor` for async | Requires `GEMINI_API_KEY` env var. Model configurable via settings. Use structured outputs (`response_schema` + `response_mime_type="application/json"`). |
| Railway (deployment) | Dockerfile, `PORT` env var, health check endpoint | Railway sets `PORT`. Dockerfile runs `uvicorn` on that port. Health check at `/docs` (or add a `/health` endpoint). |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Router <-> Service | Direct function call (dependency injection or instantiation) | Router creates service, calls `generate_claims()`. Pydantic models enforce contract. |
| Service <-> Extractors | Direct function call | Service calls `extractor.extract()`. Extractors return Pydantic models (LLM schemas). Service transforms to API schemas. |
| Extractors <-> Gemini SDK | SDK method call via `run_in_executor` | Extractors own the Gemini client instance. They format prompts, call Gemini, parse responses. Errors bubble up as exceptions. |
| Frontend <-> API | HTTP fetch (JSON) | Frontend sends `POST /generate/claims` with JSON body. Receives JSON response. No auth needed (out of scope). CORS allows same-origin (served by same FastAPI). |

## Build Order (Dependencies)

The following build order reflects component dependencies -- each step depends on the previous steps being in place.

```
Phase 1: Foundation (no dependencies)
  ├── Settings (config/settings.py)
  ├── Logger (infrastructure/logger.py)
  ├── LLM schemas (schemas/llm.py)
  └── Prompts (config/prompts/*.py)

Phase 2: Extraction Layer (depends on Phase 1)
  ├── TopicExtractor (extraction/topic_extractor.py)
  └── ClaimExtractor (extraction/claim_extractor.py)

Phase 3: Service Layer (depends on Phase 2)
  └── ClaimGenerationService (services/claim_generation.py)

Phase 4: API Layer (depends on Phase 3)
  ├── API schemas (schemas/requests.py, schemas/responses.py)
  ├── Router (routers/generate.py)
  └── FastAPI app (main.py)

Phase 5: Frontend (depends on Phase 4)
  ├── index.html
  ├── style.css
  └── app.js

Phase 6: Deployment (depends on all above)
  ├── Dockerfile
  ├── .env.example
  └── Railway config
```

**Why this order:**
- Settings and prompts have zero dependencies and everything depends on them.
- Extractors need settings (Gemini config) and prompts but nothing else. They can be built and tested with mocked Gemini responses before the API layer exists.
- The service needs extractors but not the API layer. It can be tested by calling it directly.
- The API layer wires everything together but is mostly boilerplate (FastAPI routing).
- Frontend is last because it only needs the API contract (request/response schemas), which is defined in Phase 4. Frontend can also be developed in parallel once the API schema is agreed upon.
- Deployment is last because it wraps everything into a container.

**Parallelization opportunity:** Phases 1 and 2 can be built in a single pass. The prompts, schemas, and extractors are tightly coupled enough that building them together is efficient. Similarly, Phases 4 and 5 can be built together since the API and frontend are simple.

## Sources

- Reference implementation: `submodules/extraction-api/src/extraction/premium_claim_extractor.py` -- PremiumClaimExtractor class demonstrating Gemini structured outputs with Pydantic schemas (HIGH confidence)
- Reference implementation: `submodules/extraction-api/src/pipeline/premium_extraction_pipeline.py` -- two-step pipeline pattern (topics then claims) (HIGH confidence)
- Reference implementation: `submodules/extraction-api/src/api/main.py` -- FastAPI app structure with CORS, lifespan, routers (HIGH confidence)
- Reference implementation: `submodules/extraction-api/src/config/settings.py` -- Pydantic BaseSettings pattern for configuration (HIGH confidence)
- Reference implementation: `submodules/extraction-api/src/config/prompts/` -- prompt-as-module pattern (HIGH confidence)
- Reference implementation: `submodules/extraction-api/src/infrastructure/gemini_service.py` -- `run_in_executor` pattern for sync SDK in async context (HIGH confidence)
- Reference implementation: `submodules/extraction-api/src/api/schemas/` -- separate request/response schema pattern (HIGH confidence)
- Reference implementation: `submodules/extraction-api/Dockerfile` -- Docker + uv deployment pattern for Railway (HIGH confidence)
- Project specification: `.planning/PROJECT.md` -- requirements, constraints, scope (HIGH confidence)

---
*Architecture research for: Stateless LLM-powered claim extraction API*
*Researched: 2026-02-14*

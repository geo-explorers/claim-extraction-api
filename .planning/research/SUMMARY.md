# Project Research Summary

**Project:** Claim Extraction API
**Domain:** Stateless LLM-powered text extraction API with web UI
**Researched:** 2026-02-14
**Confidence:** HIGH

## Executive Summary

This project is a stateless claim extraction service built on Gemini's structured output capabilities. The reference extraction-api codebase provides a proven implementation pattern: a two-step LLM pipeline (topics first, then claims mapped to topics) using Pydantic models as Gemini response schemas. This approach produces high-quality, topic-organized claims suitable for knowledge graph ingestion.

The recommended approach adapts the extraction-api's premium pipeline for general text (news, research, essays) instead of podcast transcripts. Core stack: Python 3.12+, FastAPI, google-genai SDK (>=1.50.0), Pydantic v2, with a plain HTML/JS frontend served by FastAPI. The service is explicitly stateless - no database, no persistence, just request-in/claims-out. Deploy via Railway with Docker using UV for fast, deterministic package management.

The critical risk is prompt brittleness: the extraction-api's prompts are deeply podcast-specific and will produce poor results on generic text without adaptation. Secondary risks include silent failures on Gemini API errors (the reference implementation swallows exceptions), safety filter blocks on controversial content, and cascading failures from the two-step pipeline. All are preventable through proper error handling, safety settings configuration, and prompt rewriting. The reference codebase provides solutions for infrastructure concerns (async Gemini client, retry logic, Railway deployment) but requires domain-specific adaptation for prompts and error UX.

## Key Findings

### Recommended Stack

From STACK.md: The extraction-api provides a battle-tested stack with exact version numbers from `uv.lock`. All core technologies are proven working together in production.

**Core technologies:**
- **Python 3.12+**: Modern type hints, proven in extraction-api. No need for 3.13, 3.12 is the compatibility sweet spot.
- **FastAPI >=0.121.0**: Async-native, auto-generates OpenAPI docs, serves static files. The `fastapi[standard]` extra bundles uvicorn and essentials.
- **google-genai >=1.50.0**: The NEW unified SDK (not the deprecated `google-generativeai`). Native support for `response_schema` with Pydantic models - the core of this project.
- **Pydantic >=2.10.0**: Dual role as API validation AND Gemini response schema. V2 required for `model_validate_json()` and JSON schema generation.
- **UV (latest)**: Rust-based package manager, 10-100x faster than pip/poetry. Proven in extraction-api Docker builds with `uv sync --frozen`.

**Critical version compatibility:** FastAPI 0.100+ requires Pydantic v2. google-genai 1.50+ works with Pydantic 2.10+. All versions are minimums from extraction-api's proven lockfile.

**Key pattern from stack research:** Use `response_schema=PydanticModel` (pass the class) with `response_mime_type="application/json"`. Do NOT use `response_json_schema=Model.model_json_schema()` (the dict-based approach). This is the cleaner pattern from extraction-api's premium extractor.

### Expected Features

From FEATURES.md: Claims must be self-contained, atomic, and organized by topic. These are non-negotiable quality requirements.

**Must have (table stakes):**
- Two-step extraction pipeline (topics then claims) - proven superior to single-pass
- Topic-organized claims output - prevents undifferentiated wall of text
- Self-contained claims (no pronouns/references) - enforced via "Shuffle Rule" from extraction-api
- Atomic claims (one fact each, 5-32 words) - makes claims verifiable and graph-ready
- Web UI with textarea and results table - curators are non-technical
- CSV export - downstream workflow integration
- Loading indicator - LLM calls take 10-60 seconds, users need feedback
- Error handling with clear messages - distinguish "no claims found" from "API error"

**Should have (competitive):**
- Attribution stripping - claims state facts directly, not "Dr. X said..."
- Topic filtering (min claims threshold) - discard noise topics with <3 claims
- Copy-to-clipboard per claim - curator convenience
- Health check endpoint - Railway deployment monitoring

**Defer (v2+):**
- Source type hints (news/research/etc) - add when one-size-fits-all prompt proves insufficient
- Claim quality scoring - requires feedback loop to train metrics
- Multi-language support - prompts are English-optimized, multilingual is scope creep

**Anti-features to avoid:**
- Database/persistence - contradicts stateless architecture, claims belong in Geo knowledge graph
- User authentication - no user accounts in this tool per PROJECT.md
- Key takeaway extraction - curators are the domain experts, not the AI
- Real-time streaming - Gemini structured outputs return complete response at once
- Batch processing - curators work one text at a time

### Architecture Approach

From ARCHITECTURE.md: Clean layered architecture separates concerns. The two-step pipeline is the core pattern, with service layer orchestrating sequential extractor calls.

**Major components:**
1. **FastAPI app (main.py)** - HTTP routing, CORS, error handling, static file serving for frontend
2. **ClaimGenerationService** - Orchestrates two-step pipeline, transforms LLM results to API format
3. **TopicExtractor** - First Gemini call: source text → topics list (TopicResult Pydantic schema)
4. **ClaimExtractor** - Second Gemini call: source text + topics → claims by topic (ClaimWithTopicResult schema)
5. **Static frontend (HTML/JS)** - Plain vanilla JS, no build step, served via FastAPI.mount()
6. **Settings (Pydantic BaseSettings)** - Loads GEMINI_API_KEY, model name, temperature, PORT from .env

**Key patterns:**
- **Two-step sequential pipeline**: Topic extraction first constrains claim extraction, reduces hallucination, produces better organization
- **Pydantic as LLM schema**: Pass `response_schema=PydanticModel` to Gemini, parse with `model_validate_json(response.text)`
- **Stateless request-response**: No database, no sessions, no background jobs. Trivial horizontal scaling.
- **Async wrapper for sync SDK**: google-genai's `generate_content` is synchronous. Wrap in `run_in_executor()` to avoid blocking FastAPI event loop.

**Recommended structure:** Separate `schemas/llm.py` (Gemini response schemas) from `schemas/responses.py` (API response schemas). Service layer transforms between them. Prompts isolated in `config/prompts/` for easy iteration.

### Critical Pitfalls

From PITFALLS.md: Most pitfalls are recoverable with 1-4 hours effort, but must be addressed in Phase 1 to avoid poor UX.

1. **Silent empty responses on Gemini API failures** - extraction-api catches all exceptions and returns empty lists. For user-facing API, this is terrible UX. Users see blank table, no error. **Fix:** Propagate errors as typed exceptions, return appropriate HTTP status codes, distinguish "no claims found" from "LLM error."

2. **Prompt brittleness to non-podcast text** - Prompts from extraction-api reference "episode," "host," "transcript" throughout. Ad filtering rejects legitimate content. Topic count guidance (6-14) is podcast-specific. **Fix:** Adapt prompts to generic "source text" language, remove/tune ad filtering, scale topic count to text length. Test against 3+ text types before shipping.

3. **Schema mismatch between `response_schema` and `response_json_schema`** - extraction-api uses both patterns inconsistently. They behave differently. **Fix:** Standardize on `response_schema=PydanticModel` everywhere (the cleaner, more supported approach).

4. **Cascading failure and doubled latency from two-step pipeline** - Two sequential Gemini calls mean 15-30+ seconds total. If topic extraction returns garbage, claim extraction fails. **Fix:** Show loading phases ("Extracting topics..." then "Extracting claims..."), validate topic output before proceeding, use Flash for speed or Flash+Pro split.

5. **Gemini API rate limits** - Free tier: 2 RPM for Pro, 15 RPM for Flash. Each user request = 2 LLM calls. Concurrent users hit limits immediately. **Fix:** Retry with exponential backoff on 429/503, use gemini-2.5-flash (higher rate limits), add request queuing/rate limiting at API level.

6. **Safety filters blocking legitimate content** - Default filters block political/health/violence content. extraction-api's premium extractor doesn't configure safety settings. **Fix:** Set `BLOCK_NONE` safety settings (copy pattern from extraction-api's gemini_service.py), check `finish_reason` for SAFETY blocks.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Core Extraction API
**Rationale:** Foundation must be solid before adding frontend. All infrastructure concerns (Gemini client, retry logic, error handling, safety settings) must be built in, not bolted on later.

**Delivers:** Working API endpoint that accepts source text and returns topic-organized claims.

**Addresses:**
- Settings and configuration (Pydantic BaseSettings, .env loading)
- Gemini client initialization (singleton pattern)
- LLM response schemas (TopicResult, ClaimWithTopicResult)
- Prompts adapted from extraction-api (rewritten for generic text, tested against 3+ types)
- Topic extractor (Gemini call #1)
- Claim extractor (Gemini call #2)
- Service layer (orchestrates two-step pipeline)
- API schemas (request/response validation)
- Router with POST /generate/claims endpoint
- Error handling (typed exceptions, appropriate HTTP status codes)
- Retry logic with exponential backoff (handles 429/503)
- Safety settings configuration (BLOCK_NONE)
- Input validation (min/max text length)
- Health check endpoint (GET /health)

**Avoids:**
- Silent empty responses (Pitfall #1) - error propagation from day one
- Prompt brittleness (Pitfall #2) - prompts adapted and tested before any code
- Schema mismatch (Pitfall #3) - standardize on response_schema pattern
- Rate limit failures (Pitfall #5) - retry logic built in
- Safety filter blocks (Pitfall #6) - BLOCK_NONE configured
- Cost explosion (Pitfall from PITFALLS.md) - input length validation

**Research flag:** SKIP - all patterns proven in extraction-api. Direct adaptation, not new research.

### Phase 2: Web UI and User Experience
**Rationale:** API must be working before building UI. Frontend is pure presentation, no business logic.

**Delivers:** Self-contained web interface for curators to paste text and export claims.

**Addresses:**
- Static HTML page (textarea, generate button, results table)
- Client-side JavaScript (fetch API, render table, loading states)
- CSS styling (clean, professional, accessible)
- Loading indicator with phase progress ("Extracting topics..." → "Extracting claims...")
- Error display (shows API error messages clearly)
- CSV export (client-side, handles commas/quotes/newlines correctly)
- Copy-to-clipboard per claim (optional, can defer to v1.1)
- FastAPI static file mounting (serve frontend from same process)

**Avoids:**
- Poor loading UX (Pitfall #4) - shows extraction phases, disables button during processing
- Overwhelming claim wall (UX pitfall from PITFALLS.md) - claims grouped by topic

**Research flag:** SKIP - plain HTML/JS, no framework, no build step. Standard patterns.

### Phase 3: Deployment and Validation
**Rationale:** Get to production fast, validate with real curator usage before adding features.

**Delivers:** Service running on Railway, ready for curator testing.

**Addresses:**
- Dockerfile (multi-stage build with UV, proven from extraction-api)
- .env.example (documents required environment variables)
- Railway configuration (railway.toml or Railway dashboard setup)
- Health check configuration (Railway uses /health endpoint)
- Production settings (PORT from env, 0.0.0.0 host binding)
- Documentation (README with setup instructions, API examples)

**Avoids:**
- Deployment gotchas from PITFALLS.md (PORT env var, health check path)

**Research flag:** SKIP - Railway deployment proven in extraction-api. Direct copy.

### Phase Ordering Rationale

**Why API-first:**
- Prompts are the product. They must be adapted and tested before writing UI code.
- Error handling and retry logic are infrastructure concerns. Building them in from Phase 1 prevents painful refactoring later.
- The extraction-api reference provides all patterns needed - this is adaptation, not invention.

**Why frontend-second:**
- API contract (request/response schemas) must be stable before building UI.
- Frontend is pure presentation. No dependencies on extractors/service layer.
- Can be built quickly once API works - plain HTML/JS with no build step.

**Why deployment-last:**
- Need working API + frontend to deploy anything useful.
- extraction-api Dockerfile and railway.toml provide direct template.
- Railway deployment is straightforward once app runs locally.

**Dependency chain:**
```
Settings/Prompts → Extractors → Service → API → Frontend → Deployment
(parallel ok)      (parallel ok)  (needs extractors) (needs API) (needs both)
```

### Research Flags

**Phases needing deeper research:** NONE. All patterns proven in extraction-api reference implementation.

**Phases with standard patterns (skip research-phase):**
- **Phase 1:** Gemini structured outputs, FastAPI routing, Pydantic schemas - all demonstrated in extraction-api
- **Phase 2:** Static HTML/JS served by FastAPI - standard pattern, no framework complexity
- **Phase 3:** Docker + Railway deployment - extraction-api provides working template

**When to trigger /gsd:research-phase during planning:**
- If prompt quality is insufficient after initial adaptation (unlikely - extraction-api prompts are excellent starting point)
- If Gemini API behavior differs significantly from extraction-api patterns (check google-genai SDK version compatibility)
- If Railway deployment patterns have changed (verify railway.toml format is current)

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions from extraction-api's uv.lock - proven working combination. Only uncertainty is google-genai async API availability (use run_in_executor as fallback). |
| Features | HIGH | Feature requirements derived from extraction-api's premium pipeline + PROJECT.md constraints. Table stakes and anti-features are well-defined. |
| Architecture | HIGH | Direct reference implementation in extraction-api. All patterns demonstrated and proven. Structure is clean separation of concerns. |
| Pitfalls | HIGH | Most pitfalls observed directly in extraction-api codebase (silent failures, podcast-specific prompts, sync SDK in async context). Solutions proven in other parts of same codebase. |

**Overall confidence:** HIGH

The extraction-api reference implementation provides HIGH confidence for all technical decisions. The codebase is well-structured, recently updated (2026-02 based on lockfile versions), and solves the exact same problem (Gemini structured outputs for claim extraction) with proven patterns.

### Gaps to Address

**Prompt adaptation quality:** The prompts require rewriting for generic text, not just find-replace of "podcast"/"episode." This cannot be fully validated until testing with real curator source texts. **Mitigation:** Test against 3+ text types (news article, research abstract, essay) during Phase 1 implementation. Iterate prompts based on extraction quality.

**Gemini model availability:** Research assumes gemini-2.5-flash and gemini-2.5-pro are available. If Google deprecates these models or changes pricing/rate limits, fallback needed. **Mitigation:** Make model name configurable via GEMINI_MODEL env var (already planned). Monitor Google AI announcements.

**Curator workflow integration:** PROJECT.md describes Geo Curator Program but doesn't detail their full workflow (how they get source texts, where claims go after extraction). **Mitigation:** This is out of scope for the API itself - CSV export handles downstream integration. Validate with curators during Phase 3.

**Scale assumptions:** Research assumes 1-10 concurrent curators (internal tool, not public service). If usage exceeds this, rate limiting and queuing needed. **Mitigation:** Start with simple deployment, monitor usage metrics in production. Add rate limiting in v1.1 if needed.

## Sources

### Primary (HIGH confidence)
- **extraction-api reference implementation** (`/home/john_malkovich/work/claim-api/submodules/extraction-api/`) - All source code, proven patterns, locked dependency versions
- **extraction-api `uv.lock`** - Exact versions for google-genai 1.52.0, fastapi 0.121.2, pydantic 2.12.3, pydantic-settings 2.11.0, uvicorn 0.38.0
- **extraction-api `premium_claim_extractor.py`** - Gemini structured output pattern with response_schema
- **extraction-api `gemini_service.py`** - Async wrapper pattern, retry logic, safety settings
- **extraction-api prompts** (`config/prompts/claim_extraction_prompt.py`, `topics_of_discussion_extraction_prompt.py`) - Prompt structure and quality criteria
- **extraction-api `Dockerfile` and `railway.toml`** - Deployment patterns
- **PROJECT.md** (`.planning/PROJECT.md`) - Requirements and constraints

### Secondary (MEDIUM confidence)
- google-genai SDK async API availability - extraction-api uses sync client with run_in_executor. Async may be available in newer SDK versions. Needs verification at implementation time.

### Tertiary (LOW confidence)
- Gemini model naming/availability long-term - "gemini-2.5-flash" and "gemini-2.5-pro" are current names but Google may change/deprecate models. Make configurable.

---
*Research completed: 2026-02-14*
*Ready for roadmap: yes*

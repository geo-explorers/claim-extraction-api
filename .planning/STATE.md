# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-14)

**Core value:** Curators can paste any source text and get back a clean table of topic-organized, self-contained claims ready for the Geo knowledge graph.
**Current focus:** Phase 3 - Deployment -- COMPLETE

## Current Position

Phase: 3 of 3 (Deployment) -- COMPLETE
Plan: 1 of 1 in current phase
Status: All Phases Complete
Last activity: 2026-02-14 -- Completed 03-01-PLAN.md (Docker + Railway deployment)

Progress: [████████████████████████████████] 100%

## Performance Metrics

**Velocity:**
- Total plans completed: 6
- Average duration: 3min
- Total execution time: 0.33 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-core-extraction-api | 4/4 | 15min | 4min |
| 02-web-ui | 1/1 | 2min | 2min |
| 03-deployment | 1/1 | 3min | 3min |

**Recent Trend:**
- Last 5 plans: 01-03 (5min), 01-04 (3min), 02-01 (2min), 03-01 (3min)
- Trend: Steady

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: 3-phase quick depth -- API first, then UI, then deployment
- [Roadmap]: INFR-03 through INFR-07 (config, tooling) bundled into Phase 1 since API needs them to function
- [01-01]: Settings class not singleton -- instantiated in FastAPI lifespan for fail-fast on missing GEMINI_API_KEY
- [01-01]: LLM schemas use plural field names (claims, claim_topics) for Gemini output clarity
- [01-01]: Exception hierarchy extends HTTPException directly for automatic FastAPI handling
- [01-02]: Retry predicate uses google.genai.errors.ServerError + ClientError(code=429) since google.api_core not installed
- [01-02]: genai.Client import in TYPE_CHECKING block (from __future__ annotations makes it string-only at runtime)
- [01-02]: Removed ad-filtering from claim prompt -- generic source texts have legitimate URLs/CTAs
- [01-03]: All service instances constructed in lifespan and stored on app.state for singleton behavior
- [01-03]: Used Annotated[..., Depends()] pattern to satisfy ruff B008
- [01-03]: TYPE_CHECKING blocks in tests for mock type imports to satisfy ruff TC003
- [01-04]: gemini_api_key is str | None with default=None -- not required at startup
- [01-04]: app.state.claim_generation_service = None when key absent; dependency raises 503
- [01-04]: monkeypatch.setenv (empty string) overrides .env file in pydantic-settings tests
- [02-01]: Route inline in main.py -- single GET / route doesn't warrant separate ui.py router
- [02-01]: Tailwind v4 CDN -- current version, no v3 lock-in, modern browser support sufficient
- [02-01]: BASE_DIR = Path(__file__).resolve().parent for template/static directory resolution
- [03-01]: Removed BuildKit cache mounts for legacy Docker compatibility (--mount=type=cache requires buildx)
- [03-01]: Shell-form CMD for Railway $PORT expansion (exec-form cannot expand env vars)
- [03-01]: Added --proxy-headers to uvicorn CMD for Railway reverse proxy

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-02-14
Stopped at: Completed 03-01-PLAN.md (Docker + Railway deployment). All phases complete. Project ready for production deployment.
Resume file: .planning/phases/03-deployment/03-01-SUMMARY.md

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-14)

**Core value:** Curators can paste any source text and get back a clean table of topic-organized, self-contained claims ready for the Geo knowledge graph.
**Current focus:** Phase 1 - Core Extraction API

## Current Position

Phase: 1 of 3 (Core Extraction API)
Plan: 2 of 3 in current phase
Status: Executing
Last activity: 2026-02-14 -- Completed 01-02-PLAN.md

Progress: [██████░░░░] 22%

## Performance Metrics

**Velocity:**
- Total plans completed: 2
- Average duration: 3.5min
- Total execution time: 0.12 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-core-extraction-api | 2/3 | 7min | 3.5min |

**Recent Trend:**
- Last 5 plans: 01-01 (3min), 01-02 (4min)
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

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-02-14
Stopped at: Completed 01-02-PLAN.md (extraction pipeline). Next: 01-03-PLAN.md (API endpoint)
Resume file: .planning/phases/01-core-extraction-api/01-02-SUMMARY.md

---
phase: 01-core-extraction-api
plan: 04
subsystem: api
tags: [fastapi, pydantic-settings, health-check, graceful-degradation]

# Dependency graph
requires:
  - phase: 01-core-extraction-api (plans 01-03)
    provides: Settings class, lifespan, dependencies, health/generate endpoints
provides:
  - Optional GEMINI_API_KEY startup -- app starts without Gemini config
  - Health endpoint always available regardless of Gemini configuration
  - HTTP 503 with clear error on generate endpoints when Gemini not configured
  - Gap closure for UAT health endpoint blocker
affects: [deployment, railway, ci-cd, monitoring]

# Tech tracking
tech-stack:
  added: []
  patterns: [graceful-degradation, optional-service-initialization, env-var-gating]

key-files:
  created: []
  modified:
    - src/config/settings.py
    - src/main.py
    - src/dependencies.py
    - tests/test_routers/test_health.py

key-decisions:
  - "gemini_api_key is str | None with default=None, not required at startup"
  - "Empty string GEMINI_API_KEY treated as unset (falsy check)"
  - "app.state.claim_generation_service set to None when key absent"
  - "Dependency uses getattr with None fallback for safe state access"

patterns-established:
  - "Graceful degradation: core endpoints (health) always work, feature endpoints return 503 when dependencies unavailable"
  - "Environment gating: conditional service initialization based on env var presence"

# Metrics
duration: 3min
completed: 2026-02-14
---

# Phase 01 Plan 04: Gap Closure -- Health Endpoint Without GEMINI_API_KEY

**Optional GEMINI_API_KEY with graceful degradation: health always responds, generate returns 503 when Gemini not configured**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-14T14:06:50Z
- **Completed:** 2026-02-14T14:09:43Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- App starts successfully without GEMINI_API_KEY environment variable
- GET /health returns {"status": "ok"} regardless of Gemini configuration
- POST /generate/claims returns HTTP 503 with clear "not configured" error when key absent
- All 23 tests pass (21 existing + 2 new gap-closure tests)
- All quality gates pass: ruff check, mypy --strict, pytest

## Task Commits

Each task was committed atomically:

1. **Task 1: Make gemini_api_key optional and defer Gemini initialization** - `6e602f9` (fix)
2. **Task 2: Update tests for health-without-key and generate-without-key** - `f3e833a` (test)

## Files Created/Modified
- `src/config/settings.py` - gemini_api_key changed from required str to optional str | None
- `src/main.py` - Lifespan conditionally creates Gemini client; logs warning when key absent
- `src/dependencies.py` - get_claim_generation_service raises HTTP 503 when service is None
- `tests/test_routers/test_health.py` - Added gap-closure tests; refactored to use monkeypatch fixtures

## Decisions Made
- Used `str | None = Field(default=None)` rather than making Settings accept missing key silently -- explicit optional typing
- Set `app.state.claim_generation_service = None` in else branch rather than omitting -- explicit None allows safe getattr pattern
- Used `monkeypatch.setenv("GEMINI_API_KEY", "")` in tests rather than `delenv` -- env var overrides .env file values in pydantic-settings
- Used `getattr(request.app.state, "claim_generation_service", None)` for defensive access pattern

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test env var override for .env file**
- **Found during:** Task 2 (test_generate_returns_503_without_gemini_key)
- **Issue:** `monkeypatch.delenv("GEMINI_API_KEY")` does not prevent pydantic-settings from reading .env file, so the key was still loaded
- **Fix:** Used `monkeypatch.setenv("GEMINI_API_KEY", "")` instead -- env vars take precedence over .env file in pydantic-settings, and empty string is falsy
- **Files modified:** tests/test_routers/test_health.py
- **Verification:** All 4 health tests pass including 503 scenario
- **Committed in:** f3e833a (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Auto-fix necessary for correct test behavior with pydantic-settings .env loading. No scope creep.

## Issues Encountered
None beyond the deviation documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 01 gap closure complete -- all UAT criteria now pass
- Health endpoint proven to work in deployment scenarios without Gemini configuration
- Ready for Phase 2 (UI) or deployment

---
*Phase: 01-core-extraction-api*
*Completed: 2026-02-14*

## Self-Check: PASSED

All files found. All commits verified.

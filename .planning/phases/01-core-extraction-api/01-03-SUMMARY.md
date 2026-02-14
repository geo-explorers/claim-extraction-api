---
phase: 01-core-extraction-api
plan: 03
subsystem: api
tags: [fastapi, dependency-injection, pytest, testing, endpoint]

# Dependency graph
requires:
  - "01-01: FastAPI app shell with lifespan, Settings, schemas, exceptions, GET /health"
  - "01-02: TopicExtractor, ClaimExtractor, ClaimGenerationService, prompts"
provides:
  - "POST /generate/claims endpoint accepting {source_text} returning {claims: [{claim_topic, claim}]}"
  - "Dependency injection wiring Settings -> Gemini client -> Extractors -> Service -> Route"
  - "Full test suite (21 tests) covering endpoints, service, and extractors with mocked Gemini"
  - "All quality gates passing: ruff check, mypy --strict, pytest"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: [annotated-depends-for-fastapi-di, app-state-lifespan-singletons, testclient-with-dependency-overrides]

key-files:
  created:
    - src/dependencies.py
    - src/routers/generate.py
    - tests/__init__.py
    - tests/conftest.py
    - tests/test_routers/__init__.py
    - tests/test_routers/test_health.py
    - tests/test_routers/test_generate.py
    - tests/test_services/__init__.py
    - tests/test_services/test_claim_generation.py
    - tests/test_extraction/__init__.py
    - tests/test_extraction/test_topic_extractor.py
    - tests/test_extraction/test_claim_extractor.py
  modified:
    - src/main.py

key-decisions:
  - "All service instances constructed in lifespan and stored on app.state for singleton behavior"
  - "Used Annotated[..., Depends()] pattern to satisfy ruff B008 (no function calls in defaults)"
  - "TYPE_CHECKING blocks in tests for mock type imports to satisfy ruff TC003 with from __future__ annotations"

patterns-established:
  - "Dependency injection via app.state: lifespan constructs services, dependency function retrieves from request.app.state"
  - "Annotated[Type, Depends(provider)] for FastAPI route parameters"
  - "TestClient with dependency_overrides for endpoint testing without real Gemini calls"
  - "Test organization: test_routers/ for endpoints, test_services/ for orchestration, test_extraction/ for extractors"

# Metrics
duration: 5min
completed: 2026-02-14
---

# Phase 1 Plan 3: API Endpoint & Test Suite Summary

**POST /generate/claims endpoint with dependency-injected extraction pipeline and 21-test suite covering all layers with mocked Gemini**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-14T13:24:47Z
- **Completed:** 2026-02-14T13:30:04Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments
- Wired full extraction pipeline (TopicExtractor + ClaimExtractor + ClaimGenerationService) into FastAPI via dependency injection using app.state lifespan pattern
- Created POST /generate/claims endpoint accepting source_text, returning {claims: [{claim_topic, claim}]}
- Built comprehensive test suite: 21 tests across 4 test modules covering health endpoint, generate endpoint (success + 4 validation + 2 error), service orchestration (success + 2 empty + transform), topic extractor (success + fallback + parse error + safety), claim extractor (success + fallback + parse error + prompt check)
- All quality gates pass: ruff check (0 errors on src/ and tests/), mypy --strict (0 errors), pytest (21/21 green)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create dependency injection and generate endpoint, wire into app** - `6b0acc1` (feat)
2. **Task 2: Write complete test suite** - `71570cf` (test)

## Files Created/Modified
- `src/dependencies.py` - FastAPI dependency function retrieving ClaimGenerationService from app.state
- `src/routers/generate.py` - POST /generate/claims endpoint with Annotated Depends pattern
- `src/main.py` - Updated lifespan to construct full service graph; includes generate router
- `tests/__init__.py` - Package init
- `tests/conftest.py` - Shared fixtures: mock Gemini, sample data, TestClient with dependency overrides
- `tests/test_routers/test_health.py` - Health endpoint tests (2 tests)
- `tests/test_routers/test_generate.py` - Generate endpoint integration tests (7 tests)
- `tests/test_services/test_claim_generation.py` - Service orchestration tests (4 tests)
- `tests/test_extraction/test_topic_extractor.py` - Topic extractor unit tests (4 tests)
- `tests/test_extraction/test_claim_extractor.py` - Claim extractor unit tests (4 tests)
- `tests/test_routers/__init__.py` - Package init
- `tests/test_services/__init__.py` - Package init
- `tests/test_extraction/__init__.py` - Package init

## Decisions Made
- All service instances (TopicExtractor, ClaimExtractor, ClaimGenerationService) are constructed once in the FastAPI lifespan and stored on app.state -- the dependency function simply retrieves the singleton. This avoids constructing services per-request.
- Used `Annotated[ClaimGenerationService, Depends(get_claim_generation_service)]` instead of `= Depends(...)` default argument pattern to satisfy ruff B008 rule. This is the modern FastAPI recommended approach.
- Test mock types (AsyncMock, MagicMock) placed in TYPE_CHECKING blocks in extraction/router test files since `from __future__ import annotations` makes annotation-only usage string-evaluated, satisfying ruff TC003.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ruff B008 on Depends() in default argument**
- **Found during:** Task 1
- **Issue:** `service: ClaimGenerationService = Depends(get_claim_generation_service)` flagged by ruff B008 (no function calls in argument defaults)
- **Fix:** Changed to `Annotated[ClaimGenerationService, Depends(get_claim_generation_service)]` pattern
- **Files modified:** src/routers/generate.py
- **Committed in:** 6b0acc1 (Task 1 commit)

**2. [Rule 1 - Bug] Fixed ruff TC003/E501 lint issues in test files**
- **Found during:** Task 2
- **Issue:** ruff flagged type-only imports outside TYPE_CHECKING blocks and lines exceeding 99 chars
- **Fix:** Moved type-only imports into TYPE_CHECKING blocks, shortened long string literals
- **Files modified:** tests/conftest.py, all test files
- **Committed in:** 71570cf (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs/lint)
**Impact on plan:** Standard lint compliance. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 1 is complete: the API is fully functional with POST /generate/claims endpoint
- All source code passes ruff check and mypy --strict
- 21 tests provide confidence for future changes
- Ready for Phase 2 (UI or deployment depending on roadmap)

## Self-Check: PASSED

- All 13 files verified present on disk
- Both task commits verified in git log (6b0acc1, 71570cf)
- SUMMARY.md exists at expected path

---
*Phase: 01-core-extraction-api*
*Completed: 2026-02-14*

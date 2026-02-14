---
phase: 01-core-extraction-api
plan: 02
subsystem: api
tags: [google-genai, tenacity, pydantic, prompt-engineering, gemini]

# Dependency graph
requires:
  - "01-01: Settings, LLM schemas (TopicResult, ClaimWithTopicResult), API response schemas (ClaimResponse, ClaimGenerationResponse), exception hierarchy"
provides:
  - "Topic extraction prompt adapted for generic source text with scaled topic counts"
  - "Claim extraction prompt with self-containment rules, no ad filtering"
  - "TopicExtractor class with async Gemini calls, tenacity retry, BLOCK_NONE safety"
  - "ClaimExtractor class with async Gemini calls, tenacity retry, BLOCK_NONE safety"
  - "ClaimGenerationService orchestrating two-step pipeline with fail-fast validation"
affects: [01-03-PLAN]

# Tech tracking
tech-stack:
  added: []
  patterns: [tenacity-retry-on-gemini-calls, type-checking-block-for-genai-imports, custom-retryable-predicate-for-429-and-5xx]

key-files:
  created:
    - src/config/prompts/__init__.py
    - src/config/prompts/topic_extraction.py
    - src/config/prompts/claim_extraction.py
    - src/extraction/__init__.py
    - src/extraction/topic_extractor.py
    - src/extraction/claim_extractor.py
    - src/services/__init__.py
    - src/services/claim_generation.py
  modified: []

key-decisions:
  - "Used google.genai.errors.ServerError + ClientError(code=429) for retry predicate instead of google.api_core.exceptions (not installed)"
  - "genai.Client type annotation moved to TYPE_CHECKING block since from __future__ import annotations makes it string-only at runtime"
  - "Removed entire ad-filtering step from claim prompt -- legitimate URLs and CTAs in news/research would be incorrectly stripped"

patterns-established:
  - "Tenacity retry pattern: _is_retryable predicate checking ServerError (5xx) or ClientError with code 429"
  - "Safety settings: BLOCK_NONE on all 4 harm categories (HATE_SPEECH, HARASSMENT, SEXUALLY_EXPLICIT, DANGEROUS_CONTENT)"
  - "Response parsing: try response.parsed first, fall back to model_validate_json(response.text)"
  - "Prompt formatting: {source_text} for topics, {topics} + {source_text} for claims"

# Metrics
duration: 4min
completed: 2026-02-14
---

# Phase 1 Plan 2: Extraction Pipeline Summary

**Two-step Gemini extraction pipeline: topic extraction then claim extraction with tenacity retry, BLOCK_NONE safety, and orchestration service transforming LLM output to API response shape**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-14T13:17:58Z
- **Completed:** 2026-02-14T13:22:19Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Adapted topic extraction prompt for generic source text: removed all podcast language, added text-length-scaled topic count guidance (2-5/4-8/6-12), single {source_text} placeholder
- Adapted claim extraction prompt: removed ad-filtering step entirely, preserved all self-containment rules (Shuffle Rule, pronoun replacement, attribution stripping, 5-32 word constraint), updated output format to match ClaimWithTopicResult schema
- Built TopicExtractor and ClaimExtractor with async Gemini calls, tenacity retry (3 attempts, exponential backoff) on 429/5xx, BLOCK_NONE safety settings, response.parsed -> model_validate_json fallback parsing
- Built ClaimGenerationService orchestrating topic->claim pipeline with fail-fast EmptyExtractionError on empty topics/claims, RetryError -> LLMProviderError conversion, and flat ClaimResponse output transformation
- All 19 source files pass ruff check and mypy --strict with zero errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Adapt extraction prompts for generic source text** - `8c91d26` (feat)
2. **Task 2: Build extractors with retry logic and orchestration service** - `355323c` (feat)

## Files Created/Modified
- `src/config/prompts/__init__.py` - Empty package init
- `src/config/prompts/topic_extraction.py` - TOPIC_EXTRACTION_PROMPT adapted for generic source text with {source_text} placeholder
- `src/config/prompts/claim_extraction.py` - CLAIM_EXTRACTION_PROMPT with self-containment rules, {topics} and {source_text} placeholders
- `src/extraction/__init__.py` - Empty package init
- `src/extraction/topic_extractor.py` - TopicExtractor class with tenacity retry, BLOCK_NONE safety, TopicResult schema
- `src/extraction/claim_extractor.py` - ClaimExtractor class with tenacity retry, BLOCK_NONE safety, ClaimWithTopicResult schema
- `src/services/__init__.py` - Empty package init
- `src/services/claim_generation.py` - ClaimGenerationService orchestrating two-step pipeline

## Decisions Made
- Used `google.genai.errors.ServerError` and `ClientError` with code=429 check for retry predicate, since `google.api_core.exceptions` (ResourceExhausted, ServiceUnavailable) is not installed as a dependency of google-genai
- Moved `google.genai` (the `genai.Client` import) into `TYPE_CHECKING` block since `from __future__ import annotations` makes type annotations string-evaluated at runtime, satisfying both ruff TC002 and mypy
- Removed the entire "ADVERTISEMENT & PROMOTION FILTERING" step from the claim extraction prompt because generic source texts (news articles, research papers, reports) contain legitimate URLs and calls-to-action that would be incorrectly stripped

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Ruff TC002/TC006 lint rules required `genai.Client` type import in TYPE_CHECKING block and quoted strings in `cast()` calls -- resolved by proper import organization and string-quoted cast types
- `google.api_core.exceptions` not available (not a dependency of google-genai) -- used `google.genai.errors.ServerError` and `ClientError` with code check as documented in Decisions

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Extraction pipeline complete and ready to be wired into POST /generate endpoint in Plan 03
- ClaimGenerationService is the single entry point: takes source_text, returns ClaimGenerationResponse
- Topic and claim extractors need a genai.Client (initialized in FastAPI lifespan on app.state) and model/temperature from Settings

## Self-Check: PASSED

- All 8 source files verified present on disk
- Both task commits verified in git log (8c91d26, 355323c)
- SUMMARY.md exists at expected path

---
*Phase: 01-core-extraction-api*
*Completed: 2026-02-14*

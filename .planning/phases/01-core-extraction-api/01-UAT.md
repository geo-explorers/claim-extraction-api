---
status: complete
phase: 01-core-extraction-api
source: 01-01-SUMMARY.md, 01-02-SUMMARY.md, 01-03-SUMMARY.md
started: 2026-02-14T14:00:00Z
updated: 2026-02-14T14:05:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Quality gates pass
expected: Run `uv run ruff check src/ tests/`, `uv run mypy --strict src/`, and `uv run pytest`. All three should pass with zero errors and all 21 tests green.
result: pass

### 2. Health endpoint responds
expected: Start the server with `uv run uvicorn src.main:app`. GET http://localhost:8000/health returns `{"status": "ok"}` with HTTP 200. No Gemini API call is made.
result: issue
reported: "App crashes on startup with ValidationError for missing gemini_api_key. Health endpoint is unreachable without setting GEMINI_API_KEY, even though health should not require Gemini."
severity: blocker

### 3. Claim generation with valid input
expected: POST http://localhost:8000/generate/claims with body `{"source_text": "<paste a news article paragraph>"}`. Returns HTTP 200 with JSON `{"claims": [{"claim_topic": "...", "claim": "..."}]}` where each claim is self-contained (no pronouns/dangling references) and atomic (one fact).
result: pass

### 4. Input validation - empty text
expected: POST /generate/claims with `{"source_text": ""}` or `{"source_text": "   "}` returns an error response with an appropriate HTTP status code (422), not an empty result or 500.
result: pass

### 5. Input validation - too short text
expected: POST /generate/claims with `{"source_text": "Hi"}` (very short text) returns a validation error with a clear message about minimum length, not an empty result.
result: pass

## Summary

total: 5
passed: 4
issues: 1
pending: 0
skipped: 0

## Gaps

- truth: "GET /health returns {status: ok} without requiring Gemini API key"
  status: failed
  reason: "User reported: App crashes on startup with ValidationError for missing gemini_api_key. Health endpoint is unreachable without setting GEMINI_API_KEY, even though health should not require Gemini."
  severity: blocker
  test: 2
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

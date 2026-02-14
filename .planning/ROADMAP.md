# Roadmap: Claim Service

## Overview

Deliver a stateless claim extraction API and web UI that lets Geo curators paste source text and get back topic-organized claims ready for the knowledge graph. The project progresses from a working API with Gemini-powered extraction, to a web interface for non-technical curators, to Railway deployment for production use.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Core Extraction API** - Working API endpoint that accepts source text and returns topic-organized claims
- [ ] **Phase 2: Web UI** - Plain HTML/JS interface for curators to paste text, view claims, and export CSV
- [ ] **Phase 3: Deployment** - Dockerized service running on Railway with health checks

## Phase Details

### Phase 1: Core Extraction API
**Goal**: Curators (or any HTTP client) can send source text to an API and receive structured, topic-organized claims back
**Depends on**: Nothing (first phase)
**Requirements**: EXTR-01, EXTR-02, EXTR-03, EXTR-04, EXTR-05, API-01, API-02, API-03, API-04, API-05, API-06, API-07, INFR-03, INFR-04, INFR-05, INFR-06, INFR-07
**Success Criteria** (what must be TRUE):
  1. `POST /generate/claims` with a news article returns a JSON array of `{ claim_topic, claim }` objects where each claim is self-contained (no pronouns, no dangling references) and atomic (one fact, 5-32 words)
  2. `POST /generate/claims` with empty, whitespace-only, too-short, or too-long text returns a clear error message with an appropriate HTTP status code (not an empty result)
  3. `GET /health` returns `{ "status": "ok" }` without making any Gemini API calls
  4. Gemini API errors (429 rate limit, 503 service unavailable) are retried with backoff and surface as clear error responses if retries are exhausted
  5. `ruff check`, `mypy --strict`, and `pytest` all pass cleanly
**Plans**: 4 plans

Plans:
- [x] 01-01-PLAN.md — Project foundation: UV init, settings, schemas, exceptions, health endpoint, FastAPI app
- [x] 01-02-PLAN.md — Extraction pipeline: adapted prompts, topic/claim extractors with retry, orchestration service
- [x] 01-03-PLAN.md — API integration: generate endpoint, dependency injection, full test suite
- [x] 01-04-PLAN.md — Gap closure: make health endpoint work without GEMINI_API_KEY

### Phase 2: Web UI
**Goal**: Non-technical curators can paste source text into a web page and get a clean table of claims they can export
**Depends on**: Phase 1
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05
**Success Criteria** (what must be TRUE):
  1. Opening the root URL in a browser shows a page with a textarea for pasting source text and a Generate button
  2. Clicking Generate shows a loading indicator, disables the button, and then renders claims as a table with `claim_topic` and `claim` columns
  3. User can click an Export CSV button that downloads a `.csv` file containing all displayed claims with proper escaping
  4. If the API returns an error, the user sees a human-readable error message (not a blank screen or raw JSON)
**Plans**: 1 plan

Plans:
- [ ] 02-01-PLAN.md — Web UI: Jinja2 template with Tailwind, vanilla JS frontend, FastAPI route wiring, tests

### Phase 3: Deployment
**Goal**: The service is running on Railway and accessible to curators via a public URL
**Depends on**: Phase 2
**Requirements**: INFR-01, INFR-02
**Success Criteria** (what must be TRUE):
  1. `docker build` produces a working image and `docker run` starts the service that responds to requests on the configured PORT
  2. Railway deployment succeeds with health check passing at `/health` and the full curator workflow (paste text, generate claims, export CSV) works end-to-end at the deployed URL
**Plans**: TBD

Plans:
- [ ] 03-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3

| Phase | Plans Complete | Status | Completed |
|-------|---------------|--------|-----------|
| 1. Core Extraction API | 4/4 | ✓ Complete | 2026-02-14 |
| 2. Web UI | 0/1 | In progress | - |
| 3. Deployment | 0/TBD | Not started | - |
